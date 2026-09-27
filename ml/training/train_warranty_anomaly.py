"""Training Pipeline for Warranty Claim Anomaly Detection (Area 4).

Trains unsupervised WarrantyAnomalyModel on approved warranty attributes without synthetic fraud labels.
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
    WARRANTY_SCOPE_NAME,
    WARRANTY_TRIAGE_THRESHOLD_PROPOSED,
)
from ml.data.feature_extractor import FeatureExtractor
from ml.models.base_model import compute_df_sha256
from ml.models.warranty_anomaly_model import WarrantyAnomalyModel
from ml.inference.writer import MLWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_training() -> WarrantyAnomalyModel:
    """Execute Unsupervised Warranty Claim Outlier Ranking Pipeline (Area 4).
    
    Fits Isolation Forest on verified warranty attributes (N=10 claims).
    Outputs empirical percentile ranks in [0.0, 1.0].
    Strictly unsupervised: zero fraud detection or classification claims.
    """
    extractor = FeatureExtractor(pg_config=PG_CONFIG)

    logger.info("Extracting approved warranty claim records...")
    df = extractor.extract_warranty_features()
    if df.empty:
        raise RuntimeError("No warranty claims extracted for anomaly scoring")

    feature_cols = [
        "claim_amount",
        "claim_amount_to_component_median_ratio",
        "component_claim_iqr_distance",
        "rolling_vehicle_claims_30d",
    ]

    logger.info(f"Total Warranty Claims: {len(df)}")

    data_sha = compute_df_sha256(df)
    ML_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ML_DATASETS_DIR / "train_warranty_anomaly.parquet", index=False)

    model = WarrantyAnomalyModel(
        model_version=MODEL_VERSIONS["warranty_anomaly"],
        contamination=0.02,
        random_state=RANDOM_SEED,
    )
    model.fit(df[feature_cols])

    metrics = model.evaluate(df[feature_cols])
    logger.info(f"Actual Warranty Outlier Ranking Evaluation Metrics: {metrics}")

    # Compute individual claim ranks for logging
    ranks = model.score_samples(df[feature_cols])
    for idx, row in df.iterrows():
        logger.info(f"  Claim ID {row['claim_id']}: Percentile Rank = {ranks[idx]:.4f} (Amount=${row['claim_amount']:.2f})")

    metadata = {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "trained_at": date.today().isoformat(),
        "training_git_commit": "b454b84",
        "training_data_sha256": data_sha,
        "scope": WARRANTY_SCOPE_NAME,
        "fraud_disclaimer": "Strictly unsupervised outlier ranking for audit prioritization. Zero claims of fraud detection, fraud classification, or abuse identification.",
        "feature_names": feature_cols,
        "hyperparameters": {
            "contamination": 0.02,
            "n_estimators": 100,
            "random_state": RANDOM_SEED,
            "scaling": "Empirical Percentile Rank [0.0, 1.0]",
            "exploratory_triage_threshold": WARRANTY_TRIAGE_THRESHOLD_PROPOSED,
        },
        "sample_size": len(df),
        "metrics": metrics,
    }
    model.metadata = metadata

    out_dir = ML_MODELS_DIR / "warranty_anomaly" / model.model_version
    artifact_path = model.save(out_dir)

    writer = MLWriter(pg_config=PG_CONFIG)
    writer.register_model_metadata(metadata)

    return model


if __name__ == "__main__":
    run_training()

