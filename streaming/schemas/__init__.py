"""Streaming event schemas for AutoCare Intelligence."""

from streaming.schemas.telemetry_event import TelemetryEvent
from streaming.schemas.diagnostic_event import DiagnosticEvent

__all__ = ["TelemetryEvent", "DiagnosticEvent"]
