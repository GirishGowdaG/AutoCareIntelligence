"""Main API Router aggregating all 12 Phase 6 Stage 2 endpoints under /api/v1."""

from fastapi import APIRouter

from backend.app.api.endpoints import (
    health,
    vehicles,
    predictions,
    audit,
    metrics,
    models,
    stream,
)

api_router = APIRouter(prefix="/api/v1")

# Endpoint 1: Health (Public)
api_router.include_router(health.router, tags=["Health"])

# Endpoints 2, 3, 4: Vehicles and Diagnostics
api_router.include_router(vehicles.router, tags=["Vehicles & Diagnostics"])

# Endpoints 5, 6, 7, 8: ML Predictions, Forecasts, and Anomalies
api_router.include_router(predictions.router, tags=["ML Predictions & Forecasts"])

# Endpoint 9: Action Audit Logs
api_router.include_router(audit.router, tags=["Action Audit Logs"])

# Endpoint 10: Fleet Metrics Overview
api_router.include_router(metrics.router, tags=["Fleet Metrics"])

# Endpoint 11: Model Governance Status
api_router.include_router(models.router, tags=["Model Governance"])

# Endpoint 12: Real-Time SSE Stream
api_router.include_router(stream.router, tags=["Event Streaming"])
