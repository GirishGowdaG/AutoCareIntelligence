"""Unit and Integration Tests for Decision Automation and Notifications (Phase 6 Stage 1).

Covers:
1. Rule 1 Trigger (High Failure Risk)
2. Rule 2 Sensor Anomaly Trigger (3 Consecutive Anomalies)
3. Rule 2 Severe DTC Trigger (CRITICAL/HIGH severities)
4. Rule 3 Demand Surge Trigger (>25% capacity excursion)
5. Rule 4 Warranty Outlier Audit Trigger (>=0.80 percentile)
6. Slack Block Kit Payload Structure
7. Email Multipart MIME & HTML Formatting
8. Real Dispatch with Local Mock Fallback
9. Action Log Persistence in ml_inference.action_logs
10. Idempotency & Duplicate Event Suppression
11. Threshold Governance (Proposed vs Ratified separation)
12. Frozen Sensor Threshold Integrity (0.838357)
13. Warranty Rule No-Fraud Disclaimer Enforcement
"""

from datetime import datetime, date, timezone
import json
import uuid
import pytest
import psycopg2

from automation.config import (
    FROZEN_SENSOR_ANOMALY_THRESHOLD,
    SENSOR_CONSECUTIVE_ANOMALIES_REQUIRED,
    PROPOSED_FAILURE_RISK_TRIGGER,
    PROPOSED_DEMAND_SURGE_PCT,
    PROPOSED_WARRANTY_AUDIT_PERCENTILE,
    PG_CONFIG,
)
from automation.action_logger import ActionLogger, generate_idempotency_key
from automation.notifiers.slack_notifier import SlackNotifier
from automation.notifiers.email_notifier import EmailNotifier
from automation.rules.rule_engine import RuleEngine
from automation.worker import AutomationWorker


class TestDecisionAutomation:
    """Comprehensive test suite for Phase 6 Stage 1 Decision Automation."""

    @pytest.fixture
    def action_logger(self):
        return ActionLogger(pg_config=PG_CONFIG)

    @pytest.fixture
    def slack_notifier(self):
        return SlackNotifier()

    @pytest.fixture
    def email_notifier(self):
        return EmailNotifier()

    @pytest.fixture
    def rule_engine(self, action_logger, slack_notifier, email_notifier):
        return RuleEngine(
            action_logger=action_logger,
            slack_notifier=slack_notifier,
            email_notifier=email_notifier,
        )

    # --------------------------------------------------------------------------
    # 1. Rule 1 Trigger Test
    # --------------------------------------------------------------------------
    def test_rule_1_failure_risk_trigger(self, rule_engine):
        high_risk_pred = {
            "vehicle_id": "VH-TEST-R1-01",
            "risk_score": 0.85,  # >= 0.70 proposed trigger
            "cutoff_date": date(2026, 9, 20),
            "top_features": {"engine_temp_max": 112.5, "dtc_count": 4.0},
        }
        res = rule_engine.evaluate_rule_1_failure_risk(high_risk_pred)
        assert res is not None
        assert res["rule_id"] == "RULE_1_FAILURE_RISK"
        assert res["vehicle_id"] == "VH-TEST-R1-01"
        assert res["risk_score"] == 0.85
        assert res["threshold"] == PROPOSED_FAILURE_RISK_TRIGGER
        assert res["delivery_status"] in ("DELIVERED", "MOCK_LOGGED")

        # Sub-threshold prediction should not trigger
        low_risk_pred = {
            "vehicle_id": "VH-TEST-R1-02",
            "risk_score": 0.45,  # < 0.70
            "cutoff_date": date(2026, 9, 20),
        }
        res_low = rule_engine.evaluate_rule_1_failure_risk(low_risk_pred)
        assert res_low is None

    # --------------------------------------------------------------------------
    # 2. Rule 2 Sensor Trigger Test (Consecutive Anomalies)
    # --------------------------------------------------------------------------
    def test_rule_2_sensor_consecutive_anomalies_trigger(self, rule_engine):
        vehicle_id = "VH-TEST-R2-SENS"
        ts = datetime.now(timezone.utc)
        telemetry = {"rpm": 6200.0, "temperature": 118.0, "vibration": 3.8}

        # Ping 1: Anomaly (score >= 0.838357) -> Count = 1, does NOT trigger yet
        res_1 = rule_engine.evaluate_rule_2_sensor_telemetry(
            vehicle_id=vehicle_id,
            timestamp=ts,
            anomaly_score=0.88,
            is_anomaly=True,
            telemetry_values=telemetry,
        )
        assert res_1 is None

        # Ping 2: Anomaly -> Count = 2, does NOT trigger yet
        res_2 = rule_engine.evaluate_rule_2_sensor_telemetry(
            vehicle_id=vehicle_id,
            timestamp=ts,
            anomaly_score=0.91,
            is_anomaly=True,
            telemetry_values=telemetry,
        )
        assert res_2 is None

        # Ping 3: Anomaly -> Count = 3 >= SENSOR_CONSECUTIVE_ANOMALIES_REQUIRED (3) -> TRIGGERS!
        res_3 = rule_engine.evaluate_rule_2_sensor_telemetry(
            vehicle_id=vehicle_id,
            timestamp=ts,
            anomaly_score=0.94,
            is_anomaly=True,
            telemetry_values=telemetry,
        )
        assert res_3 is not None
        assert res_3["rule_id"] == "RULE_2_SENSOR_ANOMALY"
        assert res_3["consecutive_pings"] == 3
        assert res_3["vehicle_id"] == vehicle_id

        # Nominal ping resets the consecutive counter
        rule_engine.evaluate_rule_2_sensor_telemetry(
            vehicle_id=vehicle_id,
            timestamp=ts,
            anomaly_score=0.20,
            is_anomaly=False,
            telemetry_values={"rpm": 2100.0, "temperature": 85.0},
        )
        assert rule_engine._consecutive_sensor_anomalies[vehicle_id] == 0

    # --------------------------------------------------------------------------
    # 3. Rule 2 Severe DTC Trigger Test
    # --------------------------------------------------------------------------
    def test_rule_2_severe_dtc_trigger(self, rule_engine):
        ts = datetime.now(timezone.utc)
        # CRITICAL severity triggers alert
        res_crit = rule_engine.evaluate_rule_2_severe_dtc(
            vehicle_id="VH-TEST-R2-DTC",
            timestamp=ts,
            dtc_code="P0217",
            severity="CRITICAL",
            description="Engine Overtemperature Condition",
        )
        assert res_crit is not None
        assert res_crit["rule_id"] == "RULE_2_SEVERE_DTC"
        assert res_crit["severity"] == "CRITICAL"
        assert res_crit["dtc_code"] == "P0217"

        # HIGH severity also triggers alert
        res_high = rule_engine.evaluate_rule_2_severe_dtc(
            vehicle_id="VH-TEST-R2-DTC2",
            timestamp=ts,
            dtc_code="P0300",
            severity="HIGH",
            description="Random/Multiple Cylinder Misfire Detected",
        )
        assert res_high is not None

        # LOW or MEDIUM severity does NOT trigger Rule 2
        res_low = rule_engine.evaluate_rule_2_severe_dtc(
            vehicle_id="VH-TEST-R2-DTC3",
            timestamp=ts,
            dtc_code="P0420",
            severity="LOW",
            description="Catalyst System Efficiency Below Threshold",
        )
        assert res_low is None

    # --------------------------------------------------------------------------
    # 4. Rule 3 Demand Surge Trigger Test
    # --------------------------------------------------------------------------
    def test_rule_3_demand_surge_trigger(self, rule_engine):
        # Forecast 18.0 visits on baseline capacity 12.0 visits -> +50% surge (> 25% proposed threshold)
        res = rule_engine.evaluate_rule_3_demand_surge(
            dealer_id="DLR-TEST-01",
            forecast_date=datetime.now(timezone.utc),
            predicted_volume=18.0,
            baseline_capacity=12.0,
        )
        assert res is not None
        assert res["rule_id"] == "RULE_3_DEMAND_SURGE"
        assert res["dealer_id"] == "DLR-TEST-01"
        assert pytest.approx(res["surge_pct"], 0.01) == 0.50

        # Sub-threshold surge (+10% <= 25%) should not trigger
        res_sub = rule_engine.evaluate_rule_3_demand_surge(
            dealer_id="DLR-TEST-02",
            forecast_date=datetime.now(timezone.utc),
            predicted_volume=13.0,
            baseline_capacity=12.0,  # ~8.3% surge
        )
        assert res_sub is None

    # --------------------------------------------------------------------------
    # 5. Rule 4 Warranty Outlier Audit Trigger Test
    # --------------------------------------------------------------------------
    def test_rule_4_warranty_outlier_trigger(self, rule_engine):
        # Outlier percentile 0.95 >= 0.80 proposed threshold
        res = rule_engine.evaluate_rule_4_warranty_outlier(
            claim_id="CLM-TEST-9901",
            flagged_at=datetime.now(timezone.utc),
            anomaly_score=0.95,
            claim_amount=4500.0,
            dealer_id="DLR-01",
            component_id="CMP-BRAKE-01",
        )
        assert res is not None
        assert res["rule_id"] == "RULE_4_WARRANTY_AUDIT"
        assert res["claim_id"] == "CLM-TEST-9901"
        assert res["delivery_status"] == "DELIVERED"  # Internal log is immediately delivered

        # Normal claim (score 0.40 < 0.80) does not trigger
        res_sub = rule_engine.evaluate_rule_4_warranty_outlier(
            claim_id="CLM-TEST-9902",
            flagged_at=datetime.now(timezone.utc),
            anomaly_score=0.40,
            claim_amount=150.0,
        )
        assert res_sub is None

    # --------------------------------------------------------------------------
    # 6. Slack Block Kit Payload Test
    # --------------------------------------------------------------------------
    def test_slack_block_kit_structure(self, slack_notifier):
        block = slack_notifier.build_sensor_anomaly_block(
            vehicle_id="VH-10025",
            anomaly_score=0.8950,
            threshold=FROZEN_SENSOR_ANOMALY_THRESHOLD,
            telemetry_values={"rpm": 5400, "temperature": 115.0, "vibration": 3.2},
            consecutive_count=3,
            action_id="act-test-1234",
        )
        assert "channel" in block
        assert "blocks" in block
        assert len(block["blocks"]) >= 3
        # Header block
        assert block["blocks"][0]["type"] == "header"
        # Section with fields
        assert block["blocks"][1]["type"] == "section"
        assert len(block["blocks"][1]["fields"]) >= 3
        # Context block
        assert block["blocks"][2]["type"] == "context"

    # --------------------------------------------------------------------------
    # 7. Email Multipart MIME Structure Test
    # --------------------------------------------------------------------------
    def test_email_mime_multipart_structure(self, email_notifier):
        msg = email_notifier.build_failure_risk_email(
            vehicle_id="VH-10030",
            risk_score=0.82,
            threshold=PROPOSED_FAILURE_RISK_TRIGGER,
            top_features={"engine_temp_max": 115.0, "vibration": 3.5},
            action_id="act-test-5678",
        )
        assert msg.is_multipart()
        parts = [p.get_content_type() for p in msg.get_payload()]
        assert "text/plain" in parts
        assert "text/html" in parts
        assert "VH-10030" in msg["Subject"]

    # --------------------------------------------------------------------------
    # 8. Mock Fallback Test (No Webhook / No SMTP configured)
    # --------------------------------------------------------------------------
    def test_mock_fallback_delivery_status(self, slack_notifier, email_notifier):
        # Empty webhook should return MOCK_LOGGED without exception
        empty_slack = SlackNotifier(webhook_url="")
        s_status, s_msg = empty_slack.dispatch({"text": "Test alert", "channel": "#test"})
        assert s_status == "MOCK_LOGGED"
        assert "Mock" in s_msg

        # Localhost SMTP with no user returns MOCK_LOGGED
        local_email = EmailNotifier(smtp_host="localhost", smtp_user="")
        msg = email_notifier.build_failure_risk_email("VH-1", 0.8, 0.7, {}, "act-1")
        e_status, e_msg = local_email.dispatch(msg)
        assert e_status == "MOCK_LOGGED"
        assert "Mock" in e_msg

    # --------------------------------------------------------------------------
    # 9. Action Log Persistence in Database
    # --------------------------------------------------------------------------
    def test_action_log_database_persistence(self, action_logger):
        act_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc)
        is_new, logged_id = action_logger.log_action(
            rule_id="RULE_1_FAILURE_RISK",
            entity_type="VEHICLE",
            entity_id="VH-DB-TEST-01",
            trigger_timestamp=ts,
            trigger_value=0.88,
            threshold_applied=0.70,
            action_taken="Pre-emptive work-order drafted",
            channel_dispatched="SLACK,EMAIL",
            delivery_status="MOCK_LOGGED",
            payload={"test_flag": True},
            action_id=act_id,
        )
        assert is_new is True
        assert logged_id == act_id

        # Verify read-back from database
        recent = action_logger.get_recent_actions(limit=10)
        found = [r for r in recent if str(r["action_id"]) == act_id]
        assert len(found) == 1
        assert found[0]["entity_id"] == "VH-DB-TEST-01"
        assert found[0]["rule_id"] == "RULE_1_FAILURE_RISK"
        assert found[0]["delivery_status"] == "MOCK_LOGGED"

    # --------------------------------------------------------------------------
    # 10. Idempotency & Duplicate Suppression Test
    # --------------------------------------------------------------------------
    def test_idempotency_duplicate_suppression(self, action_logger):
        ts = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
        test_entity = f"VH-IDEM-{uuid.uuid4().hex[:8]}"
        idem_key = generate_idempotency_key("RULE_1_FAILURE_RISK", test_entity, ts.isoformat(), 0.85)

        # First insert succeeds
        is_new_1, act_1 = action_logger.log_action(
            rule_id="RULE_1_FAILURE_RISK",
            entity_type="VEHICLE",
            entity_id=test_entity,
            trigger_timestamp=ts,
            trigger_value=0.85,
            threshold_applied=0.70,
            action_taken="Action 1",
            channel_dispatched="SLACK",
            delivery_status="DELIVERED",
            payload={"attempt": 1},
            idempotency_key=idem_key,
        )
        assert is_new_1 is True

        # Duplicate delivery with exact same idempotency key is suppressed!
        is_new_2, act_2 = action_logger.log_action(
            rule_id="RULE_1_FAILURE_RISK",
            entity_type="VEHICLE",
            entity_id=test_entity,
            trigger_timestamp=ts,
            trigger_value=0.85,
            threshold_applied=0.70,
            action_taken="Action 1 Duplicate",
            channel_dispatched="SLACK",
            delivery_status="DELIVERED",
            payload={"attempt": 2},
            idempotency_key=idem_key,
        )
        assert is_new_2 is False
        assert act_2 == act_1  # References the original action ID

    # --------------------------------------------------------------------------
    # 11. Threshold Governance (Proposed vs Ratified) Test
    # --------------------------------------------------------------------------
    def test_threshold_governance_separation(self):
        # 1. Governed Sensor Threshold MUST be frozen and equal to Method B acceptance result
        assert FROZEN_SENSOR_ANOMALY_THRESHOLD == pytest.approx(0.838357, abs=1e-4)

        # 2. Proposed thresholds must be clearly labeled as initial proposals
        assert PROPOSED_FAILURE_RISK_TRIGGER == 0.70
        assert PROPOSED_DEMAND_SURGE_PCT == 0.25
        assert PROPOSED_WARRANTY_AUDIT_PERCENTILE == 0.80

    # --------------------------------------------------------------------------
    # 12. Frozen Sensor Threshold Consumed in Rule 2 Test
    # --------------------------------------------------------------------------
    def test_rule_2_uses_exact_frozen_sensor_threshold(self, rule_engine):
        # Sub-threshold score (e.g. 0.8380 < 0.838357) should NOT increment anomaly counter
        vehicle_id = "VH-FROZEN-THRESH-TEST"
        ts = datetime.now(timezone.utc)
        res = rule_engine.evaluate_rule_2_sensor_telemetry(
            vehicle_id=vehicle_id,
            timestamp=ts,
            anomaly_score=0.8380,  # Below frozen threshold
            is_anomaly=True,
            telemetry_values={"rpm": 2500.0},
        )
        assert res is None
        assert rule_engine._consecutive_sensor_anomalies[vehicle_id] == 0

        # Above threshold score increments counter
        rule_engine.evaluate_rule_2_sensor_telemetry(
            vehicle_id=vehicle_id,
            timestamp=ts,
            anomaly_score=0.8384,  # Above frozen threshold
            is_anomaly=True,
            telemetry_values={"rpm": 5500.0},
        )
        assert rule_engine._consecutive_sensor_anomalies[vehicle_id] == 1

    # --------------------------------------------------------------------------
    # 13. Warranty Rule No-Fraud Disclaimer Enforcement Test
    # --------------------------------------------------------------------------
    def test_warranty_rule_no_fraud_claims(self, rule_engine):
        res = rule_engine.evaluate_rule_4_warranty_outlier(
            claim_id="CLM-NO-FRAUD",
            flagged_at=datetime.now(timezone.utc),
            anomaly_score=0.92,
            claim_amount=3200.0,
        )
        assert res is not None
        action_text = res["action_taken"].lower()
        # Verify prohibited terms are NOT present
        prohibited_terms = ["fraud detected", "fraud classification", "abuse detected", "criminal misconduct"]
        for term in prohibited_terms:
            assert term not in action_text

        # Verify required audit prioritization terms ARE present
        assert "audit" in action_text
        assert "priorit" in action_text
