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
  active_sensor_anomalies: number;
  surge_demand_regions: number;
  flagged_warranty_claims: number;
  recent_actions_count: number;
  timestamp: string;
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
