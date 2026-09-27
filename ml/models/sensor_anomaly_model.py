"""Sensor Anomaly Detection Model for Vehicle Telemetry.

Unsupervised Isolation Forest identifying multidimensional sensor outliers and erratic dynamics.
"""

from typing import Dict, Any, List, Optional
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

    def calibrate_threshold(self, X_val: pd.DataFrame, target_fpr: float = 0.02) -> float:
        """Calibrate decision threshold on nominal validation data to achieve empirical FPR <= target_fpr."""
        scores = self.score_samples(X_val)
        percentile = (1.0 - target_fpr) * 100.0
        self.calibrated_threshold = float(np.percentile(scores, percentile))
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

