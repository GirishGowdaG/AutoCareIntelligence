import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient, ApiClientError } from "../src/lib/api-client";

describe("apiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("getHealth calls /api/v1/health without requiring API key", async () => {
    const mockHealth = {
      status: "healthy",
      timestamp: "2026-09-27T12:00:00Z",
      version: "1.0.0",
      components: { database: "connected", models: "loaded" },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    } as Response);

    const res = await apiClient.getHealth();
    expect(res.status).toBe("healthy");
    expect(res.components.database).toBe("connected");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/health"),
      expect.objectContaining({ method: "GET" })
    );
  });

  it("attaches X-API-Key header when key is provided", async () => {
    const mockOverview = {
      total_vehicles: 50,
      critical_risk_vehicles: 6,
      active_sensor_anomalies: 2,
      surge_demand_regions: 1,
      flagged_warranty_claims: 3,
      recent_actions_count: 10,
      timestamp: "2026-09-27T12:00:00Z",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockOverview,
    } as Response);

    const res = await apiClient.getOverviewMetrics("test-admin-key");
    expect(res.total_vehicles).toBe(50);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/metrics/overview"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-API-Key": "test-admin-key" }),
      })
    );
  });

  it("throws ApiClientError with status 401 when unauthenticated", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Invalid or missing API Key" }),
    } as Response);

    await expect(apiClient.getVehicles()).rejects.toThrow(ApiClientError);
    await expect(apiClient.getVehicles()).rejects.toMatchObject({
      status: 401,
      detail: "Invalid or missing API Key",
    });
  });

  it("throws ApiClientError with status 403 when forbidden", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      json: async () => ({ detail: "Role DealerServiceManager cannot access warranty anomalies" }),
    } as Response);

    await expect(apiClient.getWarrantyAnomalies("dealer-key")).rejects.toMatchObject({
      status: 403,
      detail: "Role DealerServiceManager cannot access warranty anomalies",
    });
  });

  it("parses root-level model governance response correctly", async () => {
    const mockGov = {
      area_1_failure_risk: {
        area_name: "Area 1: Failure Risk",
        model_name: "GradientBoostingClassifier",
        version: "1.0.0",
        threshold_value: 0.7,
        is_frozen: false,
        primary_metric_name: "ROC-AUC",
        primary_metric_value: 0.8452,
      },
      area_2_sensor_anomaly: {
        area_name: "Area 2: Sensor Anomaly",
        model_name: "IsolationForestAutoencoderEnsemble",
        version: "1.0.0",
        threshold_value: 0.838357,
        is_frozen: true,
        primary_metric_name: "F1-Score",
        primary_metric_value: 0.9761,
      },
      area_3_service_demand: {
        area_name: "Area 3: Service Demand",
        model_name: "LightGBMForecaster",
        version: "1.0.0",
        threshold_value: 0.25,
        is_frozen: false,
        primary_metric_name: "MAPE",
        primary_metric_value: 0.0812,
      },
      area_4_warranty_anomaly: {
        area_name: "Area 4: Warranty Anomaly",
        model_name: "IsolationForestOutlierDetector",
        version: "1.0.0",
        threshold_value: 0.8,
        is_frozen: false,
        primary_metric_name: "Precision@Top-K",
        primary_metric_value: 0.4281,
      },
      timestamp: "2026-09-27T12:00:00Z",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockGov,
    } as Response);

    const res = await apiClient.getModelGovernanceStatus("admin-key");
    expect(res.area_2_sensor_anomaly.is_frozen).toBe(true);
    expect(res.area_2_sensor_anomaly.threshold_value).toBe(0.838357);
    expect(res.area_1_failure_risk.threshold_value).toBe(0.7);
  });
});
