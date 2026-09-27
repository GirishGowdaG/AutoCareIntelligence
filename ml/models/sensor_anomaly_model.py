"""Sensor Anomaly Detection Model for Vehicle Telemetry.

Unsupervised Isolation Forest identifying multidimensional sensor outliers and erratic dynamics.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml.models.base_model import BaseModel
from ml.config import RANDOM_SEED


class SensorAnomalyModel(BaseModel):
    """Unsupervised telemetry sensor anomaly detector using empirical min-max normalization."""

    def __init__(
        self,
        model_version: str = "v1.0.0",
        n_estimators: int = 100,
        contamination: float = 0.02,
        random_state: int = RANDOM_SEED,
    ):
        super().__init__(
            model_id="sensor_anomaly_iforest",
            model_version=model_version,
            random_state=random_state,
        )
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.estimator = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )
        self.min_raw_score: float = -1.0
        self.max_raw_score: float = 0.0
        self.calibrated_threshold: float = 0.50

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "SensorAnomalyModel":
        self.feature_names = list(X.columns)
        self.estimator.fit(X[self.feature_names])
        raw_train = self.estimator.score_samples(X[self.feature_names])
        self.min_raw_score = float(np.min(raw_train))
        self.max_raw_score = float(np.max(raw_train))
        self.is_fitted = True
        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Return empirical min-max normalized anomaly score in [0.0, 1.0].
        
        Formula:
            norm_score = clip((max_raw_train - raw_score) / (max_raw_train - min_raw_train), 0.0, 1.0)
        More negative raw score -> higher normalized anomaly score (approaching 1.0).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before scoring samples")
        raw_scores = self.estimator.score_samples(X[self.feature_names])
        denom = self.max_raw_score - self.min_raw_score
        if denom <= 1e-9:
            denom = 1.0
        norm_scores = (self.max_raw_score - raw_scores) / denom
        return np.clip(norm_scores, 0.0, 1.0)

    def calibrate_threshold(
        self,
        X_val: pd.DataFrame,
        target_fpr: Optional[float] = None,
        percentile: Optional[float] = None,
    ) -> float:
        """Calibrate decision threshold on nominal validation data.
        
        Supports target_fpr (e.g. 0.012 for Method B statistical tolerance margin)
        or explicit percentile (e.g. 98.8).
        """
        scores = self.score_samples(X_val)
        if percentile is None:
            fpr = target_fpr if target_fpr is not None else 0.02
            pct = (1.0 - fpr) * 100.0
        else:
            pct = float(percentile)
        self.calibrated_threshold = float(np.percentile(scores, pct))
        return self.calibrated_threshold

    def predict(self, X: pd.DataFrame, threshold: Optional[float] = None) -> np.ndarray:
        """Return boolean array where True = detected anomaly exceeding decision threshold."""
        thresh = self.calibrated_threshold if threshold is None else threshold
        scores = self.score_samples(X)
        return scores >= thresh

    def evaluate(self, X: pd.DataFrame, y: Optional[pd.Series] = None, threshold: Optional[float] = None) -> Dict[str, float]:
        """Compute statistical summary metrics of anomaly score distribution."""
        thresh = self.calibrated_threshold if threshold is None else threshold
        scores = self.score_samples(X)
        anomalies = self.predict(X, threshold=thresh)

        return {
            "mean_anomaly_score": round(float(np.mean(scores)), 4),
            "median_anomaly_score": round(float(np.median(scores)), 4),
            "max_anomaly_score": round(float(np.max(scores)), 4),
            "detected_anomaly_rate": round(float(np.mean(anomalies)), 4),
            "decision_threshold": round(float(thresh), 4),
        }

    def save(self, output_dir: Path) -> Path:
        """Serialize model artifact including min/max raw scores and calibrated threshold."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata.setdefault("hyperparameters", {})
        self.metadata["hyperparameters"]["min_raw_score"] = self.min_raw_score
        self.metadata["hyperparameters"]["max_raw_score"] = self.max_raw_score
        self.metadata["hyperparameters"]["calibrated_threshold"] = self.calibrated_threshold

        artifact_file = super().save(output_dir)
        payload = joblib.load(artifact_file)
        payload["min_raw_score"] = self.min_raw_score
        payload["max_raw_score"] = self.max_raw_score
        payload["calibrated_threshold"] = self.calibrated_threshold
        joblib.dump(payload, artifact_file)
        return artifact_file

    def load(self, model_file: Path) -> "SensorAnomalyModel":
        """Load serialized estimator and restore normalization parameters and calibrated threshold."""
        super().load(model_file)
        payload = joblib.load(model_file)
        if isinstance(payload, dict):
            self.min_raw_score = payload.get("min_raw_score", self.min_raw_score)
            self.max_raw_score = payload.get("max_raw_score", self.max_raw_score)
            self.calibrated_threshold = payload.get("calibrated_threshold", self.calibrated_threshold)
        if "hyperparameters" in self.metadata:
            hp = self.metadata["hyperparameters"]
            self.min_raw_score = hp.get("min_raw_score", self.min_raw_score)
            self.max_raw_score = hp.get("max_raw_score", self.max_raw_score)
            self.calibrated_threshold = hp.get("calibrated_threshold", self.calibrated_threshold)
        return self

