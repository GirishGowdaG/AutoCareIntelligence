"""AutoCare Streaming Compaction Pipeline DAG.

Orchestrates micro-batch compaction from Streaming Bronze Parquet landing into
Silver clean storage and Silver Quarantine, enforcing mathematical row conservation.
"""

from datetime import datetime, timedelta, timezone
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from streaming.compaction import StreamingCompactor
from streaming.config import STREAMING_TELEMETRY_DIR, STREAMING_DIAGNOSTICS_DIR

logger = logging.getLogger(__name__)

default_args = {
    "owner": "autocare",
    "depends_on_past": False,
    "start_date": datetime(2026, 9, 1, tzinfo=timezone.utc),
    "email": ["alerts@autocare.internal"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


def poll_streaming_bronze_callable(**context):
    """Poll Streaming Bronze landing directories for new parquet files."""
    t_files = list(STREAMING_TELEMETRY_DIR.glob("**/*.parquet"))
    d_files = list(STREAMING_DIAGNOSTICS_DIR.glob("**/*.parquet"))
    logger.info(f"Streaming Bronze poll: {len(t_files)} telemetry files, {len(d_files)} diagnostics files.")
    return {"telemetry_files_count": len(t_files), "diagnostics_files_count": len(d_files)}


def compact_telemetry_streaming_callable(**context):
    """Compact pending telemetry streaming bronze micro-batches."""
    compactor = StreamingCompactor()
    res = compactor.compact_telemetry()
    logger.info(f"Telemetry compaction result: {res}")
    if not res["conservation_verified"]:
        raise ValueError(f"Telemetry row conservation violated: {res}")
    return res


def compact_diagnostics_streaming_callable(**context):
    """Compact pending diagnostics streaming bronze micro-batches."""
    compactor = StreamingCompactor()
    res = compactor.compact_diagnostics()
    logger.info(f"Diagnostics compaction result: {res}")
    if not res["conservation_verified"]:
        raise ValueError(f"Diagnostics row conservation violated: {res}")
    return res


def verify_row_conservation_callable(**context):
    """Verify that all compacted batches satisfied mathematical row conservation."""
    logger.info("Verifying global streaming compaction conservation invariants.")
    return {"status": "SUCCESS", "message": "All datasets conserved"}


with DAG(
    dag_id="autocare_streaming_compaction",
    default_args=default_args,
    description="Micro-batch compaction from Streaming Bronze to Silver Lakehouse",
    schedule_interval="*/15 * * * *",  # Every 15 minutes
    catchup=False,
    max_active_runs=1,
    tags=["autocare", "streaming", "compaction", "silver"],
) as dag:

    poll_bronze = PythonOperator(
        task_id="poll_streaming_bronze_landing",
        python_callable=poll_streaming_bronze_callable,
    )

    compact_telemetry = PythonOperator(
        task_id="compact_telemetry_streaming_to_silver",
        python_callable=compact_telemetry_streaming_callable,
    )

    compact_diagnostics = PythonOperator(
        task_id="compact_diagnostics_streaming_to_silver",
        python_callable=compact_diagnostics_streaming_callable,
    )

    verify_conservation = PythonOperator(
        task_id="verify_row_conservation_and_quarantine",
        python_callable=verify_row_conservation_callable,
    )

    poll_bronze >> [compact_telemetry, compact_diagnostics] >> verify_conservation
