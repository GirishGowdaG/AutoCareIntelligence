"""Machine Learning Predictions, Forecasts, and Anomalies Endpoints (Endpoints 5, 6, 7, 8).

Implements:
- Endpoint 5: /predictions/failure-risk (Admin, FleetAnalyst)
- Endpoint 6: /predictions/sensor-anomalies (Admin, FleetAnalyst)
- Endpoint 7: /forecasts/service-demand (Admin, DealerServiceManager, FleetAnalyst)
- Endpoint 8: /anomalies/warranty (Admin, FleetAnalyst ONLY; DealerServiceManager -> 403 Forbidden)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from backend.app.core.database import execute_read_query
from backend.app.core.security import require_roles, UserRole
from backend.app.core.thresholds import load_frozen_sensor_threshold
from backend.app.schemas.ml import (
    FailureRiskResponse,
    FailureRiskItem,
    SensorAnomalyResponse,
    SensorAnomalyItem,
    DemandForecastResponse,
    DemandForecastItem,
    WarrantyAnomalyResponse,
    WarrantyAnomalyItem,
)

router = APIRouter()

ANALYST_ADMIN_ROLES = (UserRole.ADMIN, UserRole.FLEET_ANALYST)
ALL_ROLES = (UserRole.ADMIN, UserRole.DEALER_SERVICE_MANAGER, UserRole.FLEET_ANALYST)


# --------------------------------------------------------------------------
# Endpoint 5: Area 1 Failure Risk Predictions
# --------------------------------------------------------------------------
@router.get("/predictions/failure-risk", response_model=FailureRiskResponse, summary="Area 1 Vehicle Failure Risk Scores")
def get_failure_risk_predictions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    risk_tier: Optional[str] = Query(None),
    current_user: UserRole = Depends(require_roles(*ANALYST_ADMIN_ROLES)),
) -> FailureRiskResponse:
    """Retrieve pre-computed vehicle failure risk predictions from ml_inference."""
    where_clauses = []
    params = []

    if risk_tier:
        where_clauses.append("risk_tier = %s")
        params.append(risk_tier.upper())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
    SELECT prediction_id, vehicle_id, cutoff_date, risk_score, risk_tier,
           top_features, model_version, created_at,
           COUNT(*) OVER() AS total_count
    FROM ml_inference.vehicle_failure_predictions
    {where_sql}
    ORDER BY risk_score DESC
    LIMIT %s OFFSET %s;
    """
    rows = execute_read_query(query, params + [limit, offset])

    total = rows[0]["total_count"] if rows else 0
    items = [
        FailureRiskItem(
            prediction_id=str(r["prediction_id"]),
            vehicle_id=r["vehicle_id"],
            cutoff_date=r["cutoff_date"],
            risk_score=float(r["risk_score"]),
            risk_tier=r["risk_tier"],
            top_features=r.get("top_features"),
            model_version=r["model_version"],
            created_at=r.get("created_at"),
        )
        for r in rows
    ]

    return FailureRiskResponse(total=total, limit=limit, offset=offset, items=items)


# --------------------------------------------------------------------------
# Endpoint 6: Area 2 Sensor Anomalies
# --------------------------------------------------------------------------
@router.get("/predictions/sensor-anomalies", response_model=SensorAnomalyResponse, summary="Area 2 Detected Sensor Anomalies")
def get_sensor_anomalies(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_anomaly: Optional[bool] = Query(None),
    current_user: UserRole = Depends(require_roles(*ANALYST_ADMIN_ROLES)),
) -> SensorAnomalyResponse:
    """Retrieve detected sensor anomalies from ml_inference.
    
    Includes frozen_threshold dynamically loaded from the Phase 5 model manifest.
    """
    frozen_threshold = load_frozen_sensor_threshold()

    where_clauses = []
    params = []

    if is_anomaly is not None:
        where_clauses.append("is_anomaly = %s")
        params.append(is_anomaly)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
    SELECT anomaly_id, vehicle_id, window_timestamp, anomaly_score,
           is_anomaly, anomalous_features, model_version, detected_at,
           COUNT(*) OVER() AS total_count
    FROM ml_inference.sensor_anomalies
    {where_sql}
    ORDER BY window_timestamp DESC
    LIMIT %s OFFSET %s;
    """
    rows = execute_read_query(query, params + [limit, offset])

    total = rows[0]["total_count"] if rows else 0
    items = [
        SensorAnomalyItem(
            anomaly_id=str(r["anomaly_id"]),
            vehicle_id=r["vehicle_id"],
            window_timestamp=r["window_timestamp"],
            anomaly_score=float(r["anomaly_score"]),
            is_anomaly=r["is_anomaly"],
            anomalous_features=r.get("anomalous_features"),
            model_version=r["model_version"],
            detected_at=r.get("detected_at"),
        )
        for r in rows
    ]

    return SensorAnomalyResponse(
        total=total,
        frozen_threshold=frozen_threshold,
        limit=limit,
        offset=offset,
        items=items,
    )


# --------------------------------------------------------------------------
# Endpoint 7: Area 3 Service Demand Forecasts
# --------------------------------------------------------------------------
@router.get("/forecasts/service-demand", response_model=DemandForecastResponse, summary="Area 3 Dealership Demand Forecasts")
def get_service_demand_forecasts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    dealer_id: Optional[str] = Query(None),
    current_user: UserRole = Depends(require_roles(*ALL_ROLES)),
) -> DemandForecastResponse:
    """Retrieve service demand volume forecasts from ml_inference."""
    where_clauses = []
    params = []

    if dealer_id:
        where_clauses.append("dealer_id = %s")
        params.append(dealer_id)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
    SELECT forecast_id, dealer_id, forecast_date, predicted_volume,
           lower_bound_80, upper_bound_80, model_version, generated_at,
           COUNT(*) OVER() AS total_count
    FROM ml_inference.service_demand_forecasts
    {where_sql}
    ORDER BY forecast_date ASC
    LIMIT %s OFFSET %s;
    """
    rows = execute_read_query(query, params + [limit, offset])

    total = rows[0]["total_count"] if rows else 0
    items = [
        DemandForecastItem(
            forecast_id=str(r["forecast_id"]),
            dealer_id=r["dealer_id"],
            forecast_date=r["forecast_date"],
            predicted_volume=float(r["predicted_volume"]),
            lower_bound_80=float(r["lower_bound_80"]),
            upper_bound_80=float(r["upper_bound_80"]),
            model_version=r["model_version"],
            generated_at=r.get("generated_at"),
        )
        for r in rows
    ]

    return DemandForecastResponse(total=total, limit=limit, offset=offset, items=items)


# --------------------------------------------------------------------------
# Endpoint 8: Area 4 Warranty Claim Anomalies
# (Strictly Admin + FleetAnalyst ONLY; DealerServiceManager -> 403 Forbidden)
# --------------------------------------------------------------------------
@router.get("/anomalies/warranty", response_model=WarrantyAnomalyResponse, summary="Area 4 Forensic Warranty Claim Anomalies")
def get_warranty_anomalies(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    dealer_id: Optional[str] = Query(None),
    current_user: UserRole = Depends(require_roles(*ANALYST_ADMIN_ROLES)),
) -> WarrantyAnomalyResponse:
    """Retrieve warranty claim forensic outlier scores from ml_inference.
    
    Governance rule: Strictly audit prioritization. Zero claims of fraud or misconduct.
    Access restricted to Admin and FleetAnalyst roles (DealerServiceManager denied with 403).
    """
    where_clauses = []
    params = []

    if dealer_id:
        where_clauses.append("dealer_id = %s")
        params.append(dealer_id)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
    SELECT anomaly_id, claim_id, dealer_id, component_id, claim_amount,
           anomaly_score, outlier_reasons, model_version, flagged_at,
           COUNT(*) OVER() AS total_count
    FROM ml_inference.warranty_anomalies
    {where_sql}
    ORDER BY anomaly_score DESC
    LIMIT %s OFFSET %s;
    """
    rows = execute_read_query(query, params + [limit, offset])

    total = rows[0]["total_count"] if rows else 0
    items = [
        WarrantyAnomalyItem(
            anomaly_id=str(r["anomaly_id"]),
            claim_id=r["claim_id"],
            dealer_id=r.get("dealer_id"),
            component_id=r.get("component_id"),
            claim_amount=float(r["claim_amount"]),
            anomaly_score=float(r["anomaly_score"]),
            outlier_reasons=r.get("outlier_reasons"),
            model_version=r["model_version"],
            flagged_at=r.get("flagged_at"),
        )
        for r in rows
    ]

    return WarrantyAnomalyResponse(total=total, limit=limit, offset=offset, items=items)
