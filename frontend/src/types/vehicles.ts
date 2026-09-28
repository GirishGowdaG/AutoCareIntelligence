export interface VehicleSummary {
  vehicle_id: string;
  variant: string;
  manufacture_year: number;
  manufacture_date: string;
  status: string;
  model_name?: string | null;
  vehicle_class?: string | null;
  selling_dealer_name?: string | null;
}

export interface DiagnosticRecordItem {
  diagnostic_id: string;
  vehicle_id: string;
  timestamp: string;
  dtc_code: string;
  component?: string | null;
  severity: string;
}

export interface VehicleDiagnosticsResponse {
  vehicle_id: string;
  total_records: number;
  diagnostics: DiagnosticRecordItem[];
}

export interface VehicleDetail {
  vehicle_id: string;
  variant: string;
  manufacture_year: number;
  manufacture_date: string;
  status: string;
  model_name?: string | null;
  vehicle_class?: string | null;
  powertrain_type?: string | null;
  curb_weight_kg?: number | null;
  selling_dealer_id?: string | null;
  selling_dealer_name?: string | null;
  diagnostics?: DiagnosticRecordItem[];
}
