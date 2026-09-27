"""Automation Worker & Stream Consumer for AutoCare Intelligence (Phase 6).

Consumes real-time events from Kafka `vehicle-telemetry` using an independent
consumer group (`autocare-automation-group`) to evaluate Rule 2 (Sensor Anomalies),
and coordinates scheduled batch rule evaluations for Rules 1, 3, and 4.
"""

from datetime import datetime, timezone
import json
import logging
import time
from typing import Dict, Any, Optional, List

import psycopg2
from psycopg2.extras import RealDictCursor

from automation.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TELEMETRY_TOPIC,
    KAFKA_AUTOMATION_GROUP_ID,
    PG_CONFIG,
)
from automation.rules.rule_engine import RuleEngine
from ml.inference.streaming_inference import StreamingSensorScorer

logger = logging.getLogger(__name__)


class AutomationWorker:
    """Orchestrates streaming event evaluation and batch decision automation."""

    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        streaming_scorer: Optional[StreamingSensorScorer] = None,
        pg_config: Optional[Dict[str, Any]] = None,
    ):
        self.rule_engine = rule_engine or RuleEngine()
        self.streaming_scorer = streaming_scorer or StreamingSensorScorer()
        self.pg_config = pg_config or PG_CONFIG
        self.consumer = None

    def process_telemetry_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single real-time telemetry event.
        
        Extracts telemetry fields, scores with StreamingSensorScorer,
        and evaluates Rule 2.
        """
        try:
            vehicle_id = event.get("vehicle_id")
            if not vehicle_id:
                logger.warning("Malformed telemetry event: missing vehicle_id")
                return None

            timestamp_raw = event.get("timestamp") or datetime.now(timezone.utc).isoformat()
            if isinstance(timestamp_raw, str):
                try:
                    ts = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(timezone.utc)
            else:
                ts = timestamp_raw

            telemetry_values = {
                "rpm": float(event.get("rpm", 0.0)),
                "temperature": float(event.get("temperature", 0.0)),
                "battery": float(event.get("battery", 0.0)),
                "vibration": float(event.get("vibration", 0.0)),
            }

            # 1. Real-time scoring using StreamingSensorScorer
            score_res = self.streaming_scorer.score_event(telemetry_values)
            anomaly_score = float(score_res.get("anomaly_score", 0.0))
            is_anomaly = bool(score_res.get("is_anomaly", False))

            # 2. Evaluate Rule 2 in RuleEngine
            return self.rule_engine.evaluate_rule_2_sensor_telemetry(
                vehicle_id=vehicle_id,
                timestamp=ts,
                anomaly_score=anomaly_score,
                is_anomaly=is_anomaly,
                telemetry_values=telemetry_values,
            )
        except Exception as e:
            logger.error(f"Error processing telemetry event: {e}")
            return None

    def process_diagnostic_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a real-time diagnostic trouble code (DTC) event."""
        try:
            vehicle_id = event.get("vehicle_id")
            dtc_code = event.get("dtc_code") or event.get("code")
            severity = event.get("severity") or event.get("diagnostic_severity", "LOW")
            description = event.get("description", "")
            timestamp_raw = event.get("timestamp") or datetime.now(timezone.utc).isoformat()

            if not vehicle_id or not dtc_code:
                return None

            if isinstance(timestamp_raw, str):
                try:
                    ts = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(timezone.utc)
            else:
                ts = timestamp_raw

            return self.rule_engine.evaluate_rule_2_severe_dtc(
                vehicle_id=vehicle_id,
                timestamp=ts,
                dtc_code=dtc_code,
                severity=severity,
                description=description,
            )
        except Exception as e:
            logger.error(f"Error processing diagnostic event: {e}")
            return None

    def evaluate_batch_rules(self) -> Dict[str, int]:
        """Execute batch rule evaluations against predictions stored in ml_inference."""
        counts = {"rule_1_triggered": 0, "rule_3_triggered": 0, "rule_4_triggered": 0}

        try:
            with psycopg2.connect(**self.pg_config) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 1. Evaluate Rule 1: High Failure Risk Predictions
                    cur.execute("""
                        SELECT vehicle_id, cutoff_date, risk_score, risk_tier, top_features
                        FROM ml_inference.vehicle_failure_predictions
                        WHERE cutoff_date = (SELECT MAX(cutoff_date) FROM ml_inference.vehicle_failure_predictions);
                    """)
                    preds = cur.fetchall()
                    for p in preds:
                        res = self.rule_engine.evaluate_rule_1_failure_risk(dict(p))
                        if res and res.get("is_new"):
                            counts["rule_1_triggered"] += 1

                    # 2. Evaluate Rule 3: Service Demand Forecasts
                    # Baseline capacity estimated from 30-day historical daily average per dealer (~15 visits)
                    cur.execute("""
                        SELECT dealer_id, forecast_date, predicted_volume
                        FROM ml_inference.service_demand_forecasts
                        WHERE forecast_date = (SELECT MIN(forecast_date) FROM ml_inference.service_demand_forecasts);
                    """)
                    forecasts = cur.fetchall()
                    for f in forecasts:
                        # Baseline capacity estimated at 12.0 visits/day for typical dealership
                        res = self.rule_engine.evaluate_rule_3_demand_surge(
                            dealer_id=f["dealer_id"],
                            forecast_date=f["forecast_date"],
                            predicted_volume=float(f["predicted_volume"]),
                            baseline_capacity=10.0,
                        )
                        if res and res.get("is_new"):
                            counts["rule_3_triggered"] += 1

                    # 3. Evaluate Rule 4: Warranty Claim Outliers
                    cur.execute("""
                        SELECT claim_id, dealer_id, component_id, claim_amount, anomaly_score, flagged_at
                        FROM ml_inference.warranty_anomalies;
                    """)
                    claims = cur.fetchall()
                    for c in claims:
                        res = self.rule_engine.evaluate_rule_4_warranty_outlier(
                            claim_id=c["claim_id"],
                            flagged_at=c["flagged_at"],
                            anomaly_score=float(c["anomaly_score"]),
                            claim_amount=float(c["claim_amount"]),
                            dealer_id=c.get("dealer_id"),
                            component_id=c.get("component_id"),
                        )
                        if res and res.get("is_new"):
                            counts["rule_4_triggered"] += 1

            logger.info(f"Batch rule evaluation complete: {counts}")
            return counts
        except Exception as e:
            logger.error(f"Error executing batch rule evaluation: {e}")
            return counts

    def run_kafka_consumer_loop(self, max_messages: Optional[int] = None) -> int:
        """Run continuous Kafka consumer loop on telemetry topic using independent consumer group.
        
        Gracefully handles missing Kafka broker in local/test environments.
        """
        try:
            from kafka import KafkaConsumer
            consumer = KafkaConsumer(
                KAFKA_TELEMETRY_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_AUTOMATION_GROUP_ID,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                consumer_timeout_ms=5000,
            )
            logger.info(f"Kafka consumer initialized on topic '{KAFKA_TELEMETRY_TOPIC}' with group '{KAFKA_AUTOMATION_GROUP_ID}'")
        except Exception as e:
            logger.warning(f"Kafka broker unavailable ({e}). Worker consumer loop cannot start Kafka listener.")
            return 0

        msg_count = 0
        try:
            for message in consumer:
                event = message.value
                self.process_telemetry_event(event)
                msg_count += 1
                if max_messages and msg_count >= max_messages:
                    break
        except Exception as e:
            logger.error(f"Error in Kafka consumer loop: {e}")
        finally:
            consumer.close()

        return msg_count
