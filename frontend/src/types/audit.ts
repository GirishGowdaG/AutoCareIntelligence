export type EntityType = "VEHICLE" | "DEALER" | "CLAIM";
export type DeliveryStatus = "DELIVERED" | "MOCK_LOGGED" | "FAILED";

export interface ActionAuditRecord {
  action_id: string;
  rule_id: string;
  entity_type: EntityType;
  entity_id: string;
  trigger_timestamp: string;
  trigger_value: number;
  threshold_applied: number;
  action_taken: string;
  channel_dispatched: string;
  delivery_status: DeliveryStatus;
  idempotency_key: string;
  payload?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface TelemetryData {
  vehicle_id?: string;
  rpm: number;
  temperature: number;
  battery: number;
  vibration: number;
}

export interface TelemetryPulseEvent {
  event_type: "telemetry_pulse";
  source: "kafka" | "synthetic_demo" | string;
  timestamp: string;
  data: TelemetryData;
}

export interface AuditActionItem {
  action_id: string;
  rule_id: string;
  entity_type: EntityType;
  entity_id: string;
  trigger_timestamp?: string;
  trigger_value?: number;
  threshold_applied?: number;
  action_taken?: string;
  channel_dispatched?: string;
  delivery_status?: DeliveryStatus;
  idempotency_key?: string;
  created_at: string;
}

export interface AuditActionEvent {
  event_type: "audit_action";
  source: "action_logs" | string;
  timestamp: string;
  action: AuditActionItem;
}

export interface HeartbeatEvent {
  event_type: "heartbeat";
  source: "server" | string;
  timestamp: string;
  message_seq?: number;
}

export type SSEEventPayload =
  | { type: "telemetry_pulse"; data: TelemetryPulseEvent }
  | { type: "audit_action"; data: AuditActionEvent }
  | { type: "heartbeat"; data: HeartbeatEvent };
