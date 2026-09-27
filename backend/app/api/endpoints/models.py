"""Machine Learning Model Governance & Status Endpoint (Endpoint 11).

Reports ratification status, metrics, and threshold governance across the 4 ML areas.
Area 2 threshold is loaded dynamically from the Phase 5 model manifest.
"""

from fastapi import APIRouter, Depends

from backend.app.core.security import require_roles, UserRole
from backend.app.core.thresholds import load_frozen_sensor_threshold
from backend.app.schemas.ml import ModelGovernanceResponse, ModelStatusItem

router = APIRouter()

ANALYST_ADMIN_ROLES = (UserRole.ADMIN, UserRole.FLEET_ANALYST)


@router.get("/models/status", response_model=ModelGovernanceResponse, summary="ML Model Governance & Thresholds Status")
def get_model_status(
    current_user: UserRole = Depends(require_roles(*ANALYST_ADMIN_ROLES)),
) -> ModelGovernanceResponse:
    """Retrieve verified governance state and ratified performance metrics for all 4 ML models."""
    frozen_sensor_threshold = load_frozen_sensor_threshold()

    return ModelGovernanceResponse(
        area_1_failure_risk=ModelStatusItem(
            model_type="LightGBM Classifier",
            version="v1.0.0",
            status="RATIFIED",
            threshold_type="PROPOSED_INITIAL",
            threshold_value=0.70,
            calibration_basis="Physical Vehicle Split (50 vehicles, N=150)",
            metrics={
                "roc_auc": 0.8452,
                "pr_auc": 0.9761,
                "brier_score": 0.0812,
            },
        ),
        area_2_sensor_anomaly=ModelStatusItem(
            model_type="IsolationForest",
            version="v1.0.0",
            status="FROZEN_APPROVED",
            threshold_type="FROZEN_APPROVED",
            threshold_value=frozen_sensor_threshold,
            calibration_basis="Phase 5 Method B (98.8th Validation Percentile)",
            metrics={
                "held_out_n": 830,
                "false_alarms": 13,
                "nominal_fpr": 0.0157,
                "acceptance_gate": 0.0200,
            },
        ),
        area_3_service_demand=ModelStatusItem(
            model_type="Prophet",
            version="v1.0.0",
            status="ACCEPTED",
            threshold_type="PROPOSED_INITIAL",
            threshold_value=0.25,
            calibration_basis="Dealership-level rolling temporal forecast",
            metrics={
                "mae": 0.4281,
                "lift": 0.1676,
            },
        ),
        area_4_warranty_anomaly=ModelStatusItem(
            model_type="IsolationForest (Unsupervised)",
            version="v1.0.0",
            status="ACCEPTED",
            threshold_type="PROPOSED_INITIAL",
            threshold_value=0.80,
            calibration_basis="Forensic audit prioritization ranking",
            metrics={
                "audit_prioritization": True,
                "fraud_allegation_disclaimer": "Zero claims of fraud or misconduct",
            },
        ),
    )
