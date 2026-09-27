"""Kafka Consumer for Vehicle Diagnostic Trouble Code (DTC) events.

Consumes diagnostic streaming events, validates data contracts, lands micro-batches
to partitioned Streaming Bronze Parquet storage, and synchronously commits Kafka offsets.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from streaming.config import (
    TOPIC_DIAGNOSTICS,
    DEFAULT_BOOTSTRAP_SERVERS,
    CONSUMER_BASE_CONFIG,
    STREAMING_DIAGNOSTICS_DIR,
)
from streaming.schemas.diagnostic_event import DiagnosticEvent
from streaming.consumers.dlq_handler import DLQHandler

logger = logging.getLogger(__name__)


class DiagnosticsConsumer:
    """Consumes and lands vehicle diagnostic events into Bronze streaming partitions."""

    def __init__(
        self,
        bootstrap_servers: str = DEFAULT_BOOTSTRAP_SERVERS,
        group_id: Optional[str] = None,
        landing_dir: Path = STREAMING_DIAGNOSTICS_DIR,
        dlq_handler: Optional[DLQHandler] = None,
        mock_mode: bool = False,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.landing_dir = Path(landing_dir)
        self.mock_mode = mock_mode
        self.dlq_handler = dlq_handler or DLQHandler(bootstrap_servers=bootstrap_servers, mock_mode=mock_mode)

        config = {**CONSUMER_BASE_CONFIG, "bootstrap.servers": bootstrap_servers}
        if group_id:
            config["group.id"] = group_id
        self.config = config

        self._consumer = None
        if not self.mock_mode:
            try:
                from confluent_kafka import Consumer
                self._consumer = Consumer(self.config)
                self._consumer.subscribe([TOPIC_DIAGNOSTICS])
            except Exception as e:
                logger.warning(f"Could not init Kafka Consumer ({e}), operating in mock/test mode.")
                self.mock_mode = True

        self.landing_dir.mkdir(parents=True, exist_ok=True)

    def process_message_payload(
        self,
        raw_val: Any,
        topic: str = TOPIC_DIAGNOSTICS,
        partition: Optional[int] = None,
        offset: Optional[int] = None,
        key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Validate payload against DiagnosticEvent contract.
        
        Routes invalid payloads to DLQ. Returns clean business dict if valid.
        """
        try:
            if isinstance(raw_val, (bytes, bytearray)):
                data = json.loads(raw_val.decode("utf-8"))
            elif isinstance(raw_val, str):
                data = json.loads(raw_val)
            elif isinstance(raw_val, dict):
                data = raw_val
            else:
                raise ValueError(f"Unsupported payload type: {type(raw_val)}")

            event = DiagnosticEvent.model_validate(data)
            return event.to_business_dict()

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.dlq_handler.route_to_dlq(
                original_topic=topic,
                raw_message=raw_val,
                error_reason=f"CORRUPT_JSON: {e}",
                partition=partition,
                offset=offset,
                key=key,
            )
            return None
        except ValidationError as e:
            self.dlq_handler.route_to_dlq(
                original_topic=topic,
                raw_message=raw_val,
                error_reason=f"VALIDATION_ERROR: {e}",
                partition=partition,
                offset=offset,
                key=key,
            )
            return None
        except Exception as e:
            self.dlq_handler.route_to_dlq(
                original_topic=topic,
                raw_message=raw_val,
                error_reason=f"PROCESSING_ERROR: {e}",
                partition=partition,
                offset=offset,
                key=key,
            )
            return None

    def land_micro_batch(
        self,
        records: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
    ) -> List[Path]:
        """Write validated diagnostic records to Bronze Streaming partitioned Parquet files.
        
        Partitioning layout: year=YYYY/month=MM/day=DD/hour=HH/<batch_id>.parquet
        """
        if not records:
            return []

        batch_id = batch_id or f"batch_{uuid.uuid4().hex[:12]}"
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        written_paths = []
        df["year"] = df["timestamp"].dt.year
        df["month"] = df["timestamp"].dt.month.map("{:02d}".format)
        df["day"] = df["timestamp"].dt.day.map("{:02d}".format)
        df["hour"] = df["timestamp"].dt.hour.map("{:02d}".format)

        for (year, month, day, hour), group in df.groupby(["year", "month", "day", "hour"]):
            part_dir = self.landing_dir / f"year={year}" / f"month={month}" / f"day={day}" / f"hour={hour}"
            part_dir.mkdir(parents=True, exist_ok=True)
            out_file = part_dir / f"{batch_id}.parquet"

            sub_df = group.drop(columns=["year", "month", "day", "hour"])
            table = pa.Table.from_pandas(sub_df, preserve_index=False)
            pq.write_table(table, str(out_file), compression="SNAPPY")
            written_paths.append(out_file)

        return written_paths

    def consume_batch(
        self,
        max_messages: int = 1000,
        timeout: float = 2.0,
        mock_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[int, int, List[Path]]:
        """Consume a micro-batch of diagnostic messages.
        
        Returns: (valid_count, dlq_count, written_parquet_paths)
        Synchronously commits Kafka consumer offsets ONLY after successful disk write.
        """
        valid_records: List[Dict[str, Any]] = []
        dlq_count_before = len(self.dlq_handler.dlq_records)

        if self.mock_mode or mock_messages is not None:
            items = mock_messages or []
            for item in items[:max_messages]:
                key = item.get("key") if isinstance(item, dict) else None
                val = item.get("value") if isinstance(item, dict) else item
                parsed = self.process_message_payload(val, key=key)
                if parsed:
                    valid_records.append(parsed)
        else:
            if not self._consumer:
                return 0, 0, []

            messages = self._consumer.consume(num_messages=max_messages, timeout=timeout)
            for msg in messages:
                if msg.error():
                    logger.error(f"Consumer message error: {msg.error()}")
                    continue
                parsed = self.process_message_payload(
                    raw_val=msg.value(),
                    topic=msg.topic(),
                    partition=msg.partition(),
                    offset=msg.offset(),
                    key=msg.key().decode("utf-8") if msg.key() else None,
                )
                if parsed:
                    valid_records.append(parsed)

        dlq_count = len(self.dlq_handler.dlq_records) - dlq_count_before
        written_files = self.land_micro_batch(valid_records)

        # Synchronous offset commit AFTER successful micro-batch write to disk
        if not self.mock_mode and self._consumer and valid_records:
            try:
                self._consumer.commit(asynchronous=False)
            except Exception as e:
                logger.error(f"Synchronous commit failed after landing micro-batch: {e}")
                raise

        return len(valid_records), dlq_count, written_files

    def close(self):
        """Close Kafka consumer safely."""
        if self._consumer and not self.mock_mode:
            self._consumer.close()
