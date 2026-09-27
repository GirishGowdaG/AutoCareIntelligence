"""Health and System Status Endpoint (Endpoint 1).

Public, unauthenticated endpoint for container readiness/liveness probes
and service health monitoring.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter

from backend.app.core.config import get_app_settings
from backend.app.core.database import execute_read_scalar
from backend.app.core.thresholds import SENSOR_MANIFEST_PATH

router = APIRouter()


@router.get("/health", summary="Service Health & Connectivity Status")
def get_health() -> Dict[str, Any]:
    """Public health check probing PostgreSQL database connectivity and model manifest availability."""
    settings = get_app_settings()
    now = datetime.now(timezone.utc).isoformat()

    # 1. Database probe
    db_status = "disconnected"
    try:
        val = execute_read_scalar("SELECT 1;")
        if val == 1:
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # 2. Model manifest probe
    model_status = "loaded" if SENSOR_MANIFEST_PATH.exists() else "missing_manifest"

    overall_status = "healthy" if (db_status == "connected" and model_status == "loaded") else "degraded"

    return {
        "status": overall_status,
        "timestamp": now,
        "version": settings.app_version,
        "components": {
            "database": db_status,
            "models": model_status,
            "kafka_broker": "mock_fallback",
        },
    }
