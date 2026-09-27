"""Server-Sent Events (SSE) Streaming Endpoint (Endpoint 12).

Provides real-time event stream for telemetry pulses, action audit notifications,
and 15-second keepalive heartbeats.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse

from backend.app.core.security import require_roles, UserRole
from backend.app.services.sse_service import SSEEventStreamer

router = APIRouter()

ANALYST_ADMIN_ROLES = (UserRole.ADMIN, UserRole.FLEET_ANALYST)


@router.get("/stream/events", summary="Real-Time Server-Sent Events Stream")
def stream_events(
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    api_key: Optional[str] = Query(None, description="Browser EventSource query-param authentication fallback"),
    max_events: Optional[int] = Query(None, ge=1, le=1000, description="Optional pulse limit (primarily for testing)"),
    current_user: UserRole = Depends(require_roles(*ANALYST_ADMIN_ROLES)),
) -> StreamingResponse:
    """Stream real-time telemetry, audit action notifications, and keepalive heartbeats.
    
    Permits api_key query-parameter solely on this endpoint to facilitate browser EventSource clients.
    """
    streamer = SSEEventStreamer(last_event_id=last_event_id)

    return StreamingResponse(
        streamer.stream_events(max_events=max_events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
