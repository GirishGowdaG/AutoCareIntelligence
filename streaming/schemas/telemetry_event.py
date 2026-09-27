"""Pydantic v2 schema for Vehicle Telemetry events.

Enforces business data contracts, validates metric bounds, and isolates transport metadata.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TelemetryEvent(BaseModel):
    """Vehicle Telemetry event payload with strict validation.
    
    Zero data invention: fields strictly match approved Bronze/Silver business attributes:
    vehicle_id, timestamp, rpm, temperature, battery, vibration.
    """
    model_config = ConfigDict(extra="forbid")

    # Business attributes
    vehicle_id: str = Field(..., min_length=1, description="Unique vehicle identifier (e.g., VH001)")
    timestamp: datetime = Field(..., description="Timestamp of the event (ISO 8601 or parsed datetime)")
    rpm: float = Field(..., ge=0, le=9000, description="Engine/motor RPM, bounded 0-9000")
    temperature: float = Field(..., ge=-40.0, le=150.0, description="Engine/motor temperature in Celsius")
    battery: float = Field(..., ge=0.0, le=100.0, description="Battery state of charge percentage (0-100)")
    vibration: float = Field(..., ge=0.0, le=50.0, description="Vibration amplitude (m/s^2 or g-force)")

    # Separated Transport Metadata (optional, never injected into analytical business models)
    producer_id: Optional[str] = Field(default=None, alias="_producer_id")
    sent_at: Optional[datetime] = Field(default=None, alias="_sent_at")
    kafka_topic: Optional[str] = Field(default=None, alias="_kafka_topic")
    kafka_partition: Optional[int] = Field(default=None, alias="_kafka_partition")
    kafka_offset: Optional[int] = Field(default=None, alias="_kafka_offset")

    @field_validator("vehicle_id")
    @classmethod
    def validate_vehicle_id(cls, v: str) -> str:
        v_str = str(v).strip()
        if not v_str:
            raise ValueError("vehicle_id cannot be blank")
        return v_str

    def to_business_dict(self) -> Dict[str, Any]:
        """Extract only approved business attributes, stripping transport metadata."""
        return {
            "vehicle_id": self.vehicle_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "rpm": float(self.rpm),
            "temperature": float(self.temperature),
            "battery": float(self.battery),
            "vibration": float(self.vibration),
        }

    def to_transport_dict(self) -> Dict[str, Any]:
        """Convert entire model to dictionary including transport metadata."""
        return self.model_dump(mode="json", by_alias=True)
