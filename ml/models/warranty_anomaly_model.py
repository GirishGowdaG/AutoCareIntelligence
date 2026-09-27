"""Warranty Claim Anomaly Detection Model (Unsupervised Outlier Scorer).

Identifies statistical billing deviations, component cost outliers, and frequency spikes.
Strictly unsupervised: does not assume or invent fraud labels.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml.models.base_model import BaseModel
from ml.config import RANDOM_SEED


class WarrantyAnomalyModel(BaseModel):
    """Unsupervised warranty claim outlier and billing irregularity detector."""

    def __init__(
        self,
        model_version: str = "v1.0.0",
        contamination: float = 0.02,
        random_state: int = RANDOM_SEED,
    ):
        super().__init__(
            model_id="warranty_anomaly_iforest",
            model_version=model_version,
            random_state=random_state,
        )
        self.contamination = contamination
        self.estimator = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=random_state,
        )

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "WarrantyAnomalyModel":
        self.feature_names = list(X.columns)
        self.estimator.fit(X)
        self.is_fitted = True
        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Return continuous anomaly score in [0.0, 1.0]."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before score_samples")
        raw_scores = self.estimator.score_samples(X[self.feature_names])
        norm_scores = 1.0 / (1.0 + np.exp(raw_scores * 5.0))
        return norm_scores

    def predict(self, X: pd.DataFrame, threshold: float = 0.65) -> np.ndarray:
        """Flag claims exceeding anomaly threshold."""
        scores = self.score_samples(X)
        return scores >= threshold

    def evaluate(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> Dict[str, float]:
        """Statistical summary of outlier score distribution."""
        scores = self.score_samples(X)
        anomalies = self.predict(X)

        return {
            "mean_anomaly_score": round(float(np.mean(scores)), 4),
            "median_anomaly_score": round(float(np.median(scores)), 4),
            "max_anomaly_score": round(float(np.max(scores)), 4),
            "outlier_rate": round(float(np.mean(anomalies)), 4),
        }
