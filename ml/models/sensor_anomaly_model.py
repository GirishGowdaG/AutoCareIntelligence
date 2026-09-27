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
    """Unsupervised telemetry sensor anomaly detector."""

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

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "SensorAnomalyModel":
        self.feature_names = list(X.columns)
        self.estimator.fit(X)
        self.is_fitted = True
        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Return normalized anomaly score in [0.0, 1.0] where 1.0 is highest outlier probability."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before scoring samples")
        # In sklearn IsolationForest, score_samples returns opposite of anomaly score (lower = more abnormal)
        raw_scores = self.estimator.score_samples(X[self.feature_names])
        # Invert and min-max scale approximately into [0, 1]
        norm_scores = 1.0 / (1.0 + np.exp(raw_scores * 5.0))
        return norm_scores

    def predict(self, X: pd.DataFrame, threshold: float = 0.60) -> np.ndarray:
        """Return boolean array where True = detected anomaly."""
        scores = self.score_samples(X)
        return scores >= threshold

    def evaluate(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> Dict[str, float]:
        """Compute statistical summary metrics of anomaly score distribution."""
        scores = self.score_samples(X)
        anomalies = self.predict(X)

        return {
            "mean_anomaly_score": round(float(np.mean(scores)), 4),
            "median_anomaly_score": round(float(np.median(scores)), 4),
            "max_anomaly_score": round(float(np.max(scores)), 4),
            "detected_anomaly_rate": round(float(np.mean(anomalies)), 4),
        }
