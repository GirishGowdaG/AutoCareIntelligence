"""Pydantic v2 schema for Vehicle Diagnostics events.

Enforces business data contracts, validates DTC severity levels, and isolates transport metadata.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class DiagnosticEvent(BaseModel):
    """Vehicle Diagnostic Trouble Code (DTC) event payload with strict validation.
    
    Zero data invention: fields strictly match approved Bronze/Silver business attributes:
    vehicle_id, timestamp, code, component, severity.
    """
    model_config = ConfigDict(extra="forbid")

    # Business attributes
    vehicle_id: str = Field(..., min_length=1, description="Unique vehicle identifier (e.g., VH001)")
    timestamp: datetime = Field(..., description="Timestamp of the diagnostic event")
    code: str = Field(..., min_length=2, max_length=10, description="DTC diagnostic trouble code (e.g., P0300)")
    component: str = Field(..., min_length=1, description="Vehicle component affected")
    severity: str = Field(..., description="DTC severity rating (e.g., LOW, MEDIUM, HIGH, CRITICAL, Warning)")

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

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v_str = str(v).strip().upper()
        if not v_str:
            raise ValueError("diagnostic code cannot be blank")
        return v_str

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        v_str = str(v).strip().upper()
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL", "WARNING", "INFO"}
        if v_str not in allowed:
            raise ValueError(f"severity '{v}' must be one of {sorted(allowed)}")
        return v_str

    def to_business_dict(self) -> Dict[str, Any]:
        """Extract only approved business attributes, stripping transport metadata."""
        return {
            "vehicle_id": self.vehicle_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "code": self.code,
            "component": self.component,
            "severity": self.severity,
        }

    def to_transport_dict(self) -> Dict[str, Any]:
        """Convert entire model to dictionary including transport metadata."""
        return self.model_dump(mode="json", by_alias=True)
