"""Rule-Based Automation Engine for AutoCare Intelligence (Phase 6).

Implements the four assignment-mandated domain automation rules:
- Rule 1: High Vehicle Failure Risk (Email + Slack)
- Rule 2: Critical Telemetry Anomaly & Severe DTC (Slack)
- Rule 3: Service Demand Surge & Capacity Warning (Email + Slack)
- Rule 4: Warranty Outlier Audit Prioritization (Internal Action Log)

Strictly decouples frozen Phase 5 ML thresholds from configurable
proposed automation triggers.
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional, List, Tuple
import uuid

from automation.config import (
    FROZEN_SENSOR_ANOMALY_THRESHOLD,
    SENSOR_CONSECUTIVE_ANOMALIES_REQUIRED,
    PROPOSED_FAILURE_RISK_TRIGGER,
    PROPOSED_DEMAND_SURGE_PCT,
    PROPOSED_WARRANTY_AUDIT_PERCENTILE,
)
from automation.action_logger import ActionLogger
from automation.notifiers.slack_notifier import SlackNotifier
from automation.notifiers.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)

# Approved severe diagnostic trouble code severities
SEVERE_DTC_SEVERITIES = {"CRITICAL", "HIGH"}


class RuleEngine:
    """Evaluates real-time events and batch ML outputs against governed automation rules."""

    def __init__(
        self,
        action_logger: Optional[ActionLogger] = None,
        slack_notifier: Optional[SlackNotifier] = None,
        email_notifier: Optional[EmailNotifier] = None,
    ):
        self.action_logger = action_logger or ActionLogger()
        self.slack_notifier = slack_notifier or SlackNotifier()
        self.email_notifier = email_notifier or EmailNotifier()
        # In-memory tracking of consecutive sensor anomalies per vehicle
        self._consecutive_sensor_anomalies: Dict[str, int] = defaultdict(int)

    # --------------------------------------------------------------------------
    # RULE 1: HIGH VEHICLE FAILURE RISK
    # --------------------------------------------------------------------------
    def evaluate_rule_1_failure_risk(
        self,
        prediction: Dict[str, Any],
        threshold: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate Rule 1: High Failure Risk Trigger.
        
        Trigger Condition:
            risk_score >= PROPOSED_FAILURE_RISK_TRIGGER (0.70)
        Action:
            Draft pre-emptive inspection work-order; dispatch multi-channel (Email + Slack).
        """
        thresh = threshold if threshold is not None else PROPOSED_FAILURE_RISK_TRIGGER
        risk_score = float(prediction.get("risk_score", 0.0))
        vehicle_id = str(prediction.get("vehicle_id", "UNKNOWN"))

        if risk_score < thresh:
            return None

        action_id = str(uuid.uuid4())
        top_features = prediction.get("top_features", {})
        cutoff = prediction.get("cutoff_date", datetime.now(timezone.utc).date())
        ts = datetime.combine(cutoff, datetime.min.time(), tzinfo=timezone.utc) if not isinstance(cutoff, datetime) else cutoff

        action_taken = (
            f"Pre-emptive service work-order drafted for vehicle {vehicle_id}. "
            f"Failure probability {risk_score*100:.1f}% exceeds proposed initial trigger {thresh*100:.0f}%."
        )

        # 1. Multi-channel dispatch: Slack
        slack_payload = self.slack_notifier.build_failure_risk_block(
            vehicle_id=vehicle_id,
            risk_score=risk_score,
            threshold=thresh,
            top_features=top_features,
            action_id=action_id,
        )
        slack_status, slack_detail = self.slack_notifier.dispatch(slack_payload)

        # 2. Multi-channel dispatch: Email
        email_msg = self.email_notifier.build_failure_risk_email(
            vehicle_id=vehicle_id,
            risk_score=risk_score,
            threshold=thresh,
            top_features=top_features,
            action_id=action_id,
        )
        email_status, email_detail = self.email_notifier.dispatch(email_msg)

        combined_delivery = "DELIVERED" if (slack_status == "DELIVERED" or email_status == "DELIVERED") else (
            "MOCK_LOGGED" if (slack_status == "MOCK_LOGGED" or email_status == "MOCK_LOGGED") else "FAILED"
        )

        # 3. Transactional Action Log Persistence with Idempotency
        logged_payload = {
            "risk_score": risk_score,
            "threshold": thresh,
            "top_features": top_features,
            "slack_delivery": slack_status,
            "slack_detail": slack_detail,
            "email_delivery": email_status,
            "email_detail": email_detail,
        }

        is_new, act_id = self.action_logger.log_action(
            rule_id="RULE_1_FAILURE_RISK",
            entity_type="VEHICLE",
            entity_id=vehicle_id,
            trigger_timestamp=ts,
            trigger_value=risk_score,
            threshold_applied=thresh,
            action_taken=action_taken,
            channel_dispatched="SLACK,EMAIL",
            delivery_status=combined_delivery,
            payload=logged_payload,
            action_id=action_id,
        )

        return {
            "action_id": act_id,
            "rule_id": "RULE_1_FAILURE_RISK",
            "vehicle_id": vehicle_id,
            "risk_score": risk_score,
            "threshold": thresh,
            "action_taken": action_taken,
            "is_new": is_new,
            "delivery_status": combined_delivery,
        }

    # --------------------------------------------------------------------------
    # RULE 2: CRITICAL SENSOR ANOMALY & SEVERE DTC
    # --------------------------------------------------------------------------
    def evaluate_rule_2_sensor_telemetry(
        self,
        vehicle_id: str,
        timestamp: datetime,
        anomaly_score: float,
        is_anomaly: bool,
        telemetry_values: Dict[str, float],
        consecutive_required: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate Rule 2 for real-time streaming telemetry ping.
        
        Trigger Condition:
            anomaly_score >= FROZEN_SENSOR_ANOMALY_THRESHOLD (0.838357)
            AND consecutive anomalous pings >= SENSOR_CONSECUTIVE_ANOMALIES_REQUIRED (3)
        Action:
            Create vehicle incident record; dispatch immediate Slack alert.
        """
        required_pings = consecutive_required if consecutive_required is not None else SENSOR_CONSECUTIVE_ANOMALIES_REQUIRED

        if is_anomaly and anomaly_score >= FROZEN_SENSOR_ANOMALY_THRESHOLD:
            self._consecutive_sensor_anomalies[vehicle_id] += 1
            consec = self._consecutive_sensor_anomalies[vehicle_id]
            logger.debug(f"Vehicle {vehicle_id} anomaly ping count: {consec}/{required_pings} (Score: {anomaly_score:.4f})")
        else:
            self._consecutive_sensor_anomalies[vehicle_id] = 0
            return None

        # Check if consecutive anomaly threshold is satisfied
        if consec < required_pings:
            return None

        # Reset consecutive counter after trigger to prevent flooding
        self._consecutive_sensor_anomalies[vehicle_id] = 0

        action_id = str(uuid.uuid4())
        action_taken = (
            f"Critical telemetry anomaly incident flagged for {vehicle_id}. "
            f"Observed {consec} consecutive pings with score >= {FROZEN_SENSOR_ANOMALY_THRESHOLD:.4f}."
        )

        # Dispatch Slack Notification
        slack_payload = self.slack_notifier.build_sensor_anomaly_block(
            vehicle_id=vehicle_id,
            anomaly_score=anomaly_score,
            threshold=FROZEN_SENSOR_ANOMALY_THRESHOLD,
            telemetry_values=telemetry_values,
            consecutive_count=consec,
            action_id=action_id,
        )
        slack_status, slack_detail = self.slack_notifier.dispatch(slack_payload)

        is_new, act_id = self.action_logger.log_action(
            rule_id="RULE_2_SENSOR_ANOMALY",
            entity_type="VEHICLE",
            entity_id=vehicle_id,
            trigger_timestamp=timestamp,
            trigger_value=anomaly_score,
            threshold_applied=FROZEN_SENSOR_ANOMALY_THRESHOLD,
            action_taken=action_taken,
            channel_dispatched="SLACK",
            delivery_status=slack_status,
            payload={
                "anomaly_score": anomaly_score,
                "consecutive_pings": consec,
                "telemetry": telemetry_values,
                "slack_detail": slack_detail,
            },
            action_id=action_id,
        )

        return {
            "action_id": act_id,
            "rule_id": "RULE_2_SENSOR_ANOMALY",
            "vehicle_id": vehicle_id,
            "anomaly_score": anomaly_score,
            "consecutive_pings": consec,
            "action_taken": action_taken,
            "delivery_status": slack_status,
            "is_new": is_new,
        }

    def evaluate_rule_2_severe_dtc(
        self,
        vehicle_id: str,
        timestamp: datetime,
        dtc_code: str,
        severity: str,
        description: str,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate Rule 2 for incoming diagnostic trouble code (DTC) event.
        
        Trigger Condition:
            severity in {'CRITICAL', 'HIGH'}
        Action:
            Create immediate critical diagnostic incident record; dispatch Slack alert.
        """
        sev_upper = str(severity).upper().strip()
        if sev_upper not in SEVERE_DTC_SEVERITIES:
            return None

        action_id = str(uuid.uuid4())
        action_taken = (
            f"Severe diagnostic event ({sev_upper} - {dtc_code}) detected on vehicle {vehicle_id}. "
            f"Immediate service inspection recommended."
        )

        slack_payload = self.slack_notifier.build_sensor_anomaly_block(
            vehicle_id=vehicle_id,
            anomaly_score=1.0,
            threshold=FROZEN_SENSOR_ANOMALY_THRESHOLD,
            telemetry_values={"dtc_code": dtc_code, "severity": sev_upper},
            consecutive_count=1,
            action_id=action_id,
            dtc_code=dtc_code,
        )
        slack_status, slack_detail = self.slack_notifier.dispatch(slack_payload)

        is_new, act_id = self.action_logger.log_action(
            rule_id="RULE_2_SEVERE_DTC",
            entity_type="VEHICLE",
            entity_id=vehicle_id,
            trigger_timestamp=timestamp,
            trigger_value=1.0,
            threshold_applied=FROZEN_SENSOR_ANOMALY_THRESHOLD,
            action_taken=action_taken,
            channel_dispatched="SLACK",
            delivery_status=slack_status,
            payload={
                "dtc_code": dtc_code,
                "severity": sev_upper,
                "description": description,
                "slack_detail": slack_detail,
            },
            action_id=action_id,
        )

        return {
            "action_id": act_id,
            "rule_id": "RULE_2_SEVERE_DTC",
            "vehicle_id": vehicle_id,
            "dtc_code": dtc_code,
            "severity": sev_upper,
            "action_taken": action_taken,
            "delivery_status": slack_status,
            "is_new": is_new,
        }

    # --------------------------------------------------------------------------
    # RULE 3: SERVICE DEMAND SURGE & CAPACITY WARNING
    # --------------------------------------------------------------------------
    def evaluate_rule_3_demand_surge(
        self,
        dealer_id: str,
        forecast_date: datetime,
        predicted_volume: float,
        baseline_capacity: float,
        surge_threshold_pct: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate Rule 3: Service Demand Surge.
        
        Trigger Condition:
            (predicted_volume - baseline_capacity) / baseline_capacity > PROPOSED_DEMAND_SURGE_PCT (0.25)
        Action:
            Create dealer capacity warning; recommend parts replenishment; dispatch Email + Slack.
        """
        thresh_pct = surge_threshold_pct if surge_threshold_pct is not None else PROPOSED_DEMAND_SURGE_PCT
        if baseline_capacity <= 0:
            return None

        surge_pct = (predicted_volume - baseline_capacity) / baseline_capacity
        if surge_pct <= thresh_pct:
            return None

        action_id = str(uuid.uuid4())
        action_taken = (
            f"Service demand surge (+{surge_pct*100:.1f}%) detected for dealer {dealer_id}. "
            f"Forecasted volume ({predicted_volume:.1f}) exceeds baseline capacity ({baseline_capacity:.1f}) "
            f"by > {thresh_pct*100:.0f}%."
        )

        # Multi-channel dispatch: Slack
        slack_payload = self.slack_notifier.build_demand_surge_block(
            dealer_id=dealer_id,
            forecasted_volume=predicted_volume,
            baseline_capacity=baseline_capacity,
            surge_pct=surge_pct,
            threshold_pct=thresh_pct,
            action_id=action_id,
        )
        slack_status, slack_detail = self.slack_notifier.dispatch(slack_payload)

        # Multi-channel dispatch: Email
        email_msg = self.email_notifier.build_demand_surge_email(
            dealer_id=dealer_id,
            forecasted_volume=predicted_volume,
            baseline_capacity=baseline_capacity,
            surge_pct=surge_pct,
            threshold_pct=thresh_pct,
            action_id=action_id,
        )
        email_status, email_detail = self.email_notifier.dispatch(email_msg)

        combined_delivery = "DELIVERED" if (slack_status == "DELIVERED" or email_status == "DELIVERED") else (
            "MOCK_LOGGED" if (slack_status == "MOCK_LOGGED" or email_status == "MOCK_LOGGED") else "FAILED"
        )

        is_new, act_id = self.action_logger.log_action(
            rule_id="RULE_3_DEMAND_SURGE",
            entity_type="DEALER",
            entity_id=dealer_id,
            trigger_timestamp=forecast_date,
            trigger_value=surge_pct,
            threshold_applied=thresh_pct,
            action_taken=action_taken,
            channel_dispatched="SLACK,EMAIL",
            delivery_status=combined_delivery,
            payload={
                "predicted_volume": predicted_volume,
                "baseline_capacity": baseline_capacity,
                "surge_pct": surge_pct,
                "threshold_pct": thresh_pct,
                "slack_delivery": slack_status,
                "email_delivery": email_status,
            },
            action_id=action_id,
        )

        return {
            "action_id": act_id,
            "rule_id": "RULE_3_DEMAND_SURGE",
            "dealer_id": dealer_id,
            "surge_pct": surge_pct,
            "action_taken": action_taken,
            "delivery_status": combined_delivery,
            "is_new": is_new,
        }

    # --------------------------------------------------------------------------
    # RULE 4: WARRANTY CLAIM OUTLIER AUDIT PRIORITIZATION
    # --------------------------------------------------------------------------
    def evaluate_rule_4_warranty_outlier(
        self,
        claim_id: str,
        flagged_at: datetime,
        anomaly_score: float,
        claim_amount: float,
        dealer_id: Optional[str] = None,
        component_id: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate Rule 4: Warranty Claim Outlier Audit Prioritization.
        
        Trigger Condition:
            anomaly_score >= PROPOSED_WARRANTY_AUDIT_PERCENTILE (0.80)
        Action:
            Create audit queue record for forensic review.
        Governance Rule:
            Strictly audit prioritization. ZERO claims of fraud detection, fraud
            classification, abuse, or misconduct.
        """
        thresh = threshold if threshold is not None else PROPOSED_WARRANTY_AUDIT_PERCENTILE
        if anomaly_score < thresh:
            return None

        action_id = str(uuid.uuid4())
        action_taken = (
            f"Warranty claim {claim_id} prioritized for forensic audit review. "
            f"Outlier percentile rank {anomaly_score:.2f} meets proposed audit threshold {thresh:.2f}. "
            f"Strictly audit prioritization for sampling inspection."
        )

        is_new, act_id = self.action_logger.log_action(
            rule_id="RULE_4_WARRANTY_AUDIT",
            entity_type="CLAIM",
            entity_id=claim_id,
            trigger_timestamp=flagged_at,
            trigger_value=anomaly_score,
            threshold_applied=thresh,
            action_taken=action_taken,
            channel_dispatched="INTERNAL",
            delivery_status="DELIVERED",
            payload={
                "claim_id": claim_id,
                "dealer_id": dealer_id,
                "component_id": component_id,
                "claim_amount": claim_amount,
                "anomaly_score": anomaly_score,
                "threshold": thresh,
                "disclaimer": "Audit prioritization only; no claim of illegal activity",
            },
            action_id=action_id,
        )

        return {
            "action_id": act_id,
            "rule_id": "RULE_4_WARRANTY_AUDIT",
            "claim_id": claim_id,
            "anomaly_score": anomaly_score,
            "action_taken": action_taken,
            "delivery_status": "DELIVERED",
            "is_new": is_new,
        }
