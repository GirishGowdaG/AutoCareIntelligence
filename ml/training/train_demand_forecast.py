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
)
from ml.data.feature_extractor import FeatureExtractor
from ml.models.base_model import compute_df_sha256
from ml.models.demand_forecast_model import DemandForecastModel
from ml.inference.writer import MLWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_training() -> DemandForecastModel:
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

    # Chronological Split: Hold out final 7 days for test evaluation
    max_date = df["visit_date"].max()
    split_date = max_date - timedelta(days=7)

    train_df = df[df["visit_date"] <= split_date].copy()
    test_df = df[df["visit_date"] > split_date].copy()

    logger.info(f"Demand Series Records: {len(df)} | Train Records: {len(train_df)} | Test Records: {len(test_df)}")

    data_sha = compute_df_sha256(train_df)
    ML_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(ML_DATASETS_DIR / "train_demand_forecast.parquet", index=False)

    model = DemandForecastModel(
        model_version=MODEL_VERSIONS["demand_forecast"],
        n_estimators=100,
        random_state=RANDOM_SEED,
    )
    model.fit(train_df[feature_cols], train_df["service_count"])

    train_metrics = model.evaluate(train_df[feature_cols], train_df["service_count"])
    test_metrics = model.evaluate(test_df[feature_cols], test_df["service_count"])

    logger.info(f"Actual Train Forecast Metrics: {train_metrics}")
    logger.info(f"Actual Test Forecast Metrics:  {test_metrics}")

    metadata = {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "trained_at": date.today().isoformat(),
        "training_git_commit": "a7fc266",
        "training_data_sha256": data_sha,
        "feature_names": feature_cols,
        "hyperparameters": {"n_estimators": 100, "max_depth": 5, "random_state": RANDOM_SEED},
        "metrics": {
            "train": train_metrics,
            "test": test_metrics,
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
