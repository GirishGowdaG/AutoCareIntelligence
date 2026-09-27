"""Comprehensive Test Suite for AutoCare Intelligence Phase 6 Stage 2 FastAPI & SSE.

Validates:
1. Public Health Endpoint (200 OK, no auth required)
2. Missing X-API-Key Header -> 401 Unauthorized
3. Invalid X-API-Key Header -> 401 Unauthorized
4. Query Parameter Auth Rejected on Standard REST Endpoints -> 401 Unauthorized
5. Admin Full RBAC Access (including /api/v1/audit/actions)
6. DealerServiceManager Forbidden from Action Audit Logs -> 403 Forbidden
7. DealerServiceManager Forbidden from Forensic Warranty Anomalies -> 403 Forbidden
8. FleetAnalyst Forbidden from Action Audit Logs -> 403 Forbidden
9. FleetAnalyst Permitted on Forensic Warranty Anomalies -> 200 OK
10. Action Logs Contract: Validates Delivery Status values (DELIVERED, MOCK_LOGGED, FAILED)
11. Action Logs Contract: Validates Entity Type values (VEHICLE, DEALER, CLAIM)
12. Action Logs Contract: Validates Rule IDs (RULE_1_FAILURE_RISK, RULE_2_SENSOR_ANOMALY, etc.)
13. Vehicles Schema Conformance: dim_vehicle + joined dim_model (no vin, no mileage)
14. Vehicle Diagnostics Schema: staging.silver_diagnostics conformance
15. Sensor Anomalies Manifest Provenance (threshold dynamically loaded from manifest, not hardcoded)
16. SSE Endpoint: Query Parameter Auth Support and Synthetic Demo Tagging (source="synthetic_demo")
17. Read-Only Method Guard: POST/PUT/PATCH/DELETE -> 405 Method Not Allowed
18. Model Governance Status: Ratified Metrics & Threshold Provenance
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import APIAuthConfig
from backend.app.core.thresholds import SENSOR_MANIFEST_PATH, load_frozen_sensor_threshold
from backend.app.main import app


# Test Credential Fixtures
TEST_ADMIN_KEY = "test-secret-admin-key-999"
TEST_DEALER_KEY = "test-secret-dealer-key-888"
TEST_ANALYST_KEY = "test-secret-analyst-key-777"


@pytest.fixture(autouse=True)
def setup_test_auth(monkeypatch):
    """Inject test credentials via environment variables without hardcoded fallbacks."""
    monkeypatch.setenv("AUTOCARE_ADMIN_KEY", TEST_ADMIN_KEY)
    monkeypatch.setenv("AUTOCARE_DEALER_KEY", TEST_DEALER_KEY)
    monkeypatch.setenv("AUTOCARE_ANALYST_KEY", TEST_ANALYST_KEY)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    with TestClient(app) as c:
        yield c


class TestAPIEndpointsStage2:
    """Stage 2 REST and SSE Test Suite."""

    # 1. Public Health Endpoint
    def test_health_endpoint_public_access(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "timestamp" in data
        assert "version" in data
        assert "components" in data
        assert data["components"]["database"] == "connected"
        assert data["components"]["models"] == "loaded"

    # 2. Missing X-API-Key Header -> 401
    def test_unauthenticated_request_fails(self, client):
        response = client.get("/api/v1/vehicles")
        assert response.status_code == 401
        assert "Invalid or missing API Key" in response.json()["detail"]

    # 3. Invalid X-API-Key Header -> 401
    def test_invalid_api_key_fails(self, client):
        response = client.get(
            "/api/v1/vehicles",
            headers={"X-API-Key": "invalid-garbage-key-000"},
        )
        assert response.status_code == 401
        assert "Invalid or missing API Key" in response.json()["detail"]

    # 4. Query Parameter Auth Rejected on Standard REST Endpoints -> 401
    def test_query_param_auth_rejected_on_rest_endpoints(self, client):
        response = client.get(f"/api/v1/vehicles?api_key={TEST_ADMIN_KEY}")
        assert response.status_code == 401

    # 5. Admin Full RBAC Access
    def test_rbac_admin_full_access(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        # Check audit actions (Admin only)
        resp_audit = client.get("/api/v1/audit/actions", headers=headers)
        assert resp_audit.status_code == 200
        # Check warranty (Admin allowed)
        resp_warn = client.get("/api/v1/anomalies/warranty", headers=headers)
        assert resp_warn.status_code == 200
        # Check vehicles
        resp_veh = client.get("/api/v1/vehicles", headers=headers)
        assert resp_veh.status_code == 200

    # 6. DealerServiceManager Forbidden from Action Audit Logs -> 403
    def test_rbac_dealer_forbidden_from_audit(self, client):
        headers = {"X-API-Key": TEST_DEALER_KEY}
        response = client.get("/api/v1/audit/actions", headers=headers)
        assert response.status_code == 403
        assert "Operation not permitted" in response.json()["detail"]

    # 7. DealerServiceManager Forbidden from Forensic Warranty Anomalies -> 403
    def test_rbac_dealer_forbidden_from_warranty(self, client):
        headers = {"X-API-Key": TEST_DEALER_KEY}
        response = client.get("/api/v1/anomalies/warranty", headers=headers)
        assert response.status_code == 403
        assert "Operation not permitted" in response.json()["detail"]

    # 8. FleetAnalyst Forbidden from Action Audit Logs -> 403
    def test_rbac_analyst_forbidden_from_audit(self, client):
        headers = {"X-API-Key": TEST_ANALYST_KEY}
        response = client.get("/api/v1/audit/actions", headers=headers)
        assert response.status_code == 403
        assert "Operation not permitted" in response.json()["detail"]

    # 9. FleetAnalyst Permitted on Forensic Warranty Anomalies -> 200
    def test_rbac_analyst_allowed_warranty(self, client):
        headers = {"X-API-Key": TEST_ANALYST_KEY}
        response = client.get("/api/v1/anomalies/warranty", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    # 10. Action Logs Contract: Validates Delivery Status values
    def test_action_logs_contract_delivery_status(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        response = client.get("/api/v1/audit/actions?limit=50", headers=headers)
        assert response.status_code == 200
        items = response.json()["items"]
        valid_statuses = {"DELIVERED", "MOCK_LOGGED", "FAILED"}
        for item in items:
            assert item["delivery_status"] in valid_statuses
            assert item["delivery_status"] not in ("DISPATCHED", "MOCKED")

    # 11. Action Logs Contract: Validates Entity Type values
    def test_action_logs_contract_entity_type(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        response = client.get("/api/v1/audit/actions?limit=50", headers=headers)
        assert response.status_code == 200
        items = response.json()["items"]
        valid_types = {"VEHICLE", "DEALER", "CLAIM"}
        for item in items:
            assert item["entity_type"] in valid_types
            assert item["entity_type"] != "WARRANTY_CLAIM"

    # 12. Action Logs Contract: Validates Rule IDs
    def test_action_logs_contract_rule_ids(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        response = client.get("/api/v1/audit/actions?limit=50", headers=headers)
        assert response.status_code == 200
        items = response.json()["items"]
        valid_rules = {
            "RULE_1_FAILURE_RISK",
            "RULE_2_SENSOR_ANOMALY",
            "RULE_2_SEVERE_DTC",
            "RULE_3_DEMAND_SURGE",
            "RULE_4_WARRANTY_AUDIT",
        }
        for item in items:
            assert item["rule_id"] in valid_rules

    # 13. Vehicles Schema Conformance (no vin, no mileage)
    def test_vehicles_schema_exact_match(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        response = client.get("/api/v1/vehicles?limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        item = data["items"][0]
        # Assert approved fields exist
        assert "vehicle_id" in item
        assert "variant" in item
        assert "manufacture_year" in item
        assert "manufacture_date" in item
        assert "status" in item
        assert "model_name" in item
        # Assert prohibited invented fields DO NOT exist
        assert "vin" not in item
        assert "mileage" not in item
        assert "make" not in item
        assert "engine_type" not in item

    # 14. Vehicle Diagnostics Schema Conformance
    def test_diagnostics_history_schema(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        # First retrieve a valid vehicle_id
        veh_resp = client.get("/api/v1/vehicles?limit=1", headers=headers)
        assert veh_resp.status_code == 200
        vid = veh_resp.json()["items"][0]["vehicle_id"]

        diag_resp = client.get(f"/api/v1/vehicles/{vid}/diagnostics", headers=headers)
        assert diag_resp.status_code == 200
        data = diag_resp.json()
        assert data["vehicle_id"] == vid
        assert "diagnostics" in data
        if data["diagnostics"]:
            d_item = data["diagnostics"][0]
            assert "diagnostic_id" in d_item
            assert "dtc_code" in d_item
            assert "severity" in d_item

    # 15. Sensor Anomalies Manifest Provenance (dynamically loaded from manifest)
    def test_sensor_anomalies_manifest_provenance(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        response = client.get("/api/v1/predictions/sensor-anomalies?limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Verify that threshold matches manifest exactly
        manifest_thresh = load_frozen_sensor_threshold()
        assert data["frozen_threshold"] == manifest_thresh

    # 16. SSE Endpoint: Query Parameter Auth Support and Synthetic Demo Tagging
    def test_sse_query_param_auth_and_synthetic_label(self, client):
        # Request stream with max_events=2 via query param api_key
        response = client.get(f"/api/v1/stream/events?api_key={TEST_ADMIN_KEY}&max_events=2")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "event: heartbeat" in body or "event: telemetry_pulse" in body
        assert "data:" in body
        # Verify that synthetic demo source label is present when fallback is engaged
        if "telemetry_pulse" in body:
            assert '"source": "synthetic_demo"' in body or '"source": "kafka"' in body

    # 17. Read-Only Method Guard: POST/PUT/PATCH/DELETE -> 405 Method Not Allowed
    def test_post_method_not_allowed(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        # Attempt POST to an endpoint
        resp_post = client.post("/api/v1/vehicles", headers=headers, json={"test": "data"})
        assert resp_post.status_code == 405
        assert "Method POST not allowed" in resp_post.json()["detail"]

        resp_delete = client.delete("/api/v1/vehicles/VH001", headers=headers)
        assert resp_delete.status_code == 405

    # 18. Model Governance Status: Ratified Metrics & Threshold Provenance
    def test_models_status_governance(self, client):
        headers = {"X-API-Key": TEST_ADMIN_KEY}
        response = client.get("/api/v1/models/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Area 1: Ratified
        assert data["area_1_failure_risk"]["status"] == "RATIFIED"
        assert data["area_1_failure_risk"]["metrics"]["roc_auc"] == 0.8452
        # Area 2: Frozen Approved
        assert data["area_2_sensor_anomaly"]["status"] == "FROZEN_APPROVED"
        assert data["area_2_sensor_anomaly"]["threshold_value"] == load_frozen_sensor_threshold()
        assert data["area_2_sensor_anomaly"]["metrics"]["nominal_fpr"] == 0.0157
        # Area 3: Accepted
        assert data["area_3_service_demand"]["status"] == "ACCEPTED"
        assert data["area_3_service_demand"]["metrics"]["mae"] == 0.4281
        # Area 4: Accepted (No Fraud Allegations)
        assert data["area_4_warranty_anomaly"]["status"] == "ACCEPTED"
        assert "Zero claims of fraud" in data["area_4_warranty_anomaly"]["metrics"]["fraud_allegation_disclaimer"]
