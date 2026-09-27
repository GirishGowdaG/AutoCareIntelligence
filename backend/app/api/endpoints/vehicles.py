"""Vehicle Fleet and Diagnostics Endpoints (Endpoints 2, 3, 4).

Strictly grounded in autocare_dw.dim_vehicle, dim_model, dim_dealer,
and staging.silver_diagnostics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.database import execute_read_query
from backend.app.core.security import require_roles, UserRole
from backend.app.schemas.vehicles import (
    VehicleListResponse,
    VehicleListItem,
    VehicleDetailResponse,
    VehicleDiagnosticsResponse,
    DiagnosticRecordItem,
)

router = APIRouter()

FLEET_ROLES = (UserRole.ADMIN, UserRole.DEALER_SERVICE_MANAGER, UserRole.FLEET_ANALYST)


@router.get("/vehicles", response_model=VehicleListResponse, summary="List Fleet Vehicles")
def list_vehicles(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: UserRole = Depends(require_roles(*FLEET_ROLES)),
) -> VehicleListResponse:
    """Retrieve paginated list of vehicles joined with conformed model and dealer dimensions."""
    where_clauses = []
    params = []

    if status_filter:
        where_clauses.append("v.status = %s")
        params.append(status_filter)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
    SELECT v.vehicle_id, v.variant, v.manufacture_year, v.manufacture_date, v.status,
           m.model_name, m.vehicle_class,
           d.dealer_name AS selling_dealer_name,
           COUNT(*) OVER() AS total_count
    FROM autocare_dw.dim_vehicle v
    LEFT JOIN autocare_dw.dim_model m ON v.model_key = m.model_key
    LEFT JOIN autocare_dw.dim_dealer d ON v.selling_dealer_key = d.dealer_key
    {where_sql}
    ORDER BY v.vehicle_id ASC
    LIMIT %s OFFSET %s;
    """
    rows = execute_read_query(query, params + [limit, offset])

    total = rows[0]["total_count"] if rows else 0
    items = [
        VehicleListItem(
            vehicle_id=r["vehicle_id"],
            variant=r["variant"],
            manufacture_year=r["manufacture_year"],
            manufacture_date=r["manufacture_date"],
            status=r["status"],
            model_name=r.get("model_name"),
            vehicle_class=r.get("vehicle_class"),
            selling_dealer_name=r.get("selling_dealer_name"),
        )
        for r in rows
    ]

    return VehicleListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleDetailResponse, summary="Get Vehicle Specification")
def get_vehicle(
    vehicle_id: str,
    current_user: UserRole = Depends(require_roles(*FLEET_ROLES)),
) -> VehicleDetailResponse:
    """Retrieve detailed vehicle specification from conformed dimensions."""
    query = """
    SELECT v.vehicle_id, v.variant, v.manufacture_year, v.manufacture_date, v.status,
           m.model_name, m.vehicle_class, m.powertrain_type, m.curb_weight_kg,
           d.dealer_id AS selling_dealer_id, d.dealer_name AS selling_dealer_name
    FROM autocare_dw.dim_vehicle v
    LEFT JOIN autocare_dw.dim_model m ON v.model_key = m.model_key
    LEFT JOIN autocare_dw.dim_dealer d ON v.selling_dealer_key = d.dealer_key
    WHERE v.vehicle_id = %s;
    """
    rows = execute_read_query(query, (vehicle_id,))
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle '{vehicle_id}' not found",
        )

    r = rows[0]
    return VehicleDetailResponse(
        vehicle_id=r["vehicle_id"],
        variant=r["variant"],
        manufacture_year=r["manufacture_year"],
        manufacture_date=r["manufacture_date"],
        status=r["status"],
        model_name=r.get("model_name"),
        vehicle_class=r.get("vehicle_class"),
        powertrain_type=r.get("powertrain_type"),
        curb_weight_kg=float(r["curb_weight_kg"]) if r.get("curb_weight_kg") is not None else None,
        selling_dealer_id=r.get("selling_dealer_id"),
        selling_dealer_name=r.get("selling_dealer_name"),
    )


@router.get("/vehicles/{vehicle_id}/diagnostics", response_model=VehicleDiagnosticsResponse, summary="Get Vehicle Diagnostic History")
def get_vehicle_diagnostics(
    vehicle_id: str,
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
    current_user: UserRole = Depends(require_roles(*FLEET_ROLES)),
) -> VehicleDiagnosticsResponse:
    """Retrieve diagnostic trouble code (DTC) history for a vehicle from staging.silver_diagnostics."""
    where_clauses = ["vehicle_id = %s"]
    params = [vehicle_id]

    if severity:
        where_clauses.append("UPPER(severity) = UPPER(%s)")
        params.append(severity)

    where_sql = f"WHERE {' AND '.join(where_clauses)}"

    query = f"""
    SELECT diagnostic_id, vehicle_id, timestamp, code AS dtc_code, component, severity
    FROM staging.silver_diagnostics
    {where_sql}
    ORDER BY timestamp DESC
    LIMIT %s;
    """
    rows = execute_read_query(query, params + [limit])

    diagnostics = [
        DiagnosticRecordItem(
            diagnostic_id=r["diagnostic_id"],
            vehicle_id=r["vehicle_id"],
            timestamp=r["timestamp"],
            dtc_code=r["dtc_code"],
            component=r.get("component"),
            severity=r["severity"],
        )
        for r in rows
    ]

    return VehicleDiagnosticsResponse(
        vehicle_id=vehicle_id,
        total_records=len(diagnostics),
        diagnostics=diagnostics,
    )
