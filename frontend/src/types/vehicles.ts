export interface VehicleSummary {
  vehicle_id: string;
  make: string;
  model_name: string;
  model_year: number;
  body_class: string;
  engine_type: string;
  state: string;
}

export interface VehicleDiagnosticRecord {
  snapshot_id: string;
  timestamp: string;
  dtc_code: string | null;
  dtc_description: string | null;
  severity: string | null;
  mil_status: boolean;
}

export interface VehicleDetail extends VehicleSummary {
  diagnostics: VehicleDiagnosticRecord[];
}
