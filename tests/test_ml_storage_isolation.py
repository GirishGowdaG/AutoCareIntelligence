"""Integration tests for ML Storage Isolation and Warehouse Invariants in Phase 5.

Verifies that autocare_dw base schema remains strictly 6 dimensions + 4 facts,
and that operational ML outputs reside exclusively in the isolated `ml_inference` schema.
"""

from pathlib import Path
import psycopg2
import pytest

from ml.config import PG_CONFIG, ML_MODELS_DIR, ML_PREDICTIONS_DIR


class TestMLStorageIsolation:
    """Test suite ensuring zero warehouse schema pollution and proper ML storage isolation."""

    @pytest.fixture
    def db_conn(self):
        conn = psycopg2.connect(**PG_CONFIG)
        yield conn
        conn.close()

    def test_warehouse_base_schema_remains_frozen(self, db_conn):
        """Verify autocare_dw has strictly 6 dimensions + 4 facts (10 tables total)."""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'autocare_dw' 
            ORDER BY table_name;
        """)
        tables = [t[0] for t in cur.fetchall()]
        cur.close()

        expected_tables = [
            "dim_component",
            "dim_customer",
            "dim_date",
            "dim_dealer",
            "dim_model",
            "dim_vehicle",
            "fact_parts",
            "fact_service",
            "fact_telemetry",
            "fact_warranty",
        ]
        assert sorted(tables) == sorted(expected_tables), f"Warehouse schema drift detected: {tables}"
        assert len(tables) == 10, "Forbidden fifth fact or altered dimension count detected"

    def test_diagnostics_bridge_remains_intact(self, db_conn):
        """Verify staging.silver_diagnostics remains the active diagnostics bridge."""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'staging' AND table_name = 'silver_diagnostics';
        """)
        exists = cur.fetchone()[0]
        assert exists == 1, "staging.silver_diagnostics bridge missing"

        cur.execute("SELECT COUNT(*) FROM staging.silver_diagnostics;")
        count = cur.fetchone()[0]
        assert count > 0, "staging.silver_diagnostics bridge has zero records"
        cur.close()

    def test_ml_inference_schema_tables(self, db_conn):
        """Verify ml_inference schema contains the 5 operational ML tables."""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'ml_inference' 
            ORDER BY table_name;
        """)
        ml_tables = [t[0] for t in cur.fetchall()]
        cur.close()

        expected_ml_tables = [
            "model_metadata",
            "sensor_anomalies",
            "service_demand_forecasts",
            "vehicle_failure_predictions",
            "warranty_anomalies",
        ]
        # In Phase 6 Stage 1, ml_inference houses the action_logs audit table alongside Phase 5 ML tables
        for expected_table in expected_ml_tables:
            assert expected_table in ml_tables, f"Missing required ML table: {expected_table}"
        assert set(ml_tables) - {"action_logs"} == set(expected_ml_tables)

    def test_model_metadata_registry_records(self, db_conn):
        """Verify model_metadata contains all 4 registered models with actual training commits and metrics."""
        cur = db_conn.cursor()
        cur.execute("SELECT model_id, model_version, training_git_commit, metrics FROM ml_inference.model_metadata;")
        rows = cur.fetchall()
        cur.close()

        assert len(rows) == 4
        for model_id, version, commit, metrics in rows:
            assert commit == "a7fc266", f"Model {model_id} commit mismatch: {commit}"
            assert isinstance(metrics, dict), f"Metrics for {model_id} must be JSON dictionary"
            assert len(metrics) > 0, f"Metrics for {model_id} must not be empty"

    def test_parquet_predictions_archived(self):
        """Verify Parquet archives exist under data/ml/predictions/."""
        assert ML_PREDICTIONS_DIR.exists()
        domains = ["failure_risk", "sensor_anomalies", "service_forecasts", "warranty_anomalies"]
        for domain in domains:
            domain_dir = ML_PREDICTIONS_DIR / domain
            assert domain_dir.exists(), f"Parquet prediction directory missing for {domain}"
            files = list(domain_dir.glob("**/*.parquet"))
            assert len(files) > 0, f"No Parquet prediction files archived for {domain}"
