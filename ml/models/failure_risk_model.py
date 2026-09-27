"""Vehicle Failure-Risk Prediction Model (Predictive Maintenance).

Predicts forward 14-day breakdown probability using point-in-time telemetry aggregates,
diagnostic trouble codes, and service history.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_curve, auc, roc_auc_score, brier_score_loss, precision_score, recall_score

from ml.models.base_model import BaseModel
from ml.config import RANDOM_SEED


class FailureRiskModel(BaseModel):
    """Predictive failure risk classifier."""

    def __init__(
        self,
        model_version: str = "v1.0.0",
        n_estimators: int = 100,
        max_depth: int = 4,
        random_state: int = RANDOM_SEED,
    ):
        super().__init__(
            model_id="vehicle_failure_risk_rf",
            model_version=model_version,
            random_state=random_state,
        )
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.estimator = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            class_weight="balanced",
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "FailureRiskModel":
        self.feature_names = list(X.columns)
        self.estimator.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba")
        return self.estimator.predict_proba(X[self.feature_names])[:, 1]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probs = self.predict_proba(X)
        return (probs >= 0.5).astype(int)

    def predict_risk_tier(self, prob: float) -> str:
        """Assign risk tier based on predicted failure probability."""
        if prob >= 0.75:
            return "CRITICAL"
        if prob >= 0.50:
            return "HIGH"
        if prob >= 0.25:
            return "MEDIUM"
        return "LOW"

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        probs = self.predict_proba(X)
        preds = (probs >= 0.5).astype(int)

        # PR-AUC calculation
        precision_curve, recall_curve, _ = precision_recall_curve(y, probs)
        pr_auc_val = float(auc(recall_curve, precision_curve)) if len(recall_curve) > 1 else 0.0

        roc_auc_val = float(roc_auc_score(y, probs)) if len(np.unique(y)) > 1 else 0.5
        brier = float(brier_score_loss(y, probs))
        prec = float(precision_score(y, preds, zero_division=0))
        rec = float(recall_score(y, preds, zero_division=0))

        return {
            "pr_auc": round(pr_auc_val, 4),
            "roc_auc": round(roc_auc_val, 4),
            "brier_score": round(brier, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
        }
