"""AutoCare Intelligence — Diagnostics Lakehouse-to-PostgreSQL Staging Bridge.

Authoritative Reference:
- Phase 3 Approved Architecture
- Lakehouse Silver Layer: data/silver/diagnostics/

Design:
- Bridges Silver diagnostics Parquet files into an isolated PostgreSQL schema: staging.silver_diagnostics.
- Strictly OUTSIDE autocare_dw warehouse schema (preserves frozen 4-fact star schema).
- Deterministic primary key generated as MD5(vehicle_id || '|' || timestamp || '|' || code).
- Fully idempotent: ON CONFLICT (diagnostic_id) DO UPDATE.
"""

import hashlib
import logging
import os
from pathlib import Path
import sys
from typing import Dict, Optional

import psycopg2
from psycopg2.extras import execute_values
import pyarrow.dataset as ds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("diagnostics_staging_loader")

SILVER_DIAGNOSTICS_DIR = Path("data/silver/diagnostics")


def get_db_connection():
    """Returns a connection to the PostgreSQL database."""
    host = os.environ.get("AUTOCARE_DB_HOST", "127.0.0.1")
    port = int(os.environ.get("AUTOCARE_DB_PORT", 5432))
    user = os.environ.get("AUTOCARE_DB_USER", "postgres")
    password = os.environ.get("AUTOCARE_DB_PASSWORD", "postgres")
    dbname = os.environ.get("AUTOCARE_DB_NAME", "autocare_dw")

    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
    )


def init_staging_schema(conn) -> None:
    """Creates the isolated staging schema and silver_diagnostics table."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS staging;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS staging.silver_diagnostics (
                diagnostic_id VARCHAR(64) PRIMARY KEY,
                vehicle_id VARCHAR(32) NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                code VARCHAR(16) NOT NULL,
                component VARCHAR(64) NOT NULL,
                severity VARCHAR(16) NOT NULL,
                _source_file VARCHAR(255),
                _bronze_ingested_at VARCHAR(64),
                _bronze_batch_id VARCHAR(64),
                _silver_processed_at VARCHAR(64),
                _silver_batch_id VARCHAR(64),
                _staging_loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            
            COMMENT ON TABLE staging.silver_diagnostics IS 
            'Isolated staging buffer for Silver lakehouse diagnostics events. Strictly external to autocare_dw.';
        """)
        conn.commit()
    logger.info("Staging schema and staging.silver_diagnostics initialized.")


def load_silver_diagnostics(conn) -> int:
    """Reads Silver diagnostics Parquet files and idempotently upserts to staging."""
    if not SILVER_DIAGNOSTICS_DIR.exists():
        raise FileNotFoundError(f"Diagnostics directory not found: {SILVER_DIAGNOSTICS_DIR}")

    dataset = ds.dataset(str(SILVER_DIAGNOSTICS_DIR), format="parquet")
    table = dataset.to_table()
    df = table.to_pandas()

    logger.info(f"Loaded {len(df)} records from Silver diagnostics dataset.")

    records = []
    for _, row in df.iterrows():
        veh_id = str(row["vehicle_id"])
        ts = row["timestamp"]
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        code = str(row["code"])
        comp = str(row["component"])
        sev = str(row["severity"])

        # Deterministic primary key
        raw_key = f"{veh_id}|{ts_str}|{code}"
        diag_id = hashlib.md5(raw_key.encode("utf-8")).hexdigest()

        records.append((
            diag_id,
            veh_id,
            ts,
            code,
            comp,
            sev,
            str(row.get("_source_file", "")),
            str(row.get("_bronze_ingested_at", "")),
            str(row.get("_bronze_batch_id", "")),
            str(row.get("_silver_processed_at", "")),
            str(row.get("_silver_batch_id", "")),
        ))

    upsert_query = """
        INSERT INTO staging.silver_diagnostics (
            diagnostic_id,
            vehicle_id,
            timestamp,
            code,
            component,
            severity,
            _source_file,
            _bronze_ingested_at,
            _bronze_batch_id,
            _silver_processed_at,
            _silver_batch_id
        ) VALUES %s
        ON CONFLICT (diagnostic_id) DO UPDATE SET
            component = EXCLUDED.component,
            severity = EXCLUDED.severity,
            _silver_processed_at = EXCLUDED._silver_processed_at,
            _silver_batch_id = EXCLUDED._silver_batch_id,
            _staging_loaded_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        execute_values(cur, upsert_query, records, page_size=2000)
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM staging.silver_diagnostics;")
        count = cur.fetchone()[0]

    logger.info(f"Successfully loaded staging.silver_diagnostics: {count} total rows.")
    return count


def main():
    conn = get_db_connection()
    try:
        init_staging_schema(conn)
        cnt = load_silver_diagnostics(conn)
        print(f"\nDiagnostics Staging Ingestion Summary:")
        print(f"  staging.silver_diagnostics: {cnt} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
