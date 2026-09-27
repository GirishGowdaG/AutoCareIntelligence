"""Streaming Sensor Anomaly Inference Engine for AutoCare Intelligence.

Evaluates in-memory streaming telemetry events in near-real-time (< 5ms)
via the trained SensorAnomalyModel.
Distinct from the Airflow batch/compaction path.
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from pathlib import Path

from ml.models.sensor_anomaly_model import SensorAnomalyModel
from ml.config import SENSOR_FEATURES, ML_MODELS_DIR


class StreamingSensorScorer:
    """Near-real-time streaming scorer for live vehicle telemetry pings."""

    def __init__(self, model: Optional[SensorAnomalyModel] = None, model_dir: Optional[Path] = None):
        if model is not None:
            self.model = model
        else:
            model_path = (model_dir or ML_MODELS_DIR / "sensor_anomaly" / "v1.0.0") / "model.joblib"
            self.model = SensorAnomalyModel()
            if model_path.exists():
                self.model.load(model_path)

    def score_event(self, event: Dict[str, Any], anomaly_threshold: float = 0.60) -> Dict[str, Any]:
        """Score an individual streaming telemetry event in real time.
        
        Requires verified sensor attributes: rpm, temperature, battery, vibration.
        """
        rpm = float(event.get("rpm", 0.0))
        temp = float(event.get("temperature", 0.0))
        battery = float(event.get("battery", 0.0))
        vib = float(event.get("vibration", 0.0))

        # In-memory feature projection
        norm_rpm = (rpm - 2500.0) / 1500.0
        norm_temp = (temp - 85.0) / 20.0
        norm_vib = (vib - 1.0) / 1.0
        vib_ratio = vib / (rpm + 1.0)

        df_features = pd.DataFrame([{
            "rpm": rpm,
            "temperature": temp,
            "battery": battery,
            "vibration": vib,
            "norm_rpm": norm_rpm,
            "norm_temperature": norm_temp,
            "norm_vibration": norm_vib,
            "vibration_per_rpm_ratio": vib_ratio,
        }])

        if self.model.is_fitted:
            score = float(self.model.score_samples(df_features)[0])
            is_anomaly = score >= anomaly_threshold
        else:
            # Fallback heuristic if model not yet fitted
            score = 0.1
            is_anomaly = False

        anomalous_features = {}
        if is_anomaly:
            if temp > 105.0 or temp < -10.0:
                anomalous_features["temperature"] = temp
            if vib > 4.0:
                anomalous_features["vibration"] = vib

        return {
            "vehicle_id": event.get("vehicle_id", "UNKNOWN"),
            "window_timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "anomaly_score": round(score, 4),
            "is_anomaly": is_anomaly,
            "anomalous_features": anomalous_features,
            "model_version": self.model.model_version,
            "inference_mode": "STREAMING_REALTIME",
        }
