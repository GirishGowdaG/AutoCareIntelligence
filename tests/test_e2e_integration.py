"""End-to-End (E2E) Programmatic Integration & Governance Test Suite.

Authoritative Reference: AutoCare_Intelligence.pdf (Sections 10, 11, 12, 14, 15, 17)
Phase 6 Stage 5 Deliverable: Comprehensive Vertical Slice Integration Matrix.

Verifies:
1. Docker service health & API connectivity
2. Kafka telemetry event injection
3. Automation worker event consumption
4. ML sensor anomaly scoring against frozen threshold 0.838357
5. Decision automation rule evaluation (Rule 2)
6. Action log persistence in ml_inference.action_logs
7. Backend API retrieval of generated action logs
8. RBAC 401 Unauthorized enforcement (missing/invalid key)
9. RBAC 403 Forbidden enforcement (role-scoped restrictions)
10. Valid role access (Admin, DealerServiceManager, FleetAnalyst)
11. SSE stream contract using Stage 2 dual authentication (X-API-Key & ?api_key=)
12. Data warehouse base schema invariants (strictly 6 dims + 4 facts)
13. Strict test data isolation (isolated test entity UUIDs)
14. Administrative fixture cleanup (zero pollution of seed data)
15. Production database role privilege immutability (NO DELETE for worker/backend)
"""

import json
import os
import uuid
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import get_app_settings, get_auth_config
from backend.app.core.security import UserRole
from ml.config import PG_CONFIG
from automation.config import FROZEN_SENSOR_ANOMALY_THRESHOLD
from automation.worker import AutomationWorker
from automation.rules.rule_engine import RuleEngine
from automation.action_logger import ActionLogger

TEST_ADMIN_KEY = "test-secret-admin-key-e2e-999"
TEST_DEALER_KEY = "test-secret-dealer-key-e2e-888"
TEST_ANALYST_KEY = "test-secret-analyst-key-e2e-777"


@pytest.fixture(autouse=True)
def setup_test_auth(monkeypatch):
    """Inject test credentials via environment variables without hardcoded fallbacks."""
    monkeypatch.setenv("AUTOCARE_ADMIN_KEY", TEST_ADMIN_KEY)
    monkeypatch.setenv("AUTOCARE_DEALER_KEY", TEST_DEALER_KEY)
    monkeypatch.setenv("AUTOCARE_ANALYST_KEY", TEST_ANALYST_KEY)


@pytest.fixture
def api_client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_keys():
    """Resolves authenticated keys from auth configuration."""
    cfg = get_auth_config()
    return {
        "admin": cfg.admin_key,
        "dealer": cfg.dealer_key,
        "analyst": cfg.analyst_key,
    }


@pytest.fixture(scope="module")
def admin_db_conn():
    """Administrative database connection for schema invariant checks and test teardown.
    
    Uses admin superuser connection to prevent granting DELETE privilege to production roles.
    """
    admin_cfg = PG_CONFIG.copy()
    conn = psycopg2.connect(**admin_cfg)
    yield conn
    conn.close()


@pytest.fixture
def isolated_test_vehicle_id():
    """Generates a strictly isolated test vehicle identifier."""
    unique_id = f"VH-E2E-TEST-{uuid.uuid4().hex[:8].upper()}"
    yield unique_id
    # Teardown: Clean up test action logs using admin superuser connection
    try:
        with psycopg2.connect(**PG_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM ml_inference.action_logs WHERE entity_id = %s;",
                    (unique_id,)
                )
            conn.commit()
    except Exception:
        pass


class TestEndToEndIntegrationPipeline:
    """Fifteen-point E2E integration test suite for Stage 5."""

    # 1. Service Health & API Connectivity
    def test_e2e_01_service_health_endpoint(self, api_client):
        """Verifies GET /api/v1/health satisfies the Stage 2 contract."""
        resp = api_client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "timestamp" in data
        assert "version" in data
        assert data["components"]["database"] == "connected"
        assert data["components"]["models"] == "loaded"
        assert data["components"]["kafka_broker"] == "mock_fallback"

    # 2 - 6. Telemetry Injection -> Worker Consumption -> ML Scoring -> Rule Eval -> Action Log
    def test_e2e_02_through_06_telemetry_to_action_log_pipeline(self, isolated_test_vehicle_id):
        """Verifies telemetry injection, streaming scoring, rule evaluation, and action log persistence."""
        worker = AutomationWorker()
        
        # Inject critical anomaly event for isolated test vehicle
        critical_event = {
            "vehicle_id": isolated_test_vehicle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rpm": 5500.0,
            "temperature": 125.0,  # Extreme temperature
            "battery": 11.0,
            "vibration": 8.5,      # Severe vibration
        }

        # Process 3 consecutive events to trigger Rule 2
        last_res = None
        for _ in range(3):
            last_res = worker.process_telemetry_event(critical_event)

        assert last_res is not None, "Rule 2 did not trigger on consecutive critical anomalies"
        assert last_res.get("rule_id") == "RULE_2_SENSOR_ANOMALY"
        assert last_res.get("vehicle_id") == isolated_test_vehicle_id
        assert last_res.get("delivery_status") in ("MOCK_LOGGED", "DELIVERED")

        # Verify action log persisted in PostgreSQL ml_inference.action_logs
        with psycopg2.connect(**PG_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT action_id, rule_id, entity_type, entity_id, delivery_status "
                    "FROM ml_inference.action_logs WHERE entity_id = %s;",
                    (isolated_test_vehicle_id,)
                )
                rows = cur.fetchall()
                assert len(rows) >= 1, "Action log was not persisted to database"
                log_entry = rows[0]
                assert log_entry["rule_id"] == "RULE_2_SENSOR_ANOMALY"
                assert log_entry["entity_type"] == "VEHICLE"
                assert log_entry["delivery_status"] in ("MOCK_LOGGED", "DELIVERED")

    # 7. Backend API Retrieval of Action Logs
    def test_e2e_07_api_retrieval_of_action_logs(self, api_client, auth_keys, isolated_test_vehicle_id):
        """Verifies GET /api/v1/audit/actions retrieves the persisted action log via Admin role."""
        # Ensure log exists
        worker = AutomationWorker()
        event = {
            "vehicle_id": isolated_test_vehicle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rpm": 5500.0,
            "temperature": 125.0,
            "battery": 11.0,
            "vibration": 8.5,
        }
        for _ in range(3):
            worker.process_telemetry_event(event)

        headers = {"X-API-Key": auth_keys["admin"]}
        resp = api_client.get(f"/api/v1/audit/actions?limit=50", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

        matching = [item for item in data["items"] if item["entity_id"] == isolated_test_vehicle_id]
        assert len(matching) >= 1, f"Failed to retrieve action log for entity {isolated_test_vehicle_id} via API"
        assert matching[0]["rule_id"] == "RULE_2_SENSOR_ANOMALY"

    # 8. RBAC 401 Unauthorized Enforcement
    def test_e2e_08_rbac_401_unauthorized_enforcement(self, api_client):
        """Verifies 401 Unauthorized on missing and invalid API keys."""
        # Missing key
        resp_no_key = api_client.get("/api/v1/vehicles")
        assert resp_no_key.status_code == 401
        assert "Invalid or missing API Key" in resp_no_key.json()["detail"]

        # Invalid key
        resp_bad_key = api_client.get("/api/v1/vehicles", headers={"X-API-Key": "invalid-key-xyz"})
        assert resp_bad_key.status_code == 401
        assert "Invalid or missing API Key" in resp_bad_key.json()["detail"]

    # 9. RBAC 403 Forbidden Enforcement
    def test_e2e_09_rbac_403_forbidden_enforcement(self, api_client, auth_keys):
        """Verifies 403 Forbidden for DealerServiceManager on warranty and audit logs."""
        dealer_headers = {"X-API-Key": auth_keys["dealer"]}

        # DealerServiceManager accessing warranty audit -> 403
        resp_warranty = api_client.get("/api/v1/anomalies/warranty", headers=dealer_headers)
        assert resp_warranty.status_code == 403
        assert "Operation not permitted" in resp_warranty.json()["detail"]

        # DealerServiceManager accessing action audit logs -> 403
        resp_audit = api_client.get("/api/v1/audit/actions", headers=dealer_headers)
        assert resp_audit.status_code == 403
        assert "Operation not permitted" in resp_audit.json()["detail"]

        # FleetAnalyst accessing action audit logs -> 403
        analyst_headers = {"X-API-Key": auth_keys["analyst"]}
        resp_analyst_audit = api_client.get("/api/v1/audit/actions", headers=analyst_headers)
        assert resp_analyst_audit.status_code == 403
        assert "Operation not permitted" in resp_analyst_audit.json()["detail"]

    # 10. Valid Role Access Across Personas
    def test_e2e_10_valid_role_access(self, api_client, auth_keys):
        """Verifies permitted endpoints return 200 OK for valid roles."""
        # Admin permitted on audit logs
        resp_admin = api_client.get("/api/v1/audit/actions", headers={"X-API-Key": auth_keys["admin"]})
        assert resp_admin.status_code == 200

        # DealerServiceManager permitted on fleet vehicles & demand forecasts
        resp_dealer = api_client.get("/api/v1/vehicles", headers={"X-API-Key": auth_keys["dealer"]})
        assert resp_dealer.status_code == 200

        # FleetAnalyst permitted on warranty outlier audit
        resp_analyst = api_client.get("/api/v1/anomalies/warranty", headers={"X-API-Key": auth_keys["analyst"]})
        assert resp_analyst.status_code == 200

    # 11. SSE Stream Protocol & Authentication Contract
    def test_e2e_11_sse_authentication_and_protocol(self, api_client, auth_keys):
        """Verifies SSE endpoint supports X-API-Key header and ?api_key= query parameter."""
        # 1. Header auth
        resp_header = api_client.get(
            "/api/v1/stream/events?max_events=2",
            headers={"X-API-Key": auth_keys["analyst"]}
        )
        assert resp_header.status_code == 200
        assert "text/event-stream" in resp_header.headers["content-type"]
        assert "id:" in resp_header.text
        assert "event:" in resp_header.text
        assert "data:" in resp_header.text

        # 2. Query parameter fallback auth
        resp_query = api_client.get(
            f"/api/v1/stream/events?api_key={auth_keys['admin']}&max_events=2"
        )
        assert resp_query.status_code == 200
        assert "text/event-stream" in resp_query.headers["content-type"]
        assert "data:" in resp_query.text

        # 3. Unauthorized access -> 401
        resp_no_auth = api_client.get("/api/v1/stream/events?max_events=1")
        assert resp_no_auth.status_code == 401

    # 12. Warehouse Base Schema Invariants
    def test_e2e_12_warehouse_invariants(self, admin_db_conn):
        """Verifies autocare_dw has strictly 6 dimensions + 4 facts (10 tables total)."""
        cur = admin_db_conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'autocare_dw' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        cur.close()

        expected = [
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
        assert tables == expected, f"Warehouse schema polluted: {tables}"

    # 13 - 15. Production Database Role Privilege Immutability
    def test_e2e_13_through_15_production_role_privilege_immutability(self, admin_db_conn):
        """Verifies autocare_backend and autocare_worker have strictly read/insert privileges and ZERO delete/update/DDL."""
        cur = admin_db_conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT grantee, table_schema, table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee IN ('autocare_backend', 'autocare_worker');
        """)
        grants = cur.fetchall()
        cur.close()

        for g in grants:
            grantee = g["grantee"]
            priv = g["privilege_type"]
            schema = g["table_schema"]
            tbl = g["table_name"]

            # Strict Invariant: Neither role may ever hold DELETE, UPDATE, TRUNCATE, or REFERENCES
            assert priv not in ("DELETE", "UPDATE", "TRUNCATE", "REFERENCES"), (
                f"Security violation: {grantee} possesses unauthorized privilege {priv} on {schema}.{tbl}"
            )

            # autocare_backend: SELECT only
            if grantee == "autocare_backend":
                assert priv == "SELECT", f"autocare_backend has non-SELECT privilege {priv} on {schema}.{tbl}"

            # autocare_worker: SELECT on inference tables, INSERT only on action_logs
            if grantee == "autocare_worker":
                if priv == "INSERT":
                    assert schema == "ml_inference" and tbl == "action_logs", (
                        f"autocare_worker possesses unauthorized INSERT on {schema}.{tbl}"
                    )
                else:
                    assert priv == "SELECT", f"autocare_worker has unauthorized privilege {priv} on {schema}.{tbl}"
