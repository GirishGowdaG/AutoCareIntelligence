"""Service-Demand Forecasting Model for AutoCare Intelligence.

Forecasts aggregate daily service visits per dealer using autoregressive and seasonal lags.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from ml.models.base_model import BaseModel
from ml.config import RANDOM_SEED


class DemandForecastModel(BaseModel):
    """Time-series regressor for dealer service visit volume."""

    def __init__(
        self,
        model_version: str = "v1.0.0",
        n_estimators: int = 100,
        random_state: int = RANDOM_SEED,
    ):
        super().__init__(
            model_id="service_demand_forecast_rf",
            model_version=model_version,
            random_state=random_state,
        )
        self.n_estimators = n_estimators
        self.estimator = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=5,
            random_state=random_state,
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "DemandForecastModel":
        self.feature_names = list(X.columns)
        self.estimator.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict")
        preds = self.estimator.predict(X[self.feature_names])
        return np.maximum(0.0, preds)

    def predict_with_intervals(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Predict point forecast and 80% prediction intervals across ensemble trees."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        tree_preds = np.array([tree.predict(X[self.feature_names].values) for tree in self.estimator.estimators_])
        point_preds = np.maximum(0.0, np.mean(tree_preds, axis=0))
        lower_80 = np.maximum(0.0, np.percentile(tree_preds, 10, axis=0))
        upper_80 = np.maximum(0.0, np.percentile(tree_preds, 90, axis=0))
        return point_preds, lower_80, upper_80

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        preds = self.predict(X)
        actuals = y.values

        # WAPE calculation: sum(|actual - pred|) / sum(actual)
        sum_actual = np.sum(actuals)
        wape = float(np.sum(np.abs(actuals - preds)) / (sum_actual + 1e-5)) if sum_actual > 0 else 0.0
        mae = float(mean_absolute_error(actuals, preds))
        rmse = float(np.sqrt(np.mean((actuals - preds) ** 2)))

        return {
            "wape": round(wape, 4),
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
        }
