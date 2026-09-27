"""Training Pipeline for Vehicle Failure-Risk Prediction (Area 1).

Extracts point-in-time features, validates complete forward outcome windows,
trains FailureRiskModel, evaluates real metrics, and persists artifacts.
"""

from datetime import date
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
from ml.data.temporal_splitter import TemporalSplitter
from ml.models.base_model import compute_df_sha256
from ml.models.failure_risk_model import FailureRiskModel
from ml.inference.writer import MLWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_training() -> FailureRiskModel:
    extractor = FeatureExtractor(pg_config=PG_CONFIG)
    splitter = TemporalSplitter(horizon_days=14, lookback_days=7)

    # In our 30-day dataset (Aug 27 - Sep 25), max eligible cutoff is Sep 11
    # Train cutoff: Sep 05, Val cutoff: Sep 08, Test cutoff: Sep 11
    train_cutoff = date(2026, 9, 5)
    val_cutoff = date(2026, 9, 8)
    test_cutoff = date(2026, 9, 11)

    t_min = date(2026, 8, 27)
    t_max = date(2026, 9, 25)

    # Validate all cutoffs have complete observable forward outcome windows
    for c_date in [train_cutoff, val_cutoff, test_cutoff]:
        valid, msg = splitter.validate_cutoff(c_date, t_min, t_max)
        if not valid:
            raise ValueError(f"Censored cutoff rejection: {msg}")

    logger.info("Extracting point-in-time cohorts for eligible cutoffs...")
    train_df = extractor.extract_failure_risk_cohort(cutoff_date=train_cutoff, lookback_days=7, horizon_days=14)
    val_df = extractor.extract_failure_risk_cohort(cutoff_date=val_cutoff, lookback_days=7, horizon_days=14)
    test_df = extractor.extract_failure_risk_cohort(cutoff_date=test_cutoff, lookback_days=7, horizon_days=14)

    if train_df.empty:
        raise RuntimeError("No training records extracted for failure risk cohort")

    feature_cols = [
        "telemetry_avg_engine_temp_30d",
        "telemetry_max_engine_temp_7d",
        "telemetry_vibration_stddev_30d",
        "telemetry_battery_min_7d",
        "telemetry_high_rpm_ping_count_30d",
        "dtc_critical_high_count_30d",
        "historical_service_count",
        "days_since_last_service",
    ]

    X_train, y_train = train_df[feature_cols], train_df["target"]
    X_val, y_val = val_df[feature_cols], val_df["target"]
    X_test, y_test = test_df[feature_cols], test_df["target"]

    # Compute training data SHA-256
    data_sha = compute_df_sha256(train_df)
    ML_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(ML_DATASETS_DIR / "train_failure_risk.parquet", index=False)

    logger.info(f"Fitting FailureRiskModel on {len(X_train)} samples (positives={y_train.sum()})...")
    model = FailureRiskModel(
        model_version=MODEL_VERSIONS["failure_risk"],
        n_estimators=100,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)

    train_metrics = model.evaluate(X_train, y_train)
    val_metrics = model.evaluate(X_val, y_val)
    test_metrics = model.evaluate(X_test, y_test)

    logger.info(f"Actual Train Metrics: {train_metrics}")
    logger.info(f"Actual Val Metrics:   {val_metrics}")
    logger.info(f"Actual Test Metrics:  {test_metrics}")

    # Build metadata envelope
    metadata = {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "trained_at": date.today().isoformat(),
        "training_git_commit": "a7fc266",
        "training_data_sha256": data_sha,
        "feature_names": feature_cols,
        "hyperparameters": {"n_estimators": 100, "max_depth": 4, "random_state": RANDOM_SEED},
        "metrics": {
            "train": train_metrics,
            "val": val_metrics,
            "test": test_metrics,
        },
    }
    model.metadata = metadata

    # Save artifact
    out_dir = ML_MODELS_DIR / "failure_risk" / model.model_version
    artifact_path = model.save(out_dir)

    # Register in database
    writer = MLWriter(pg_config=PG_CONFIG)
    writer.register_model_metadata(metadata)

    return model


if __name__ == "__main__":
    run_training()
