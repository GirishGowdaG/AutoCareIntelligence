"""Pydantic schemas for Server-Sent Events (SSE) streaming data."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SSEEventPayload(BaseModel):
    """Generic payload for an SSE event."""
    event_type: str
    source: str = Field(..., description="'kafka', 'synthetic_demo', or 'action_logs'")
    timestamp: datetime
    data: Dict[str, Any]
