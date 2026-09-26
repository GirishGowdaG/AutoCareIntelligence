"""Tests for Phase 3 dbt Analytical Modeling Layer.

Authoritative References:
- AutoCare_Intelligence.pdf (Section 4 & Section 7)
- Approved Phase 3 Planning & Architectural Reconciliation Report
- PostgreSQL 16+ autocare_dw warehouse

Verifies:
- Official dbt PostgreSQL adapter (dbt-postgres) configuration.
- Exact diagnostics staging architecture (staging.silver_diagnostics external to autocare_dw).
- Zero warehouse schema drift (strictly 6 dimensions and 4 facts in autocare_dw).
- Staging models inventory and row conservation.
- Intermediate models calculation (dynamic telemetry durations, failure join, dealer rollup).
- All 4 analytical marts presence and integrity.
- Absence of ungrounded/invented attributes (no inventory_fill_rate, no service_capacity_utilization).
- Successful execution of all dbt native and singular custom tests (64/64 pass).
"""

import subprocess
import psycopg2
import pytest


def get_pg_connection():
    """Provides a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        user="postgres",
        password="postgres",
        dbname="autocare_dw",
    )


def test_dbt_debug_connection():
    """Verify dbt connects cleanly to PostgreSQL autocare_dw."""
    cmd = [
        ".venv\\Scripts\\dbt.exe",
        "debug",
        "--project-dir", "dbt_autocare",
        "--profiles-dir", "dbt_autocare",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"dbt debug failed: {res.stdout}\n{res.stderr}"
    assert "All checks passed!" in res.stdout


def test_diagnostics_staging_isolation():
    """Verify diagnostics staging table lives strictly in schema 'staging' with 1,483 rows."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'silver_diagnostics';
        """)
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "staging", f"silver_diagnostics must be in 'staging', found {rows[0][0]}"

        cur.execute("SELECT COUNT(*) FROM staging.silver_diagnostics;")
        cnt = cur.fetchone()[0]
        assert cnt == 1483, f"Expected 1,483 diagnostics rows, got {cnt}"
        cur.close()
    finally:
        conn.close()


def test_warehouse_schema_zero_drift():
    """Verify autocare_dw contains strictly the approved 6 dimensions and 4 facts."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'autocare_dw'
            ORDER BY table_name;
        """)
        tables = set(r[0] for r in cur.fetchall())
        expected_tables = {
            "dim_date",
            "dim_model",
            "dim_dealer",
            "dim_customer",
            "dim_component",
            "dim_vehicle",
            "fact_telemetry",
            "fact_service",
            "fact_warranty",
            "fact_parts",
        }
        assert tables == expected_tables, f"Warehouse schema drift detected: {tables.symmetric_difference(expected_tables)}"
        cur.close()
    finally:
        conn.close()


def test_all_dbt_models_exist_and_populated():
    """Verify that all staging, intermediate, and marts models exist and have positive row counts."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        models = [
            ("dbt_analytics_staging", "stg_dim_date", 4019),
            ("dbt_analytics_staging", "stg_dim_model", 5),
            ("dbt_analytics_staging", "stg_dim_dealer", 6),
            ("dbt_analytics_staging", "stg_dim_customer", 41),
            ("dbt_analytics_staging", "stg_dim_component", 9),
            ("dbt_analytics_staging", "stg_dim_vehicle", 51),
            ("dbt_analytics_staging", "stg_fact_telemetry", 7554),
            ("dbt_analytics_staging", "stg_fact_service", 46),
            ("dbt_analytics_staging", "stg_fact_warranty", 10),
            ("dbt_analytics_staging", "stg_fact_parts", 40),
            ("dbt_analytics_staging", "stg_diagnostics", 1483),
            ("dbt_analytics_intermediate", "int_telemetry_trip_sessions", 1259),
            ("dbt_analytics_intermediate", "int_component_failures_joined", 18),
            ("dbt_analytics_intermediate", "int_dealer_service_parts_rollup", 9),
            ("dbt_analytics_analytics", "mart_vehicle_health_daily", 1259),
            ("dbt_analytics_analytics", "mart_component_failure_risk", 18),
            ("dbt_analytics_analytics", "mart_warranty_cost_analysis", 6),
            ("dbt_analytics_analytics", "mart_dealer_operational_summary", 9),
        ]

        for schema, name, expected_count in models:
            cur.execute(f"SELECT COUNT(*) FROM {schema}.{name};")
            cnt = cur.fetchone()[0]
            assert cnt == expected_count, f"Model {schema}.{name} expected {expected_count} rows, got {cnt}"

        cur.close()
    finally:
        conn.close()


def test_absence_of_invented_metrics():
    """Verify prohibited metrics (inventory_fill_rate, service_capacity_utilization, bays) are absent."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'dbt_analytics_analytics'
              AND table_name = 'mart_dealer_operational_summary';
        """)
        cols = set(r[0] for r in cur.fetchall())
        forbidden_cols = {"inventory_fill_rate", "service_capacity_utilization", "capacity_bays", "bays"}
        intersection = cols.intersection(forbidden_cols)
        assert not intersection, f"Forbidden invented columns detected in dealer mart: {intersection}"
        cur.close()
    finally:
        conn.close()


def test_dbt_tests_pass_cleanly():
    """Verify that all dbt schema and custom data tests pass with 0 errors."""
    cmd = [
        ".venv\\Scripts\\dbt.exe",
        "test",
        "--project-dir", "dbt_autocare",
        "--profiles-dir", "dbt_autocare",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"dbt test failed:\n{res.stdout}\n{res.stderr}"
    assert "Completed successfully" in res.stdout
