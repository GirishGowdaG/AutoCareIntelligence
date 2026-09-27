"""Dead-Letter Queue (DLQ) Handler for streaming poison pills and malformed events.

Ensures no silent drops by routing corrupt payloads to dedicated DLQ topics with
diagnostic error metadata.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from streaming.config import (
    TOPIC_TELEMETRY_DLQ,
    TOPIC_DIAGNOSTICS_DLQ,
    DEFAULT_BOOTSTRAP_SERVERS,
    PRODUCER_BASE_CONFIG,
)

logger = logging.getLogger(__name__)


class DLQHandler:
    """Routes invalid or malformed streaming messages to Kafka DLQ topics."""

    def __init__(
        self,
        bootstrap_servers: str = DEFAULT_BOOTSTRAP_SERVERS,
        mock_mode: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.mock_mode = mock_mode
        self.dlq_records: List[Dict[str, Any]] = []

        self._producer = None
        if not self.mock_mode:
            try:
                from confluent_kafka import Producer
                self._producer = Producer({
                    **PRODUCER_BASE_CONFIG,
                    "bootstrap.servers": bootstrap_servers,
                })
            except Exception as e:
                logger.warning(f"Could not init DLQ producer ({e}), falling back to mock/offline mode.")
                self.mock_mode = True

    def route_to_dlq(
        self,
        original_topic: str,
        raw_message: Any,
        error_reason: str,
        partition: Optional[int] = None,
        offset: Optional[int] = None,
        key: Optional[str] = None,
    ) -> bool:
        """Route a malformed or rejected record to the appropriate DLQ topic."""
        if "diagnostic" in original_topic:
            dlq_topic = TOPIC_DIAGNOSTICS_DLQ
        else:
            dlq_topic = TOPIC_TELEMETRY_DLQ

        raw_str = (
            raw_message.decode("utf-8", errors="replace")
            if isinstance(raw_message, (bytes, bytearray))
            else str(raw_message)
        )

        dlq_envelope = {
            "_dlq_timestamp": datetime.now(timezone.utc).isoformat(),
            "_dlq_reason": error_reason,
            "_original_topic": original_topic,
            "_original_partition": partition,
            "_original_offset": offset,
            "_original_key": key,
            "_raw_payload": raw_str,
        }

        self.dlq_records.append(dlq_envelope)
        logger.warning(
            f"Routing poison pill to {dlq_topic} (reason: {error_reason}, key: {key})"
        )

        if self.mock_mode or self._producer is None:
            return True

        try:
            val_bytes = json.dumps(dlq_envelope).encode("utf-8")
            key_bytes = str(key).encode("utf-8") if key else None
            self._producer.produce(
                topic=dlq_topic,
                key=key_bytes,
                value=val_bytes,
            )
            self._producer.poll(0)
            return True
        except Exception as e:
            logger.error(f"Failed to publish to DLQ topic {dlq_topic}: {e}")
            return False

    def flush(self, timeout: float = 5.0) -> int:
        if self._producer and not self.mock_mode:
            return self._producer.flush(timeout)
        return 0
