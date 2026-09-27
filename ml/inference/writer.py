"""ML Inference Output Writer for AutoCare Intelligence.

Persists model inference scores and predictions to the isolated PostgreSQL `ml_inference` schema
and archives partitioned Parquet records to `data/ml/predictions/`.
"""

import json
import logging
import uuid
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Dict, Any, List, Optional
import psycopg2
import psycopg2.extras
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ml.config import PG_CONFIG, ML_PREDICTIONS_DIR

logger = logging.getLogger(__name__)


class MLWriter:
    """Manages writing operational predictions to database and Parquet storage."""

    def __init__(self, pg_config: Optional[Dict[str, Any]] = None, predictions_dir: Path = ML_PREDICTIONS_DIR):
        self.pg_config = pg_config or PG_CONFIG
        self.predictions_dir = Path(predictions_dir)

    def _get_connection(self):
        return psycopg2.connect(**self.pg_config)

    def write_failure_predictions(
        self,
        predictions: List[Dict[str, Any]],
        model_version: str,
        batch_id: Optional[str] = None,
    ) -> int:
        """Write vehicle failure risk predictions to database and Parquet."""
        if not predictions:
            return 0

        batch_id = batch_id or f"fail_{uuid.uuid4().hex[:10]}"
        now_utc = datetime.now(timezone.utc)
        rows_to_insert = []

        for p in predictions:
            pred_id = p.get("prediction_id", str(uuid.uuid4()))
            rows_to_insert.append((
                pred_id,
                p["vehicle_id"],
                p["cutoff_date"],
                float(p["risk_score"]),
                p["risk_tier"],
                json.dumps(p.get("top_features", {})),
                model_version,
                now_utc,
            ))

        conn = self._get_connection()
        try:
            sql = """
                INSERT INTO ml_inference.vehicle_failure_predictions (
                    prediction_id, vehicle_id, cutoff_date, risk_score, risk_tier, top_features, model_version, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            cur = conn.cursor()
            psycopg2.extras.execute_batch(cur, sql, rows_to_insert)
            conn.commit()
            cur.close()
        finally:
            conn.close()

        # Archive to Parquet
        archive_dir = self.predictions_dir / "failure_risk" / f"year={now_utc.year}" / f"month={now_utc.month:02d}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_file = archive_dir / f"{batch_id}.parquet"
        pq.write_table(pa.Table.from_pandas(pd.DataFrame(predictions)), str(archive_file))

        return len(rows_to_insert)

    def write_sensor_anomalies(
        self,
        anomalies: List[Dict[str, Any]],
        model_version: str,
        batch_id: Optional[str] = None,
    ) -> int:
        """Write sensor anomaly events to database and Parquet."""
        if not anomalies:
            return 0

        batch_id = batch_id or f"sensor_{uuid.uuid4().hex[:10]}"
        now_utc = datetime.now(timezone.utc)
        rows = []

        for a in anomalies:
            aid = a.get("anomaly_id", str(uuid.uuid4()))
            rows.append((
                aid,
                a["vehicle_id"],
                a["window_timestamp"],
                float(a["anomaly_score"]),
                bool(a["is_anomaly"]),
                json.dumps(a.get("anomalous_features", {})),
                model_version,
                now_utc,
            ))

        conn = self._get_connection()
        try:
            sql = """
                INSERT INTO ml_inference.sensor_anomalies (
                    anomaly_id, vehicle_id, window_timestamp, anomaly_score, is_anomaly, anomalous_features, model_version, detected_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            cur = conn.cursor()
            psycopg2.extras.execute_batch(cur, sql, rows)
            conn.commit()
            cur.close()
        finally:
            conn.close()

        # Archive to Parquet
        archive_dir = self.predictions_dir / "sensor_anomalies" / f"year={now_utc.year}" / f"month={now_utc.month:02d}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_file = archive_dir / f"{batch_id}.parquet"
        pq.write_table(pa.Table.from_pandas(pd.DataFrame(anomalies)), str(archive_file))

        return len(rows)

    def write_demand_forecasts(
        self,
        forecasts: List[Dict[str, Any]],
        model_version: str,
        batch_id: Optional[str] = None,
    ) -> int:
        """Write dealer service demand forecasts to database and Parquet."""
        if not forecasts:
            return 0

        batch_id = batch_id or f"demand_{uuid.uuid4().hex[:10]}"
        now_utc = datetime.now(timezone.utc)
        rows = []

        for f in forecasts:
            fid = f.get("forecast_id", str(uuid.uuid4()))
            rows.append((
                fid,
                f["dealer_id"],
                f["forecast_date"],
                float(f["predicted_volume"]),
                float(f["lower_bound_80"]),
                float(f["upper_bound_80"]),
                model_version,
                now_utc,
            ))

        conn = self._get_connection()
        try:
            sql = """
                INSERT INTO ml_inference.service_demand_forecasts (
                    forecast_id, dealer_id, forecast_date, predicted_volume, lower_bound_80, upper_bound_80, model_version, generated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            cur = conn.cursor()
            psycopg2.extras.execute_batch(cur, sql, rows)
            conn.commit()
            cur.close()
        finally:
            conn.close()

        archive_dir = self.predictions_dir / "service_forecasts" / f"year={now_utc.year}" / f"month={now_utc.month:02d}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_file = archive_dir / f"{batch_id}.parquet"
        pq.write_table(pa.Table.from_pandas(pd.DataFrame(forecasts)), str(archive_file))

        return len(rows)

    def write_warranty_anomalies(
        self,
        anomalies: List[Dict[str, Any]],
        model_version: str,
        batch_id: Optional[str] = None,
    ) -> int:
        """Write warranty claim anomalies to database and Parquet."""
        if not anomalies:
            return 0

        batch_id = batch_id or f"warr_{uuid.uuid4().hex[:10]}"
        now_utc = datetime.now(timezone.utc)
        rows = []

        for w in anomalies:
            wid = w.get("anomaly_id", str(uuid.uuid4()))
            rows.append((
                wid,
                w["claim_id"],
                w.get("dealer_id"),
                w.get("component_id"),
                float(w["claim_amount"]),
                float(w["anomaly_score"]),
                json.dumps(w.get("outlier_reasons", {})),
                model_version,
                now_utc,
            ))

        conn = self._get_connection()
        try:
            sql = """
                INSERT INTO ml_inference.warranty_anomalies (
                    anomaly_id, claim_id, dealer_id, component_id, claim_amount, anomaly_score, outlier_reasons, model_version, flagged_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cur = conn.cursor()
            psycopg2.extras.execute_batch(cur, sql, rows)
            conn.commit()
            cur.close()
        finally:
            conn.close()

        archive_dir = self.predictions_dir / "warranty_anomalies" / f"year={now_utc.year}" / f"month={now_utc.month:02d}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_file = archive_dir / f"{batch_id}.parquet"
        pq.write_table(pa.Table.from_pandas(pd.DataFrame(anomalies)), str(archive_file))

        return len(rows)

    def register_model_metadata(self, metadata: Dict[str, Any]) -> None:
        """Register model version, hyperparameters, training commit, and metrics in metadata table."""
        conn = self._get_connection()
        try:
            sql = """
                INSERT INTO ml_inference.model_metadata (
                    model_id, model_version, trained_at, training_git_commit, training_data_sha256,
                    feature_names, hyperparameters, metrics, artifact_path, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (model_id, model_version) DO UPDATE SET
                    metrics = EXCLUDED.metrics,
                    artifact_path = EXCLUDED.artifact_path;
            """
            cur = conn.cursor()
            cur.execute(sql, [
                metadata["model_id"],
                metadata["model_version"],
                metadata["trained_at"],
                metadata["training_git_commit"],
                metadata["training_data_sha256"],
                json.dumps(metadata.get("feature_names", [])),
                json.dumps(metadata.get("hyperparameters", {})),
                json.dumps(metadata.get("metrics", {})),
                metadata["artifact_path"],
            ])
            conn.commit()
            cur.close()
        finally:
            conn.close()
