import {
  HealthResponse,
  OverviewMetricsResponse,
  PaginatedResponse,
} from "@/types/api";
import { VehicleDetail, VehicleSummary } from "@/types/vehicles";
import {
  FailureRiskPrediction,
  ModelGovernanceResponse,
  SensorAnomaliesResponse,
  ServiceDemandForecast,
  WarrantyAnomalyRecord,
} from "@/types/ml";
import { ActionAuditRecord } from "@/types/audit";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiClientError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  apiKey?: string | null,
  params?: Record<string, string | number | boolean | undefined | null>
): Promise<T> {
  const url = new URL(path, BASE_URL);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const headers: HeadersInit = {
    Accept: "application/json",
  };

  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        detail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new ApiClientError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  getHealth: () => request<HealthResponse>("/api/v1/health"),

  getOverviewMetrics: (apiKey?: string | null) =>
    request<OverviewMetricsResponse>("/api/v1/metrics/overview", apiKey),

  getVehicles: (
    apiKey?: string | null,
    params?: { limit?: number; offset?: number; make?: string; state?: string }
  ) => request<PaginatedResponse<VehicleSummary>>("/api/v1/vehicles", apiKey, params),

  getVehicleDetail: (id: string, apiKey?: string | null) =>
    request<VehicleDetail>(`/api/v1/vehicles/${encodeURIComponent(id)}`, apiKey),

  getFailureRisk: (
    apiKey?: string | null,
    params?: { limit?: number; offset?: number; risk_tier?: string }
  ) => request<PaginatedResponse<FailureRiskPrediction>>("/api/v1/predictions/failure-risk", apiKey, params),

  getSensorAnomalies: (
    apiKey?: string | null,
    params?: { limit?: number; offset?: number; is_anomaly?: boolean; vehicle_id?: string }
  ) => request<SensorAnomaliesResponse>("/api/v1/predictions/sensor-anomalies", apiKey, params),

  getServiceDemandForecast: (
    apiKey?: string | null,
    params?: { limit?: number; offset?: number; dealer_id?: string; is_surge?: boolean }
  ) => request<PaginatedResponse<ServiceDemandForecast>>("/api/v1/forecast/service-demand", apiKey, params),

  getWarrantyAnomalies: (
    apiKey?: string | null,
    params?: { limit?: number; offset?: number; dealer_id?: string }
  ) => request<PaginatedResponse<WarrantyAnomalyRecord>>("/api/v1/anomalies/warranty", apiKey, params),

  getActionAuditLogs: (
    apiKey?: string | null,
    params?: { limit?: number; offset?: number; entity_type?: string; delivery_status?: string }
  ) => request<PaginatedResponse<ActionAuditRecord>>("/api/v1/audit/actions", apiKey, params),

  getModelGovernanceStatus: (apiKey?: string | null) =>
    request<ModelGovernanceResponse>("/api/v1/models/status", apiKey),
};
