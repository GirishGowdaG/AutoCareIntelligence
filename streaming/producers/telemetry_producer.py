"""Kafka Producer for Vehicle Telemetry events.

Enforces idempotent producer delivery (enable.idempotence=true) and vehicle_id
key partitioning for partition affinity.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Generator, List
from pathlib import Path

from streaming.config import (
    TOPIC_TELEMETRY,
    DEFAULT_BOOTSTRAP_SERVERS,
    PRODUCER_BASE_CONFIG,
    DEFAULT_SIMULATION_TARGET_HZ,
)
from streaming.schemas.telemetry_event import TelemetryEvent

logger = logging.getLogger(__name__)


class TelemetryProducer:
    """Producer for vehicle telemetry streaming events."""

    def __init__(
        self,
        bootstrap_servers: str = DEFAULT_BOOTSTRAP_SERVERS,
        producer_id: str = "autocare-telemetry-producer",
        extra_config: Optional[Dict[str, Any]] = None,
        mock_mode: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.producer_id = producer_id
        self.mock_mode = mock_mode
        self.delivered_records: List[Dict[str, Any]] = []
        self.failed_records: List[Dict[str, Any]] = []

        config = {**PRODUCER_BASE_CONFIG, "bootstrap.servers": bootstrap_servers}
        if extra_config:
            config.update(extra_config)
        self.config = config

        self._producer = None
        if not self.mock_mode:
            try:
                from confluent_kafka import Producer
                self._producer = Producer(self.config)
            except Exception as e:
                logger.warning(
                    f"Could not initialize Confluent Kafka Producer ({e}). Falling back to mock/offline mode."
                )
                self.mock_mode = True

    def _delivery_report(self, err, msg):
        """Delivery callback for Kafka producer events."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            self.failed_records.append({"error": str(err)})
        else:
            self.delivered_records.append({
                "topic": msg.topic(),
                "partition": msg.partition(),
                "offset": msg.offset(),
                "key": msg.key().decode("utf-8") if msg.key() else None,
            })

    def send_event(self, event: TelemetryEvent) -> bool:
        """Send a validated TelemetryEvent to Kafka.
        
        Uses vehicle_id as message key to ensure partition affinity.
        Note: Key partitioning guarantees partition affinity, but does not
        guarantee chronological event-timestamp ordering.
        """
        payload = event.to_transport_dict()
        payload["_producer_id"] = self.producer_id
        payload["_sent_at"] = datetime.now(timezone.utc).isoformat()
        payload["_kafka_topic"] = TOPIC_TELEMETRY

        message_bytes = json.dumps(payload).encode("utf-8")
        key_bytes = event.vehicle_id.encode("utf-8")

        if self.mock_mode or self._producer is None:
            # Deterministic recording in mock/offline mode
            self.delivered_records.append({
                "topic": TOPIC_TELEMETRY,
                "partition": hash(event.vehicle_id) % 3,
                "offset": len(self.delivered_records),
                "key": event.vehicle_id,
                "payload": payload,
            })
            return True

        try:
            self._producer.produce(
                topic=TOPIC_TELEMETRY,
                key=key_bytes,
                value=message_bytes,
                callback=self._delivery_report,
            )
            self._producer.poll(0)
            return True
        except Exception as e:
            logger.error(f"Failed to produce telemetry event for {event.vehicle_id}: {e}")
            self.failed_records.append({"event": payload, "error": str(e)})
            return False

    def flush(self, timeout: float = 10.0) -> int:
        """Flush pending producer messages."""
        if self._producer and not self.mock_mode:
            return self._producer.flush(timeout)
        return 0

    def replay_from_parquet(
        self,
        parquet_file: Path,
        max_events: Optional[int] = None,
        target_hz: float = DEFAULT_SIMULATION_TARGET_HZ,
    ) -> int:
        """Replay historical telemetry records from Parquet into Kafka topic."""
        import pyarrow.parquet as pq

        table = pq.read_table(str(parquet_file))
        df = table.to_pandas()
        count = 0
        interval = 1.0 / target_hz if target_hz > 0 else 0.0

        for _, row in df.iterrows():
            if max_events is not None and count >= max_events:
                break
            try:
                event = TelemetryEvent(
                    vehicle_id=str(row["vehicle_id"]),
                    timestamp=row["timestamp"],
                    rpm=float(row["rpm"]),
                    temperature=float(row["temperature"]),
                    battery=float(row["battery"]),
                    vibration=float(row["vibration"]),
                )
                if self.send_event(event):
                    count += 1
                if interval > 0:
                    time.sleep(interval)
            except Exception as e:
                logger.warning(f"Skipping invalid historical record: {e}")

        self.flush()
        return count
