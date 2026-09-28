export type UserRole = "Admin" | "DealerServiceManager" | "FleetAnalyst";

export interface HealthResponse {
  status: "healthy" | "degraded";
  timestamp: string;
  version: string;
  components: {
    database: string;
    models: string;
  };
}

export interface OverviewMetricsResponse {
  total_vehicles: number;
  critical_risk_vehicles: number;
  sensor_anomalies_detected: number;
  warranty_outliers_flagged: number;
  actions_logged_total: number;
  last_action_timestamp?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiError {
  detail: string;
  status?: number;
}
