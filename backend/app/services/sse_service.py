"""Server-Sent Events (SSE) Streaming Service.

Provides real-time event generator streaming:
- 15-second keepalive heartbeats.
- Real-time telemetry events from Kafka (source="kafka") with graceful fallback
  to synthetic pulses (source="synthetic_demo") if Kafka broker is unavailable.
- Automated action events from ml_inference.action_logs (source="action_logs").
- Last-Event-ID reconnection support.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import AsyncGenerator, Optional
import uuid

from backend.app.core.config import get_app_settings
from backend.app.core.database import execute_read_query

logger = logging.getLogger(__name__)


class SSEEventStreamer:
    """Asynchronous event generator for Server-Sent Events (SSE)."""

    def __init__(self, last_event_id: Optional[str] = None):
        self.last_event_id = last_event_id
        self.settings = get_app_settings()
        self._last_action_poll_time = datetime.now(timezone.utc)
        self._last_heartbeat_time = datetime.now(timezone.utc)
        self._message_counter = 0

    def _format_sse(self, event: str, data: dict, event_id: Optional[str] = None) -> str:
        """Format dictionary payload into valid SSE text/event-stream message."""
        eid = event_id or str(uuid.uuid4())
        payload = json.dumps(data, default=str)
        return f"id: {eid}\nevent: {event}\ndata: {payload}\n\n"

    async def stream_events(self, max_events: Optional[int] = None) -> AsyncGenerator[str, None]:
        """Generate SSE messages continuously.
        
        Args:
            max_events: Optional limit for testing/mock streaming.
        """
        produced = 0
        while max_events is None or produced < max_events:
            now = datetime.now(timezone.utc)

            # 1. 15-Second Keepalive Heartbeat
            if (now - self._last_heartbeat_time).total_seconds() >= 15.0 or produced == 0:
                self._last_heartbeat_time = now
                self._message_counter += 1
                yield self._format_sse(
                    event="heartbeat",
                    data={
                        "event_type": "heartbeat",
                        "source": "server",
                        "timestamp": now.isoformat(),
                        "message_seq": self._message_counter,
                    },
                    event_id=f"hb-{self._message_counter}",
                )
                produced += 1
                if max_events is not None and produced >= max_events:
                    break

            # 2. Check for New Automated Action Logs (Observation)
            try:
                actions = execute_read_query(
                    """
                    SELECT action_id, rule_id, entity_type, entity_id, trigger_timestamp,
                           trigger_value, threshold_applied, action_taken, channel_dispatched,
                           delivery_status, idempotency_key, created_at
                    FROM ml_inference.action_logs
                    WHERE created_at > %s
                    ORDER BY created_at ASC
                    LIMIT 5;
                    """,
                    (self._last_action_poll_time,),
                )
                for act in actions:
                    self._last_action_poll_time = act["created_at"]
                    self._message_counter += 1
                    yield self._format_sse(
                        event="audit_action",
                        data={
                            "event_type": "audit_action",
                            "source": "action_logs",
                            "timestamp": act["created_at"].isoformat() if isinstance(act["created_at"], datetime) else str(act["created_at"]),
                            "action": act,
                        },
                        event_id=f"act-{act['action_id']}",
                    )
                    produced += 1
                    if max_events is not None and produced >= max_events:
                        break
            except Exception as e:
                logger.debug(f"Action log polling error in SSE: {e}")

            if max_events is not None and produced >= max_events:
                break

            # 3. Telemetry Stream (Kafka or Synthetic Fallback)
            telemetry_event = self._get_telemetry_event()
            if telemetry_event:
                self._message_counter += 1
                yield self._format_sse(
                    event="telemetry_pulse",
                    data=telemetry_event,
                    event_id=f"tel-{self._message_counter}",
                )
                produced += 1
                if max_events is not None and produced >= max_events:
                    break

            # Non-blocking pause between pulses
            await asyncio.sleep(1.0)

    def _get_telemetry_event(self) -> dict:
        """Attempt to read from Kafka topic; fallback to explicitly labeled synthetic pulse."""
        # Check if confluent_kafka is available and Kafka broker is reachable
        try:
            from confluent_kafka import Consumer, KafkaError
            conf = {
                "bootstrap.servers": self.settings.kafka_bootstrap_servers,
                "group.id": self.settings.kafka_consumer_group_sse,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
                "socket.timeout.ms": 500,
            }
            consumer = Consumer(conf)
            consumer.subscribe([self.settings.kafka_topic_telemetry])
            msg = consumer.poll(timeout=0.1)
            consumer.close()

            if msg is not None and not msg.error():
                payload = json.loads(msg.value().decode("utf-8"))
                return {
                    "event_type": "telemetry_pulse",
                    "source": "kafka",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": payload,
                }
        except Exception:
            # Kafka unavailable -> Fallback to explicitly labeled synthetic demo data
            pass

        # Strictly labeled synthetic fallback
        return {
            "event_type": "telemetry_pulse",
            "source": "synthetic_demo",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "vehicle_id": "VH001",
                "rpm": 2450,
                "temperature": 92.5,
                "battery": 13.8,
                "vibration": 1.25,
            },
        }
