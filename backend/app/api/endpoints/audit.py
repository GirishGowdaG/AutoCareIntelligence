"""Automated Action Audit Logs Endpoint (Endpoint 9).

Admin-only endpoint exposing transactional decision logs from Stage 1 automation.
Strictly preserves stored Stage 1 contract (DELIVERED/MOCK_LOGGED/FAILED, VEHICLE/DEALER/CLAIM).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from backend.app.core.database import execute_read_query
from backend.app.core.security import require_roles, UserRole
from backend.app.schemas.audit import ActionLogResponse, ActionLogItem

router = APIRouter()


@router.get("/audit/actions", response_model=ActionLogResponse, summary="Automated Action Audit Logs")
def get_action_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    rule_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    delivery_status: Optional[str] = Query(None),
    current_user: UserRole = Depends(require_roles(UserRole.ADMIN)),
) -> ActionLogResponse:
    """Retrieve automated action audit logs from ml_inference.action_logs.
    
    Restricted strictly to Admin role (all other roles receive 403 Forbidden).
    """
    where_clauses = []
    params = []

    if rule_id:
        where_clauses.append("rule_id = %s")
        params.append(rule_id.upper())

    if entity_type:
        where_clauses.append("entity_type = %s")
        params.append(entity_type.upper())

    if delivery_status:
        where_clauses.append("delivery_status = %s")
        params.append(delivery_status.upper())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
    SELECT action_id, rule_id, entity_type, entity_id, trigger_timestamp,
           trigger_value, threshold_applied, action_taken, channel_dispatched,
           delivery_status, idempotency_key, payload, created_at,
           COUNT(*) OVER() AS total_count
    FROM ml_inference.action_logs
    {where_sql}
    ORDER BY trigger_timestamp DESC
    LIMIT %s OFFSET %s;
    """
    rows = execute_read_query(query, params + [limit, offset])

    total = rows[0]["total_count"] if rows else 0
    items = [
        ActionLogItem(
            action_id=str(r["action_id"]),
            rule_id=r["rule_id"],
            entity_type=r["entity_type"],
            entity_id=r["entity_id"],
            trigger_timestamp=r["trigger_timestamp"],
            trigger_value=float(r["trigger_value"]),
            threshold_applied=float(r["threshold_applied"]),
            action_taken=r["action_taken"],
            channel_dispatched=r["channel_dispatched"],
            delivery_status=r["delivery_status"],
            idempotency_key=r["idempotency_key"],
            payload=r.get("payload"),
            created_at=r.get("created_at"),
        )
        for r in rows
    ]

    return ActionLogResponse(total=total, limit=limit, offset=offset, items=items)
