"""Unit and integration tests for Kafka streaming components in Phase 4.

Tests event schemas, partition affinity, DLQ routing, consumer micro-batch landing,
and mathematical row conservation during Silver compaction.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from streaming.config import (
    TOPIC_TELEMETRY,
    TOPIC_DIAGNOSTICS,
    TOPIC_TELEMETRY_DLQ,
    TOPIC_DIAGNOSTICS_DLQ,
    PRODUCER_BASE_CONFIG,
    CONSUMER_BASE_CONFIG,
)
from streaming.schemas.telemetry_event import TelemetryEvent
from streaming.schemas.diagnostic_event import DiagnosticEvent
from streaming.producers.telemetry_producer import TelemetryProducer
from streaming.producers.diagnostics_producer import DiagnosticsProducer
from streaming.consumers.dlq_handler import DLQHandler
from streaming.consumers.telemetry_consumer import TelemetryConsumer
from streaming.consumers.diagnostics_consumer import DiagnosticsConsumer
from streaming.compaction import StreamingCompactor


class TestEventSchemas:
    """Test suite for event validation schemas."""

    def test_valid_telemetry_event(self):
        event = TelemetryEvent(
            vehicle_id="VH001",
            timestamp=datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc),
            rpm=3200.0,
            temperature=88.5,
            battery=92.0,
            vibration=1.2,
        )
        assert event.vehicle_id == "VH001"
        assert event.rpm == 3200.0

        b_dict = event.to_business_dict()
        assert "vehicle_id" in b_dict
        assert "_producer_id" not in b_dict
        assert "_sent_at" not in b_dict

    def test_telemetry_out_of_bounds_rejection(self):
        # RPM > 9000 must fail validation
        with pytest.raises(ValidationError):
            TelemetryEvent(
                vehicle_id="VH001",
                timestamp=datetime.now(timezone.utc),
                rpm=12000.0,  # Invalid
                temperature=85.0,
                battery=80.0,
                vibration=1.0,
            )

        # Battery > 100% must fail validation
        with pytest.raises(ValidationError):
            TelemetryEvent(
                vehicle_id="VH001",
                timestamp=datetime.now(timezone.utc),
                rpm=3000.0,
                temperature=85.0,
                battery=150.0,  # Invalid
                vibration=1.0,
            )

    def test_valid_diagnostic_event(self):
        event = DiagnosticEvent(
            vehicle_id="VH002",
            timestamp=datetime(2026, 9, 25, 14, 30, 0, tzinfo=timezone.utc),
            code="P0300",
            component="Engine",
            severity="CRITICAL",
        )
        assert event.code == "P0300"
        assert event.severity == "CRITICAL"

        b_dict = event.to_business_dict()
        assert b_dict["code"] == "P0300"
        assert "_kafka_topic" not in b_dict

    def test_diagnostic_invalid_severity_rejection(self):
        with pytest.raises(ValidationError):
            DiagnosticEvent(
                vehicle_id="VH002",
                timestamp=datetime.now(timezone.utc),
                code="P0300",
                component="Engine",
                severity="UNKNOWN_SEVERITY_LEVEL",
            )


class TestProducersAndAffinity:
    """Test suite for Kafka producers, configuration, and partition key affinity."""

    def test_producer_idempotent_configuration(self):
        # Producer must have enable.idempotence=True
        assert PRODUCER_BASE_CONFIG["enable.idempotence"] is True
        assert PRODUCER_BASE_CONFIG["acks"] == "all"

    def test_telemetry_producer_key_partition_affinity(self):
        producer = TelemetryProducer(mock_mode=True)
        event_1 = TelemetryEvent(
            vehicle_id="VH001",
            timestamp=datetime(2026, 9, 25, 10, 0, 0, tzinfo=timezone.utc),
            rpm=2500.0,
            temperature=80.0,
            battery=95.0,
            vibration=0.8,
        )
        event_2 = TelemetryEvent(
            vehicle_id="VH001",
            timestamp=datetime(2026, 9, 25, 10, 1, 0, tzinfo=timezone.utc),
            rpm=2700.0,
            temperature=82.0,
            battery=94.5,
            vibration=0.9,
        )

        assert producer.send_event(event_1) is True
        assert producer.send_event(event_2) is True
        assert len(producer.delivered_records) == 2

        # Both records for VH001 must have key 'VH001' and map to identical partition
        rec1 = producer.delivered_records[0]
        rec2 = producer.delivered_records[1]
        assert rec1["key"] == "VH001"
        assert rec2["key"] == "VH001"
        assert rec1["partition"] == rec2["partition"]

    def test_diagnostics_producer_delivery(self):
        producer = DiagnosticsProducer(mock_mode=True)
        event = DiagnosticEvent(
            vehicle_id="VH005",
            timestamp=datetime(2026, 9, 25, 11, 0, 0, tzinfo=timezone.utc),
            code="P0420",
            component="Catalyst",
            severity="WARNING",
        )
        assert producer.send_event(event) is True
        assert len(producer.delivered_records) == 1
        assert producer.delivered_records[0]["key"] == "VH005"


class TestDLQAndConsumers:
    """Test suite for Dead-Letter Queue routing and consumer batch landing."""

    def test_dlq_routing_malformed_json(self):
        dlq = DLQHandler(mock_mode=True)
        consumer = TelemetryConsumer(mock_mode=True, dlq_handler=dlq)

        # Poison pill (invalid JSON string)
        result = consumer.process_message_payload(
            raw_val="NOT_VALID_JSON{{{",
            topic=TOPIC_TELEMETRY,
            partition=0,
            offset=101,
            key="VH999",
        )
        assert result is None
        assert len(dlq.dlq_records) == 1
        dlq_entry = dlq.dlq_records[0]
        assert "CORRUPT_JSON" in dlq_entry["_dlq_reason"]
        assert dlq_entry["_original_key"] == "VH999"
        assert dlq_entry["_original_topic"] == TOPIC_TELEMETRY

    def test_dlq_routing_schema_violation(self):
        dlq = DLQHandler(mock_mode=True)
        consumer = TelemetryConsumer(mock_mode=True, dlq_handler=dlq)

        # Schema violation: rpm exceeds physical threshold
        invalid_payload = {
            "vehicle_id": "VH001",
            "timestamp": "2026-09-25T12:00:00Z",
            "rpm": 99999.0,  # Bounded <= 9000
            "temperature": 85.0,
            "battery": 80.0,
            "vibration": 1.0,
        }
        result = consumer.process_message_payload(
            raw_val=invalid_payload,
            topic=TOPIC_TELEMETRY,
            partition=1,
            offset=205,
            key="VH001",
        )
        assert result is None
        assert len(dlq.dlq_records) == 1
        assert "VALIDATION_ERROR" in dlq.dlq_records[0]["_dlq_reason"]

    def test_consumer_micro_batch_landing(self, tmp_path):
        landing_dir = tmp_path / "streaming_telemetry"
        dlq = DLQHandler(mock_mode=True)
        consumer = TelemetryConsumer(landing_dir=landing_dir, dlq_handler=dlq, mock_mode=True)

        mock_batch = [
            {
                "key": "VH001",
                "value": {
                    "vehicle_id": "VH001",
                    "timestamp": "2026-09-25T12:00:00Z",
                    "rpm": 3000.0,
                    "temperature": 85.0,
                    "battery": 90.0,
                    "vibration": 1.1,
                },
            },
            {
                "key": "VH002",
                "value": {
                    "vehicle_id": "VH002",
                    "timestamp": "2026-09-25T12:00:00Z",
                    "rpm": 3200.0,
                    "temperature": 87.0,
                    "battery": 88.0,
                    "vibration": 1.3,
                },
            },
            {
                "key": "VH003",
                "value": "CORRUPT_PAYLOAD",  # Should route to DLQ
            },
        ]

        valid_cnt, dlq_cnt, files = consumer.consume_batch(mock_messages=mock_batch)
        assert valid_cnt == 2
        assert dlq_cnt == 1
        assert len(files) == 1
        assert files[0].exists()

        # Read back parquet file and verify contents
        table = pq.read_table(str(files[0]))
        df = table.to_pandas()
        assert len(df) == 2
        assert set(df["vehicle_id"]) == {"VH001", "VH002"}
        assert "rpm" in df.columns


class TestStreamingCompactionAndConservation:
    """Test suite for StreamingCompactor row conservation and duplicate quarantine."""

    def test_compaction_row_conservation_and_deduplication(self, tmp_path):
        streaming_t_dir = tmp_path / "bronze_streaming" / "telemetry"
        silver_t_dir = tmp_path / "silver" / "telemetry"
        quarantine_t_dir = tmp_path / "silver" / "quarantine" / "telemetry"

        # Create 1 pre-existing Silver record
        existing_df = pd.DataFrame([{
            "vehicle_id": "VH001",
            "timestamp": pd.to_datetime("2026-09-25 10:00:00+00:00"),
            "rpm": 2500.0,
            "temperature": 80.0,
            "battery": 90.0,
            "vibration": 1.0,
        }])
        exist_part = silver_t_dir / "year=2026" / "month=9" / "day=25"
        exist_part.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(existing_df), str(exist_part / "part-0.parquet"))

        # Create streaming micro-batches:
        # 1 unique new record (VH002)
        # 1 duplicate of existing Silver (VH001, 10:00:00)
        # 1 duplicate within streaming batch itself (VH002 duplicate)
        # Total streaming input = 3 rows
        stream_part = streaming_t_dir / "year=2026" / "month=09" / "day=25" / "hour=11"
        stream_part.mkdir(parents=True, exist_ok=True)

        batch_df = pd.DataFrame([
            {
                "vehicle_id": "VH002",
                "timestamp": pd.to_datetime("2026-09-25 11:00:00+00:00"),
                "rpm": 2800.0,
                "temperature": 82.0,
                "battery": 85.0,
                "vibration": 1.2,
            },
            {
                "vehicle_id": "VH001",
                "timestamp": pd.to_datetime("2026-09-25 10:00:00+00:00"),  # Duplicate of existing
                "rpm": 2500.0,
                "temperature": 80.0,
                "battery": 90.0,
                "vibration": 1.0,
            },
            {
                "vehicle_id": "VH002",
                "timestamp": pd.to_datetime("2026-09-25 11:00:00+00:00"),  # Duplicate within batch
                "rpm": 2850.0,
                "temperature": 82.5,
                "battery": 84.8,
                "vibration": 1.2,
            },
        ])
        pq.write_table(pa.Table.from_pandas(batch_df), str(stream_part / "batch_01.parquet"))

        compactor = StreamingCompactor(
            streaming_telemetry_dir=streaming_t_dir,
            silver_telemetry_dir=silver_t_dir,
            quarantine_telemetry_dir=quarantine_t_dir,
        )

        res = compactor.compact_telemetry(batch_id="test_run_01")
        assert res["input_count"] == 3
        assert res["silver_added"] == 1       # Only VH002 unique row
        assert res["quarantine_added"] == 2   # 2 duplicate rows
        assert res["conservation_verified"] is True
        assert res["input_count"] == res["silver_added"] + res["quarantine_added"]

        # Check quarantine parquet file content
        q_files = list(quarantine_t_dir.glob("*.parquet"))
        assert len(q_files) == 1
        q_table = pq.read_table(str(q_files[0]))
        q_df = q_table.to_pandas()
        assert len(q_df) == 2
        assert all(q_df["_quarantine_rule"] == "DUPLICATE_KEY")
