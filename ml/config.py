"""Configuration and domain constants for AutoCare Intelligence ML layer.

Defines database settings, directory paths, deterministic mappings, feature sets,
and temporal windowing parameters.
"""

from pathlib import Path
from typing import Dict, Any, Set, List

BASE_DIR = Path(__file__).resolve().parent.parent

# Database Connection Parameters
PG_CONFIG: Dict[str, Any] = {
    "dbname": "autocare_dw",
    "user": "postgres",
    "host": "127.0.0.1",
    "port": 5432,
}

# Storage Directories
ML_DATA_DIR = BASE_DIR / "data" / "ml"
ML_MODELS_DIR = ML_DATA_DIR / "models"
ML_PREDICTIONS_DIR = ML_DATA_DIR / "predictions"
ML_DATASETS_DIR = ML_DATA_DIR / "datasets"

# Reproducibility
RANDOM_SEED = 42

# 1. Vehicle Failure-Risk Configuration
FAILURE_RISK_LOOKBACK_DAYS = 7  # Backward observation window
FAILURE_RISK_HORIZON_DAYS = 14  # Forward target realization window

# Approved Deterministic Issue Mapping
# In approved fact_service: 'Scheduled routine maintenance and multi-point inspection' is routine.
# All other issues are unscheduled component repairs/replacements/failures.
ROUTINE_MAINTENANCE_ISSUES: Set[str] = {
    "Scheduled routine maintenance and multi-point inspection"
}

BREAKDOWN_KEYWORDS: List[str] = [
    "repair",
    "replacement",
    "failure",
    "leak",
    "solenoid",
    "strut",
    "rotor",
    "pump",
    "alternator",
]


def is_breakdown_issue(issue: str) -> bool:
    """Deterministic rule evaluating whether an issue string represents an unscheduled failure."""
    if not issue:
        return False
    issue_str = str(issue).strip()
    if issue_str in ROUTINE_MAINTENANCE_ISSUES:
        return False
    lower = issue_str.lower()
    return any(kw in lower for kw in BREAKDOWN_KEYWORDS)


# 2. Sensor Anomaly Configuration
# Verified telemetry attributes only (ambient temperature and vehicle class are excluded)
SENSOR_FEATURES: List[str] = ["rpm", "temperature", "battery", "vibration"]
SEVERE_DIAGNOSTIC_SEVERITIES: Set[str] = {"CRITICAL", "HIGH"}
FAULT_EXCLUSION_PRE_HOURS = 2.0
FAULT_EXCLUSION_POST_HOURS = 6.0

# 3. Service Demand Forecasting Configuration
DEMAND_FORECAST_HORIZON_DAYS = 14
DEMAND_LAGS: List[int] = [7, 14]

# 4. Warranty Anomaly Configuration
WARRANTY_FEATURES: List[str] = [
    "claim_amount",
    "claim_amount_to_component_median_ratio",
    "component_claim_iqr_distance",
    "dealer_component_claim_volume_30d",
]

# Model Registry and Versions
MODEL_VERSIONS: Dict[str, str] = {
    "failure_risk": "v1.0.0",
    "sensor_anomaly": "v1.0.0",
    "demand_forecast": "v1.0.0",
    "warranty_anomaly": "v1.0.0",
}

# Ratified Acceptance Criteria & Operational Parameters
# Area 1: Failure Risk (Pooled repeated-cutoff evaluation)
FAILURE_RISK_POOLED_CUTOFFS: List[str] = [
    "2026-09-09",
    "2026-09-10",
    "2026-09-11",
]
FAILURE_RISK_ROC_AUC_THRESHOLD: float = 0.70
FAILURE_RISK_PR_AUC_THRESHOLD: float = 0.35
FAILURE_RISK_BRIER_THRESHOLD: float = 0.15

# Area 2: Sensor Anomaly (Empirical min-max normalization & Method B calibration)
SENSOR_CALIBRATION_METHOD: str = "STATISTICAL_TOLERANCE_MARGIN"
SENSOR_NOMINAL_FPR_TARGET: float = 0.02
SENSOR_CALIBRATION_PERCENTILE: float = 98.8
# Pre-specified conservative calibration target derived from a one-sided 95% statistical confidence-margin calculation for the finite validation sample (N_val=829)
SENSOR_NOMINAL_CALIBRATION_TARGET_FPR: float = 0.012
SENSOR_ALGO_LATENCY_TARGET_MS: float = 10.0      # Engineering measurement target
SENSOR_PIPELINE_LATENCY_TARGET_MS: float = 100.0  # Engineering measurement target

# Area 3: Service Demand Forecasting (Daily MAE & Lift)
DEMAND_MAE_THRESHOLD: float = 0.60
DEMAND_MIN_IMPROVEMENT_PCT: float = 0.10

# Area 4: Warranty Outlier Ranking (Unsupervised)
WARRANTY_SCOPE_NAME: str = "Unsupervised Warranty Outlier Ranking for Audit Prioritization"
WARRANTY_RANK_NORMALIZATION: bool = True
WARRANTY_TRIAGE_THRESHOLD_PROPOSED: float = 0.80  # Proposed initial threshold — not yet approved

