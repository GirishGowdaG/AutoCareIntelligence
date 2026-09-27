"""Warranty Claim Anomaly Detection Model (Unsupervised Outlier Scorer).

Identifies statistical billing deviations, component cost outliers, and frequency spikes.
Strictly unsupervised: does not assume, predict, or classify fraud.
Scope: Unsupervised Warranty Outlier Ranking for Audit Prioritization.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.ensemble import IsolationForest

from ml.models.base_model import BaseModel
from ml.config import RANDOM_SEED, WARRANTY_TRIAGE_THRESHOLD_PROPOSED


class WarrantyAnomalyModel(BaseModel):
    """Unsupervised warranty claim outlier ranking model for audit prioritization."""

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
        self.estimator.fit(X[self.feature_names])
        self.is_fitted = True
        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Return empirical percentile rank anomaly score in [0.0, 1.0].
        
        Formula:
            Rank Score_i = (Rank(-raw_score_i) - 1) / (N - 1)
        where Rank 1 is the most nominal claim (score 0.0) and Rank N is the
        most extreme statistical outlier claim (score 1.0).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before score_samples")
        raw_scores = self.estimator.score_samples(X[self.feature_names])
        n = len(raw_scores)
        if n <= 1:
            return np.zeros(n, dtype=float)
        # In sklearn, more negative raw_score indicates greater outlier severity.
        # -raw_scores maps more negative values to larger positive values.
        ranks = rankdata(-raw_scores, method="min")
        rank_scores = (ranks - 1.0) / (n - 1.0)
        return np.clip(rank_scores, 0.0, 1.0)

    def predict(self, X: pd.DataFrame, threshold: float = WARRANTY_TRIAGE_THRESHOLD_PROPOSED) -> np.ndarray:
        """Flag claims exceeding exploratory triage threshold (proposed 0.80)."""
        scores = self.score_samples(X)
        return scores >= threshold

    def evaluate(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> Dict[str, float]:
        """Statistical summary of outlier percentile rank distribution."""
        scores = self.score_samples(X)
        anomalies = self.predict(X)

        return {
            "mean_anomaly_score": round(float(np.mean(scores)), 4),
            "median_anomaly_score": round(float(np.median(scores)), 4),
            "max_anomaly_score": round(float(np.max(scores)), 4),
            "min_anomaly_score": round(float(np.min(scores)), 4),
            "outlier_triage_count": int(np.sum(anomalies)),
            "outlier_triage_rate": round(float(np.mean(anomalies)), 4),
        }

