"""Training Pipeline for Sensor Anomaly Detection (Area 2).

Fits unsupervised Isolation Forest on verified nominal telemetry with known fault windows excised.
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
from ml.models.base_model import compute_df_sha256
from ml.models.sensor_anomaly_model import SensorAnomalyModel
from ml.inference.writer import MLWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_training() -> SensorAnomalyModel:
    extractor = FeatureExtractor(pg_config=PG_CONFIG)

    logger.info("Extracting sensor telemetry features with fault window excision...")
    df = extractor.extract_sensor_telemetry_features(excise_fault_windows=True)
    if df.empty:
        raise RuntimeError("No telemetry records extracted")

    feature_cols = [
        "rpm",
        "temperature",
        "battery",
        "vibration",
        "norm_rpm",
        "norm_temperature",
        "norm_vibration",
        "vibration_per_rpm_ratio",
    ]

    # Training baseline is strictly nominal (excised fault windows)
    nominal_train = df[~df["is_fault_window"]].copy()
    fault_test = df[df["is_fault_window"]].copy()

    logger.info(f"Total Telemetry Pings: {len(df)} | Nominal Train: {len(nominal_train)} | Excised Fault Pings: {len(fault_test)}")

    data_sha = compute_df_sha256(nominal_train)
    ML_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    nominal_train.to_parquet(ML_DATASETS_DIR / "train_sensor_anomaly.parquet", index=False)

    model = SensorAnomalyModel(
        model_version=MODEL_VERSIONS["sensor_anomaly"],
        contamination=0.02,
        random_state=RANDOM_SEED,
    )
    model.fit(nominal_train[feature_cols])

    train_metrics = model.evaluate(nominal_train[feature_cols])
    test_metrics = model.evaluate(fault_test[feature_cols]) if not fault_test.empty else {}

    logger.info(f"Nominal Baseline Metrics: {train_metrics}")
    logger.info(f"Fault Window Metrics:    {test_metrics}")

    metadata = {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "trained_at": date.today().isoformat(),
        "training_git_commit": "a7fc266",
        "training_data_sha256": data_sha,
        "feature_names": feature_cols,
        "hyperparameters": {"contamination": 0.02, "n_estimators": 100, "random_state": RANDOM_SEED},
        "metrics": {
            "nominal_train": train_metrics,
            "fault_eval": test_metrics,
        },
    }
    model.metadata = metadata

    out_dir = ML_MODELS_DIR / "sensor_anomaly" / model.model_version
    artifact_path = model.save(out_dir)

    writer = MLWriter(pg_config=PG_CONFIG)
    writer.register_model_metadata(metadata)

    return model


if __name__ == "__main__":
    run_training()
