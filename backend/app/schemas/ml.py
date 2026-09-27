"""Pydantic schemas for Machine Learning Predictions, Forecasts, and Model Governance."""

from datetime import date, datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# Area 1: Failure Risk
class FailureRiskItem(BaseModel):
    prediction_id: str
    vehicle_id: str
    cutoff_date: date
    risk_score: float
    risk_tier: str
    top_features: Optional[Dict[str, Any]] = None
    model_version: str
    created_at: Optional[datetime] = None


class FailureRiskResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[FailureRiskItem]


# Area 2: Sensor Anomalies
class SensorAnomalyItem(BaseModel):
    anomaly_id: str
    vehicle_id: str
    window_timestamp: datetime
    anomaly_score: float
    is_anomaly: bool
    anomalous_features: Optional[Dict[str, Any]] = None
    model_version: str
    detected_at: Optional[datetime] = None


class SensorAnomalyResponse(BaseModel):
    total: int
    frozen_threshold: float = Field(..., description="Authoritative threshold dynamically loaded from manifest")
    limit: int
    offset: int
    items: List[SensorAnomalyItem]


# Area 3: Service Demand Forecasts
class DemandForecastItem(BaseModel):
    forecast_id: str
    dealer_id: str
    forecast_date: date
    predicted_volume: float
    lower_bound_80: float
    upper_bound_80: float
    model_version: str
    generated_at: Optional[datetime] = None


class DemandForecastResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[DemandForecastItem]


# Area 4: Warranty Anomalies
class WarrantyAnomalyItem(BaseModel):
    anomaly_id: str
    claim_id: str
    dealer_id: Optional[str] = None
    component_id: Optional[str] = None
    claim_amount: float
    anomaly_score: float
    outlier_reasons: Optional[Dict[str, Any]] = None
    model_version: str
    flagged_at: Optional[datetime] = None


class WarrantyAnomalyResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[WarrantyAnomalyItem]


# Fleet Metrics Overview
class FleetMetricsOverviewResponse(BaseModel):
    total_vehicles: int
    critical_risk_vehicles: int
    sensor_anomalies_detected: int
    warranty_outliers_flagged: int
    actions_logged_total: int
    last_action_timestamp: Optional[datetime] = None


# ML Model Governance Status
class ModelStatusItem(BaseModel):
    model_type: str
    version: str
    status: str
    threshold_type: str
    threshold_value: Optional[float] = None
    calibration_basis: Optional[str] = None
    metrics: Dict[str, Any]


class ModelGovernanceResponse(BaseModel):
    area_1_failure_risk: ModelStatusItem
    area_2_sensor_anomaly: ModelStatusItem
    area_3_service_demand: ModelStatusItem
    area_4_warranty_anomaly: ModelStatusItem
