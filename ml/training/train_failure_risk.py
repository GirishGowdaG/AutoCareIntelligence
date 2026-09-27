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
    FAILURE_RISK_LOOKBACK_DAYS,
    FAILURE_RISK_HORIZON_DAYS,
    FAILURE_RISK_POOLED_CUTOFFS,
    FAILURE_RISK_ROC_AUC_THRESHOLD,
    FAILURE_RISK_PR_AUC_THRESHOLD,
    FAILURE_RISK_BRIER_THRESHOLD,
)
from ml.data.feature_extractor import FeatureExtractor
from ml.data.temporal_splitter import TemporalSplitter
from ml.models.base_model import compute_df_sha256
from ml.models.failure_risk_model import FailureRiskModel
from ml.inference.writer import MLWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_training() -> FailureRiskModel:
    """Execute Failure-Risk Training with Pooled Repeated-Cutoff Point-in-Time Evaluation.
    
    Data Limitation Documentation:
    The 29-day dataset cannot provide a conventional non-overlapping temporal embargo for a
    7-day lookback + 14-day horizon. Training target windows overlap the subsequent evaluation
    calendar period, and repeated vehicle observations introduce temporal autocorrelation.
    """
    extractor = FeatureExtractor(pg_config=PG_CONFIG)
    splitter = TemporalSplitter(
        horizon_days=FAILURE_RISK_HORIZON_DAYS,
        lookback_days=FAILURE_RISK_LOOKBACK_DAYS,
    )

    t_min = date(2026, 8, 27)
    t_max = date(2026, 9, 25)

    # Training cutoffs: Sep 03 through Sep 08 (6 rolling dates x 10 vehicles = 60 observations)
    train_cutoff_dates = [
        date(2026, 9, 3),
        date(2026, 9, 4),
        date(2026, 9, 5),
        date(2026, 9, 6),
        date(2026, 9, 7),
        date(2026, 9, 8),
    ]

    # Evaluation cutoffs: Sep 09, Sep 10, Sep 11 (3 rolling dates x 10 vehicles = 30 pooled observations)
    eval_cutoff_dates = [date.fromisoformat(d) for d in FAILURE_RISK_POOLED_CUTOFFS]

    # Validate all cutoffs
    for c_date in train_cutoff_dates + eval_cutoff_dates:
        valid, msg = splitter.validate_cutoff(c_date, t_min, t_max)
        if not valid:
            raise ValueError(f"Censored cutoff rejection: {msg}")

    logger.info("Extracting training cohorts across rolling cutoffs (2026-09-03 to 2026-09-08)...")
    train_dfs = []
    for c_date in train_cutoff_dates:
        df_c = extractor.extract_failure_risk_cohort(
            cutoff_date=c_date,
            lookback_days=FAILURE_RISK_LOOKBACK_DAYS,
            horizon_days=FAILURE_RISK_HORIZON_DAYS,
        )
        if not df_c.empty:
            train_dfs.append(df_c)

    if not train_dfs:
        raise RuntimeError("No training records extracted for failure risk cohort")
    train_df = pd.concat(train_dfs, ignore_index=True)

    logger.info("Extracting pooled evaluation cohort across cutoffs (2026-09-09 to 2026-09-11)...")
    eval_dfs = []
    per_cutoff_eval_dfs = {}
    for c_date in eval_cutoff_dates:
        df_e = extractor.extract_failure_risk_cohort(
            cutoff_date=c_date,
            lookback_days=FAILURE_RISK_LOOKBACK_DAYS,
            horizon_days=FAILURE_RISK_HORIZON_DAYS,
        )
        if not df_e.empty:
            eval_dfs.append(df_e)
            per_cutoff_eval_dfs[c_date.isoformat()] = df_e

    if not eval_dfs:
        raise RuntimeError("No evaluation records extracted for failure risk cohort")
    eval_df = pd.concat(eval_dfs, ignore_index=True)

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
    X_eval, y_eval = eval_df[feature_cols], eval_df["target"]

    # Compute training data SHA-256
    data_sha = compute_df_sha256(train_df)
    ML_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(ML_DATASETS_DIR / "train_failure_risk.parquet", index=False)
    eval_df.to_parquet(ML_DATASETS_DIR / "eval_failure_risk.parquet", index=False)

    logger.info(f"Fitting FailureRiskModel on {len(X_train)} training observations (positives={y_train.sum()})...")
    model = FailureRiskModel(
        model_version=MODEL_VERSIONS["failure_risk"],
        n_estimators=100,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)

    train_metrics = model.evaluate(X_train, y_train)
    pooled_eval_metrics = model.evaluate(X_eval, y_eval)

    # Per-cutoff metrics for transparent reporting
    per_cutoff_metrics = {}
    for c_str, df_c in per_cutoff_eval_dfs.items():
        per_cutoff_metrics[c_str] = model.evaluate(df_c[feature_cols], df_c["target"])

    logger.info(f"Actual Train Metrics:               {train_metrics}")
    logger.info(f"Actual Pooled Eval Metrics (N={len(X_eval)}): {pooled_eval_metrics}")
    for c_str, m in per_cutoff_metrics.items():
        logger.info(f"  Cutoff {c_str} Metrics:         {m}")

    # Acceptance Gate Evaluation
    roc_pass = pooled_eval_metrics["roc_auc"] >= FAILURE_RISK_ROC_AUC_THRESHOLD
    pr_pass = pooled_eval_metrics["pr_auc"] >= FAILURE_RISK_PR_AUC_THRESHOLD
    brier_pass = pooled_eval_metrics["brier_score"] <= FAILURE_RISK_BRIER_THRESHOLD
    overall_pass = roc_pass and pr_pass and brier_pass

    logger.info(
        f"Failure-Risk Acceptance Check: ROC-AUC={pooled_eval_metrics['roc_auc']} (>= {FAILURE_RISK_ROC_AUC_THRESHOLD}: {roc_pass}), "
        f"PR-AUC={pooled_eval_metrics['pr_auc']} (>= {FAILURE_RISK_PR_AUC_THRESHOLD}: {pr_pass}), "
        f"Brier={pooled_eval_metrics['brier_score']} (<= {FAILURE_RISK_BRIER_THRESHOLD}: {brier_pass}) -> Overall: {'PASS' if overall_pass else 'FAIL'}"
    )

    # Build metadata envelope
    metadata = {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "trained_at": date.today().isoformat(),
        "training_git_commit": "b454b84",
        "training_data_sha256": data_sha,
        "feature_names": feature_cols,
        "hyperparameters": {"n_estimators": 100, "max_depth": 4, "random_state": RANDOM_SEED},
        "evaluation_framework": "Pooled Repeated-Cutoff Point-in-Time Evaluation with documented temporal target overlap and repeated-vehicle dependence.",
        "data_limitation_note": (
            "The 29-day dataset cannot provide a conventional non-overlapping temporal embargo for a "
            "7-day lookback + 14-day horizon. Training target windows overlap evaluation calendar periods."
        ),
        "sample_sizes": {
            "train_observations": len(X_train),
            "eval_observations": len(X_eval),
            "train_cutoffs": [d.isoformat() for d in train_cutoff_dates],
            "eval_cutoffs": [d.isoformat() for d in eval_cutoff_dates],
        },
        "metrics": {
            "train": train_metrics,
            "pooled_eval": pooled_eval_metrics,
            "per_cutoff_eval": per_cutoff_metrics,
        },
        "acceptance_status": {
            "roc_auc_pass": roc_pass,
            "pr_auc_pass": pr_pass,
            "brier_pass": brier_pass,
            "overall_pass": overall_pass,
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

