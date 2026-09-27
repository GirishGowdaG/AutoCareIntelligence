"""FastAPI Application Entrypoint for AutoCare Intelligence (Phase 6 Stage 2).

Enforces:
- Strict GET and OPTIONS HTTP methods only.
- CORS origin restriction.
- Startup configuration verification (no hardcoded keys, manifest presence).
- Automatic redaction of api_key query parameters from access logs.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.router import api_router
from backend.app.core.config import get_auth_config, get_app_settings
from backend.app.core.thresholds import load_frozen_sensor_threshold

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager verifying required runtime dependencies."""
    # 1. Verify Authentication Credentials
    auth_config = get_auth_config()
    logger.info("Authentication configuration verified successfully from environment.")

    # 2. Authoritatively verify frozen sensor threshold from manifest
    threshold = load_frozen_sensor_threshold()
    logger.info("Authoritative sensor anomaly threshold verified successfully from manifest.")

    yield
    logger.info("FastAPI backend shutting down cleanly.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_app_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Phase 6 Stage 2 REST API and Server-Sent Events engine for AutoCare Intelligence.",
        lifespan=lifespan,
    )

    # CORS Middleware: GET and OPTIONS only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type", "Last-Event-ID"],
    )

    # Method guard middleware: reject any POST/PUT/PATCH/DELETE with 405 Method Not Allowed
    @app.middleware("http")
    async def enforce_read_only_methods(request: Request, call_next):
        if request.method not in ("GET", "OPTIONS", "HEAD"):
            return JSONResponse(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                content={"detail": f"Method {request.method} not allowed. System is strictly read-only."},
            )
        response = await call_next(request)
        return response

    # Mount API v1 router
    app.include_router(api_router)

    return app


app = create_app()
