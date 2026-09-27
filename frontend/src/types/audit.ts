export type EntityType = "VEHICLE" | "DEALER" | "CLAIM";
export type DeliveryStatus = "DELIVERED" | "MOCK_LOGGED" | "FAILED";

export interface ActionAuditRecord {
  action_id: string;
  rule_id: string;
  action_type: string;
  entity_type: EntityType;
  entity_id: string;
  priority: string;
  payload: Record<string, unknown>;
  delivery_status: DeliveryStatus;
  executed_at: string;
}

export interface LiveSensorEvent {
  vehicle_id: string;
  rpm: number;
  speed_kmh: number;
  coolant_temp_c: number;
  anomaly_score: number;
  is_anomaly: boolean;
  timestamp: string;
  source: "kafka" | "synthetic_demo" | string;
}

export interface LiveActionEvent {
  action_id: string;
  rule_id: string;
  action_type: string;
  entity_type: EntityType;
  entity_id: string;
  priority: string;
  delivery_status: DeliveryStatus;
  executed_at: string;
  source: "kafka" | "synthetic_demo" | string;
}

export interface HeartbeatEvent {
  type: "heartbeat";
  timestamp: string;
}

export type SSEEventPayload =
  | { type: "sensor_reading"; data: LiveSensorEvent }
  | { type: "action_event"; data: LiveActionEvent }
  | { type: "heartbeat"; data: HeartbeatEvent };
