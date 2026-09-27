"""Scheduled Batch Inference Runner for AutoCare Intelligence ML Layer.

Executes batch scoring for failure risk, sensor anomalies, service demand, and warranty claims,
persisting outputs via MLWriter to the isolated `ml_inference` schema and Parquet archives.
"""

from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import uuid
import pandas as pd

from ml.config import (
    PG_CONFIG,
    ML_MODELS_DIR,
    MODEL_VERSIONS,
    FAILURE_RISK_HORIZON_DAYS,
    DEMAND_FORECAST_HORIZON_DAYS,
)
from ml.data.feature_extractor import FeatureExtractor
from ml.models.failure_risk_model import FailureRiskModel
from ml.models.sensor_anomaly_model import SensorAnomalyModel
from ml.models.demand_forecast_model import DemandForecastModel
from ml.models.warranty_anomaly_model import WarrantyAnomalyModel
from ml.inference.writer import MLWriter

logger = logging.getLogger(__name__)


class BatchInferenceRunner:
    """Orchestrates scheduled batch inference runs across all intelligence areas."""

    def __init__(
        self,
        models_dir: Path = ML_MODELS_DIR,
        pg_config: Optional[Dict[str, Any]] = None,
    ):
        self.models_dir = Path(models_dir)
        self.extractor = FeatureExtractor(pg_config=pg_config)
        self.writer = MLWriter(pg_config=pg_config)

    def run_failure_risk_inference(self, cutoff_date: Optional[date] = None) -> int:
        """Run daily failure-risk batch inference."""
        cutoff_date = cutoff_date or date.today()
        model_file = self.models_dir / "failure_risk" / MODEL_VERSIONS["failure_risk"] / "model.joblib"
        model = FailureRiskModel(model_version=MODEL_VERSIONS["failure_risk"])
        if model_file.exists():
            model.load(model_file)

        df = self.extractor.extract_failure_risk_cohort(cutoff_date=cutoff_date)
        if df.empty or not model.is_fitted:
            return 0

        X = df[model.feature_names]
        probs = model.predict_proba(X)

        records = []
        for i, row in df.iterrows():
            prob = float(probs[i])
            tier = model.predict_risk_tier(prob)
            records.append({
                "prediction_id": str(uuid.uuid4()),
                "vehicle_id": row["vehicle_id"],
                "cutoff_date": cutoff_date,
                "risk_score": prob,
                "risk_tier": tier,
                "top_features": {col: float(row[col]) for col in model.feature_names if col in row},
            })

        return self.writer.write_failure_predictions(records, model_version=model.model_version)

    def run_sensor_anomaly_batch(self, cutoff_date: Optional[date] = None) -> int:
        """Run micro-batch telemetry sensor anomaly detection."""
        model_file = self.models_dir / "sensor_anomaly" / MODEL_VERSIONS["sensor_anomaly"] / "model.joblib"
        model = SensorAnomalyModel(model_version=MODEL_VERSIONS["sensor_anomaly"])
        if model_file.exists():
            model.load(model_file)

        df = self.extractor.extract_sensor_telemetry_features(cutoff_date=cutoff_date, excise_fault_windows=False)
        if df.empty or not model.is_fitted:
            return 0

        X = df[model.feature_names]
        scores = model.score_samples(X)
        is_anom = model.predict(X)

        records = []
        for i, row in df.iterrows():
            records.append({
                "anomaly_id": str(uuid.uuid4()),
                "vehicle_id": row["vehicle_id"],
                "window_timestamp": row["timestamp"],
                "anomaly_score": float(scores[i]),
                "is_anomaly": bool(is_anom[i]),
                "anomalous_features": {
                    "rpm": float(row["rpm"]),
                    "temperature": float(row["temperature"]),
                    "vibration": float(row["vibration"]),
                } if is_anom[i] else {},
            })

        return self.writer.write_sensor_anomalies(records, model_version=model.model_version)

    def run_service_demand_forecast(self, forecast_origin: Optional[date] = None) -> int:
        """Run weekly service-demand forecasting across dealers."""
        forecast_origin = forecast_origin or date.today()
        model_file = self.models_dir / "demand_forecast" / MODEL_VERSIONS["demand_forecast"] / "model.joblib"
        model = DemandForecastModel(model_version=MODEL_VERSIONS["demand_forecast"])
        if model_file.exists():
            model.load(model_file)

        df = self.extractor.extract_service_demand_series()
        if df.empty or not model.is_fitted:
            return 0

        # Filter strictly up to forecast origin
        df_origin = df[df["visit_date"] <= forecast_origin].copy()
        if df_origin.empty:
            return 0

        # Generate forward 14 days grid
        all_dealers = df_origin["dealer_id"].unique()
        forward_records = []

        for dealer in all_dealers:
            dealer_df = df_origin[df_origin["dealer_id"] == dealer].sort_values("visit_date")
            if dealer_df.empty:
                continue
            last_row = dealer_df.iloc[-1]

            for h in range(1, DEMAND_FORECAST_HORIZON_DAYS + 1):
                f_date = forecast_origin + timedelta(days=h)
                feat_dict = {
                    "service_count_lag_7d": float(last_row.get("service_count_lag_7d", 0.0)),
                    "service_count_lag_14d": float(last_row.get("service_count_lag_14d", 0.0)),
                    "rolling_mean_service_count_7d": float(last_row.get("rolling_mean_service_count_7d", 0.0)),
                    "day_of_week": f_date.weekday(),
                    "is_weekend": 1 if f_date.weekday() in [5, 6] else 0,
                }
                feat_df = pd.DataFrame([feat_dict])
                point, lower, upper = model.predict_with_intervals(feat_df)
                forward_records.append({
                    "forecast_id": str(uuid.uuid4()),
                    "dealer_id": dealer,
                    "forecast_date": f_date,
                    "predicted_volume": float(point[0]),
                    "lower_bound_80": float(lower[0]),
                    "upper_bound_80": float(upper[0]),
                })

        return self.writer.write_demand_forecasts(forward_records, model_version=model.model_version)

    def run_warranty_anomaly_scoring(self) -> int:
        """Run daily batch scoring for warranty claim outliers."""
        model_file = self.models_dir / "warranty_anomaly" / MODEL_VERSIONS["warranty_anomaly"] / "model.joblib"
        model = WarrantyAnomalyModel(model_version=MODEL_VERSIONS["warranty_anomaly"])
        if model_file.exists():
            model.load(model_file)

        df = self.extractor.extract_warranty_features()
        if df.empty or not model.is_fitted:
            return 0

        X = df[model.feature_names]
        scores = model.score_samples(X)

        records = []
        for i, row in df.iterrows():
            score = float(scores[i])
            records.append({
                "anomaly_id": str(uuid.uuid4()),
                "claim_id": row["claim_id"],
                "dealer_id": None,
                "component_id": row["component_id"],
                "claim_amount": float(row["claim_amount"]),
                "anomaly_score": score,
                "outlier_reasons": {
                    "median_ratio": float(row.get("claim_amount_to_component_median_ratio", 1.0)),
                    "iqr_distance": float(row.get("component_claim_iqr_distance", 0.0)),
                } if score >= 0.80 else {},
            })

        return self.writer.write_warranty_anomalies(records, model_version=model.model_version)

