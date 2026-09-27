"""Training Pipeline for Service-Demand Forecasting (Area 3).

Trains DemandForecastModel on historical daily service visits using autoregressive lag features.
"""

from datetime import date, timedelta
from pathlib import Path
import logging
import pandas as pd

from ml.config import (
    PG_CONFIG,
    ML_MODELS_DIR,
    ML_DATASETS_DIR,
    MODEL_VERSIONS,
    RANDOM_SEED,
    DEMAND_MAE_THRESHOLD,
    DEMAND_MIN_IMPROVEMENT_PCT,
)
from ml.data.feature_extractor import FeatureExtractor
from ml.models.base_model import compute_df_sha256
from ml.models.demand_forecast_model import DemandForecastModel
from ml.inference.writer import MLWriter
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_training() -> DemandForecastModel:
    """Execute Service-Demand Forecast Training with Daily MAE and Naive Baseline Lift Verification."""
    extractor = FeatureExtractor(pg_config=PG_CONFIG)

    logger.info("Extracting historical service demand time series...")
    df = extractor.extract_service_demand_series()
    if df.empty:
        raise RuntimeError("No service history extracted for demand forecasting")

    feature_cols = [
        "service_count_lag_7d",
        "service_count_lag_14d",
        "rolling_mean_service_count_7d",
        "day_of_week",
        "is_weekend",
    ]

    # Chronological Split: Hold out final 7 days (2026-09-19 to 2026-09-25) for test evaluation
    max_date = df["visit_date"].max()
    split_date = max_date - timedelta(days=7)

    train_df = df[df["visit_date"] <= split_date].copy()
    test_df = df[df["visit_date"] > split_date].copy()

    logger.info(f"Demand Series Records: {len(df)} | Train Records: {len(train_df)} | Test Records: {len(test_df)}")

    data_sha = compute_df_sha256(train_df)
    ML_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(ML_DATASETS_DIR / "train_demand_forecast.parquet", index=False)
    test_df.to_parquet(ML_DATASETS_DIR / "test_demand_forecast.parquet", index=False)

    model = DemandForecastModel(
        model_version=MODEL_VERSIONS["demand_forecast"],
        n_estimators=100,
        random_state=RANDOM_SEED,
    )
    model.fit(train_df[feature_cols], train_df["service_count"])

    train_metrics = model.evaluate(train_df[feature_cols], train_df["service_count"])
    test_metrics = model.evaluate(test_df[feature_cols], test_df["service_count"])

    # Compute Naive 7-day Seasonal Lag Baseline MAE on test horizon
    test_actuals = test_df["service_count"].values
    naive_preds = test_df["service_count_lag_7d"].values
    naive_mae = float(np.mean(np.abs(test_actuals - naive_preds)))

    candidate_mae = test_metrics["mae"]
    relative_lift = float((naive_mae - candidate_mae) / (naive_mae + 1e-9))

    mae_pass = candidate_mae <= DEMAND_MAE_THRESHOLD
    lift_pass = relative_lift >= DEMAND_MIN_IMPROVEMENT_PCT
    overall_pass = mae_pass and lift_pass

    logger.info(f"Actual Train Forecast Metrics: {train_metrics}")
    logger.info(f"Actual Test Forecast Metrics:  {test_metrics}")
    logger.info(f"Naive 7-Day Seasonal Lag MAE:  {naive_mae:.4f}")
    logger.info(f"Candidate Relative Lift:       {relative_lift * 100.0:.2f}%")
    logger.info(
        f"Service Demand Acceptance Check: Candidate MAE={candidate_mae:.4f} (<= {DEMAND_MAE_THRESHOLD}: {mae_pass}), "
        f"Relative Lift={relative_lift * 100.0:.2f}% (>= {DEMAND_MIN_IMPROVEMENT_PCT * 100.0:.1f}%: {lift_pass}) -> Overall: {'PASS' if overall_pass else 'FAIL'}"
    )

    metadata = {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "trained_at": date.today().isoformat(),
        "training_git_commit": "b454b84",
        "training_data_sha256": data_sha,
        "feature_names": feature_cols,
        "hyperparameters": {"n_estimators": 100, "max_depth": 5, "random_state": RANDOM_SEED},
        "sample_sizes": {
            "train_dealer_days": len(train_df),
            "test_dealer_days": len(test_df),
        },
        "metrics": {
            "train": train_metrics,
            "test": test_metrics,
            "naive_baseline_mae": round(naive_mae, 4),
            "relative_lift": round(relative_lift, 4),
        },
        "acceptance_status": {
            "candidate_mae": candidate_mae,
            "mae_threshold": DEMAND_MAE_THRESHOLD,
            "mae_pass": mae_pass,
            "relative_lift": relative_lift,
            "lift_threshold": DEMAND_MIN_IMPROVEMENT_PCT,
            "lift_pass": lift_pass,
            "overall_pass": overall_pass,
        },
    }
    model.metadata = metadata

    out_dir = ML_MODELS_DIR / "demand_forecast" / model.model_version
    artifact_path = model.save(out_dir)

    writer = MLWriter(pg_config=PG_CONFIG)
    writer.register_model_metadata(metadata)

    return model


if __name__ == "__main__":
    run_training()

