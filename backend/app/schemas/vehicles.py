"""Pydantic schemas for Vehicle Fleet and Diagnostics endpoints.

Strictly mapped to conformed autocare_dw.dim_vehicle, dim_model, dim_dealer,
and staging.silver_diagnostics tables.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class VehicleListItem(BaseModel):
    """Vehicle summary item returned in fleet listings."""
    vehicle_id: str = Field(..., description="Unique vehicle identifier")
    variant: str = Field(..., description="Vehicle trim/variant")
    manufacture_year: int = Field(..., description="Manufacturing calendar year")
    manufacture_date: date = Field(..., description="Manufacturing date")
    status: str = Field(..., description="Vehicle operational status")
    model_name: Optional[str] = Field(None, description="Conformed model name from dim_model")
    vehicle_class: Optional[str] = Field(None, description="Vehicle engineering classification")
    selling_dealer_name: Optional[str] = Field(None, description="Selling dealership name from dim_dealer")


class VehicleListResponse(BaseModel):
    """Paginated list of fleet vehicles."""
    total: int
    limit: int
    offset: int
    items: List[VehicleListItem]


class VehicleDetailResponse(BaseModel):
    """Comprehensive vehicle specifications and metadata."""
    vehicle_id: str
    variant: str
    manufacture_year: int
    manufacture_date: date
    status: str
    model_name: Optional[str] = None
    vehicle_class: Optional[str] = None
    powertrain_type: Optional[str] = None
    curb_weight_kg: Optional[float] = None
    selling_dealer_id: Optional[str] = None
    selling_dealer_name: Optional[str] = None


class DiagnosticRecordItem(BaseModel):
    """Individual diagnostic trouble code (DTC) event record."""
    diagnostic_id: str
    vehicle_id: str
    timestamp: datetime
    dtc_code: str
    component: Optional[str] = None
    severity: str


class VehicleDiagnosticsResponse(BaseModel):
    """Diagnostic history response for a specific vehicle."""
    vehicle_id: str
    total_records: int
    diagnostics: List[DiagnosticRecordItem]
