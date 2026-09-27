"""Pydantic schemas for Automated Action Audit Logs (Stage 1 Automation).

Strictly enforces verified Stage 1 enumerations:
- delivery_status: DELIVERED | MOCK_LOGGED | FAILED
- entity_type: VEHICLE | DEALER | CLAIM
- rule_id: RULE_1_FAILURE_RISK | RULE_2_SENSOR_ANOMALY | RULE_2_SEVERE_DTC | RULE_3_DEMAND_SURGE | RULE_4_WARRANTY_AUDIT
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DeliveryStatusEnum(str, Enum):
    DELIVERED = "DELIVERED"
    MOCK_LOGGED = "MOCK_LOGGED"
    FAILED = "FAILED"


class EntityTypeEnum(str, Enum):
    VEHICLE = "VEHICLE"
    DEALER = "DEALER"
    CLAIM = "CLAIM"


class RuleIdEnum(str, Enum):
    RULE_1_FAILURE_RISK = "RULE_1_FAILURE_RISK"
    RULE_2_SENSOR_ANOMALY = "RULE_2_SENSOR_ANOMALY"
    RULE_2_SEVERE_DTC = "RULE_2_SEVERE_DTC"
    RULE_3_DEMAND_SURGE = "RULE_3_DEMAND_SURGE"
    RULE_4_WARRANTY_AUDIT = "RULE_4_WARRANTY_AUDIT"


class ActionLogItem(BaseModel):
    action_id: str
    rule_id: str
    entity_type: str
    entity_id: str
    trigger_timestamp: datetime
    trigger_value: float
    threshold_applied: float
    action_taken: str
    channel_dispatched: str
    delivery_status: str
    idempotency_key: str
    payload: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class ActionLogResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ActionLogItem]
