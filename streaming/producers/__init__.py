"""Streaming producers for AutoCare Intelligence."""

from streaming.producers.telemetry_producer import TelemetryProducer
from streaming.producers.diagnostics_producer import DiagnosticsProducer

__all__ = ["TelemetryProducer", "DiagnosticsProducer"]
