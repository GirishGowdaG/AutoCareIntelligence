"""Automation Engine Configuration and Governance Thresholds.

Explicitly separates FROZEN / RATIFIED Phase 5 ML thresholds from
PROPOSED INITIAL THRESHOLDS (configurable engineering proposals).
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

from ml.config import PG_CONFIG, ML_MODELS_DIR

BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# 1. FROZEN / RATIFIED THRESHOLD (IMMUTABLE PHASE 5 ACCEPTANCE BASELINE)
# ==============================================================================
# Derived exclusively from Phase 5 Method B Statistical Tolerance-Margin Calibration
# on the nominal validation split (N_val=829, 98.8th percentile, target FPR=0.012).
# Evaluated and formally ratified on the untouched held-out test split (13/830 = 1.57%).
# This value MUST NOT be tuned, recalibrated, or overridden by environment variables.
def _load_governed_sensor_threshold() -> float:
    manifest_path = ML_MODELS_DIR / "sensor_anomaly" / "v1.0.0" / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data["hyperparameters"]["calibrated_threshold"])
        except Exception:
            pass
    return 0.838357

FROZEN_SENSOR_ANOMALY_THRESHOLD: float = _load_governed_sensor_threshold()
SENSOR_CONSECUTIVE_ANOMALIES_REQUIRED: int = int(os.getenv("AUTOMATION_SENSOR_CONSECUTIVE_ANOMALIES", "3"))

# ==============================================================================
# 2. PROPOSED INITIAL THRESHOLDS (CONFIGURABLE ENGINEERING PROPOSALS)
# ==============================================================================
# The following thresholds are operational decision triggers and NOT Phase 5 ML
# acceptance criteria. They are configurable via environment variables and can be
# tuned by operational policy without retraining or altering Phase 5 ML models.

# Rule 1: High Failure Risk Trigger (P(failure) >= 0.70)
# Purpose: High-priority service recommendation & dealer inspection dispatch
# Governance Status: PROPOSED INITIAL THRESHOLD (Engineering proposal for top risk tier)
PROPOSED_FAILURE_RISK_TRIGGER: float = float(os.getenv("AUTOMATION_FAILURE_RISK_TRIGGER", "0.70"))

# Rule 3: Service Demand Surge Percentage (> 25% over dealer baseline capacity)
# Purpose: Dealer capacity constraint warning & high-failure parts replenishment
# Governance Status: PROPOSED INITIAL THRESHOLD (Engineering proposal for +1.5 sigma demand spike)
PROPOSED_DEMAND_SURGE_PCT: float = float(os.getenv("AUTOMATION_DEMAND_SURGE_PCT", "0.25"))

# Rule 4: Warranty Outlier Audit Trigger (Percentile Rank >= 0.80)
# Purpose: Prioritizes top 20% of anomalous warranty claims for forensic audit review
# Governance Status: PROPOSED INITIAL THRESHOLD (Audit sampling proposal; zero fraud claims)
PROPOSED_WARRANTY_AUDIT_PERCENTILE: float = float(os.getenv("AUTOMATION_WARRANTY_AUDIT_PERCENTILE", "0.80"))

# ==============================================================================
# 3. NOTIFICATION DISPATCHER CONFIGURATION
# ==============================================================================
# Slack Incoming Webhook (Real dispatch with local mock fallback)
SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#telemetry-alerts")

# SMTP / Email Configuration (Real MIME/HTML dispatch with local mock fallback)
SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM: str = os.getenv("SMTP_FROM", "alerts@autocare-intelligence.com")
SMTP_TO_SERVICE_MANAGER: str = os.getenv("SMTP_TO_SERVICE_MANAGER", "service-manager@dealership.com")
SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# Timeout limits for external dispatch (prevents blocking ingestion stream)
DISPATCH_TIMEOUT_SECONDS: float = float(os.getenv("AUTOMATION_DISPATCH_TIMEOUT", "5.0"))

# ==============================================================================
# 4. KAFKA STREAMING & CONSUMER GROUP CONFIGURATION
# ==============================================================================
# Preserves Phase 4 Kafka KRaft architecture with dedicated automation consumer group
KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TELEMETRY_TOPIC: str = os.getenv("KAFKA_TELEMETRY_TOPIC", "vehicle-telemetry")
KAFKA_DIAGNOSTICS_TOPIC: str = os.getenv("KAFKA_DIAGNOSTICS_TOPIC", "diagnostic-events")
KAFKA_AUTOMATION_GROUP_ID: str = os.getenv("KAFKA_AUTOMATION_GROUP_ID", "autocare-automation-group")
