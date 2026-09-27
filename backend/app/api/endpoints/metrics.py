"""Fleet Aggregate Metrics Overview Endpoint (Endpoint 10).

Computes high-level fleet health KPIs across data warehouse and ML schemas.
"""

from fastapi import APIRouter, Depends

from backend.app.core.database import execute_read_query, execute_read_scalar
from backend.app.core.security import require_roles, UserRole
from backend.app.schemas.ml import FleetMetricsOverviewResponse

router = APIRouter()

ALL_ROLES = (UserRole.ADMIN, UserRole.DEALER_SERVICE_MANAGER, UserRole.FLEET_ANALYST)


@router.get("/metrics/overview", response_model=FleetMetricsOverviewResponse, summary="Fleet Aggregate KPI Summary")
def get_fleet_metrics_overview(
    current_user: UserRole = Depends(require_roles(*ALL_ROLES)),
) -> FleetMetricsOverviewResponse:
    """Retrieve aggregate fleet statistics and high-level health metrics."""
    total_vehicles = execute_read_scalar("SELECT COUNT(DISTINCT vehicle_id) FROM autocare_dw.dim_vehicle WHERE vehicle_key > 0;") or 0

    critical_risk = execute_read_scalar(
        "SELECT COUNT(*) FROM ml_inference.vehicle_failure_predictions WHERE risk_tier = 'CRITICAL';"
    ) or 0

    sensor_anomalies = execute_read_scalar(
        "SELECT COUNT(*) FROM ml_inference.sensor_anomalies WHERE is_anomaly = TRUE;"
    ) or 0

    warranty_outliers = execute_read_scalar(
        "SELECT COUNT(*) FROM ml_inference.warranty_anomalies;"
    ) or 0

    action_stats = execute_read_query(
        "SELECT COUNT(*) AS total_actions, MAX(created_at) AS last_ts FROM ml_inference.action_logs;"
    )

    actions_total = action_stats[0]["total_actions"] if action_stats else 0
    last_ts = action_stats[0]["last_ts"] if action_stats else None

    return FleetMetricsOverviewResponse(
        total_vehicles=int(total_vehicles),
        critical_risk_vehicles=int(critical_risk),
        sensor_anomalies_detected=int(sensor_anomalies),
        warranty_outliers_flagged=int(warranty_outliers),
        actions_logged_total=int(actions_total),
        last_action_timestamp=last_ts,
    )
