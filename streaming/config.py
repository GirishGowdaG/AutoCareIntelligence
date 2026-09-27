"""Streaming configuration and topic definitions for AutoCare Intelligence.

Defines topic names, partition counts, retention periods, broker defaults,
consumer groups, and landing directory paths.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass(frozen=True)
class TopicConfig:
    name: str
    partitions: int
    replication_factor: int
    retention_ms: int
    cleanup_policy: str = "delete"


# Approved Kafka Topics (selected local/development configuration)
TOPIC_TELEMETRY = "vehicle-telemetry"
TOPIC_DIAGNOSTICS = "vehicle-diagnostics"
TOPIC_TELEMETRY_DLQ = "vehicle-telemetry-dlq"
TOPIC_DIAGNOSTICS_DLQ = "vehicle-diagnostics-dlq"

TOPIC_CONFIGS: Dict[str, TopicConfig] = {
    TOPIC_TELEMETRY: TopicConfig(
        name=TOPIC_TELEMETRY,
        partitions=3,
        replication_factor=1,
        retention_ms=7 * 24 * 3600 * 1000,  # 7 days
    ),
    TOPIC_DIAGNOSTICS: TopicConfig(
        name=TOPIC_DIAGNOSTICS,
        partitions=3,
        replication_factor=1,
        retention_ms=30 * 24 * 3600 * 1000,  # 30 days
    ),
    TOPIC_TELEMETRY_DLQ: TopicConfig(
        name=TOPIC_TELEMETRY_DLQ,
        partitions=1,
        replication_factor=1,
        retention_ms=14 * 24 * 3600 * 1000,  # 14 days
    ),
    TOPIC_DIAGNOSTICS_DLQ: TopicConfig(
        name=TOPIC_DIAGNOSTICS_DLQ,
        partitions=1,
        replication_factor=1,
        retention_ms=14 * 24 * 3600 * 1000,  # 14 days
    ),
}

# Broker & Connection Defaults
DEFAULT_BOOTSTRAP_SERVERS = "localhost:9092"
DEFAULT_CONSUMER_GROUP = "autocare-streaming-bronze-group"
DEFAULT_SIMULATION_TARGET_HZ = 100  # Proposed simulation load target (configurable)

# Producer Base Configuration
PRODUCER_BASE_CONFIG: Dict[str, Any] = {
    "bootstrap.servers": DEFAULT_BOOTSTRAP_SERVERS,
    "enable.idempotence": True,  # Idempotent producer delivery, protects against duplicate retries
    "acks": "all",
    "retries": 5,
    "max.in.flight.requests.per.connection": 5,
    "compression.type": "snappy",
    "linger.ms": 20,
    "batch.num.messages": 1000,
}

# Consumer Base Configuration
CONSUMER_BASE_CONFIG: Dict[str, Any] = {
    "bootstrap.servers": DEFAULT_BOOTSTRAP_SERVERS,
    "group.id": DEFAULT_CONSUMER_GROUP,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,  # Offsets committed synchronously only after successful batch landing
    "max.poll.interval.ms": 300000,
}

# Storage Landing Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STREAMING_BRONZE_DIR = BASE_DIR / "data" / "bronze" / "streaming"
STREAMING_TELEMETRY_DIR = STREAMING_BRONZE_DIR / "telemetry"
STREAMING_DIAGNOSTICS_DIR = STREAMING_BRONZE_DIR / "diagnostics"

SILVER_DIR = BASE_DIR / "data" / "silver"
SILVER_TELEMETRY_DIR = SILVER_DIR / "telemetry"
SILVER_DIAGNOSTICS_DIR = SILVER_DIR / "diagnostics"

SILVER_QUARANTINE_DIR = SILVER_DIR / "quarantine"
QUARANTINE_TELEMETRY_DIR = SILVER_QUARANTINE_DIR / "telemetry"
QUARANTINE_DIAGNOSTICS_DIR = SILVER_QUARANTINE_DIR / "diagnostics"

AIRFLOW_STATE_DIR = BASE_DIR / "airflow" / "state"
INGESTION_MANIFEST_PATH = AIRFLOW_STATE_DIR / "ingestion_manifest.json"
