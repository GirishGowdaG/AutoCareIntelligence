export type RiskTier = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface FailureRiskPrediction {
  prediction_id?: string;
  vehicle_id: string;
  cutoff_date: string;
  risk_score: number;
  risk_tier: RiskTier;
  top_features?: Record<string, any> | null;
  model_version: string;
  created_at?: string | null;
}

export interface SensorAnomalyRecord {
  anomaly_id: string;
  vehicle_id: string;
  window_timestamp: string;
  anomaly_score: number;
  is_anomaly: boolean;
  anomalous_features?: Record<string, unknown> | null;
  model_version: string;
  detected_at?: string | null;
}

export interface SensorAnomaliesResponse {
  items: SensorAnomalyRecord[];
  total: number;
  frozen_threshold: number;
  limit: number;
  offset: number;
}

export interface ServiceDemandForecast {
  forecast_id: string;
  dealer_id: string;
  forecast_date: string;
  predicted_volume: number;
  lower_bound_80: number;
  upper_bound_80: number;
  model_version: string;
  generated_at?: string;
  is_surge?: boolean;
}

export interface WarrantyAnomalyRecord {
  anomaly_id: string;
  claim_id: string;
  dealer_id?: string | null;
  component_id?: string | null;
  claim_amount: number;
  anomaly_score: number;
  outlier_reasons?: Record<string, any> | null;
  model_version: string;
  flagged_at?: string | null;
}

export interface ModelGovernanceItem {
  area_name: string;
  model_name: string;
  version: string;
  status: string;
  status_display: string;
  governance_status: string;
  governance_display: string;
  threshold_type: string;
  threshold_value: number | string;
  threshold_label: string;
  primary_metric_name: string;
  primary_metric_value: number | string;
  primary_metric_display: string;
  manifest_path: string;
  manifest_provenance: string;
  is_frozen: boolean;
}

export interface ModelGovernanceResponse {
  area_1_failure_risk: ModelGovernanceItem;
  area_2_sensor_anomaly: ModelGovernanceItem;
  area_3_service_demand: ModelGovernanceItem;
  area_4_warranty_anomaly: ModelGovernanceItem;
  timestamp: string;
}
