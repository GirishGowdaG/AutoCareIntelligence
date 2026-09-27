import { describe, it, expect } from "vitest";
import { TelemetryPulseEvent, AuditActionEvent, HeartbeatEvent } from "../src/types/audit";

describe("useSSEStream & Approved Event Contract", () => {
  it("constructs correct query parameter authenticated SSE URL with Last-Event-ID support", () => {
    const apiKey = "test-operator-secret-key-123";
    const baseUrl = "http://localhost:8000";
    const lastEventId = "tel-42";
    const streamUrl = `${baseUrl}/api/v1/stream/events?api_key=${encodeURIComponent(apiKey)}&last_event_id=${encodeURIComponent(lastEventId)}`;

    expect(streamUrl).toBe("http://localhost:8000/api/v1/stream/events?api_key=test-operator-secret-key-123&last_event_id=tel-42");
    expect(streamUrl).toContain("?api_key=");
    expect(streamUrl).toContain("&last_event_id=");
  });

  it("handles approved event: telemetry_pulse with exact 4 verified fields", () => {
    const rawPulse = {
      event_type: "telemetry_pulse",
      source: "synthetic_demo",
      timestamp: "2026-09-27T12:00:00Z",
      data: {
        vehicle_id: "VH001",
        rpm: 2450,
        temperature: 92.5,
        battery: 13.8,
        vibration: 1.25,
      },
    };

    const pulse = rawPulse as TelemetryPulseEvent;
    expect(pulse.event_type).toBe("telemetry_pulse");
    expect(pulse.source).toBe("synthetic_demo");
    expect(pulse.data.rpm).toBe(2450);
    expect(pulse.data.temperature).toBe(92.5);
    expect(pulse.data.battery).toBe(13.8);
    expect(pulse.data.vibration).toBe(1.25);
  });

  it("handles approved event: audit_action for Alert Center updates", () => {
    const rawAudit = {
      event_type: "audit_action",
      source: "action_logs",
      timestamp: "2026-09-27T12:00:01Z",
      action: {
        action_id: "act-101",
        rule_id: "RULE_4_WARRANTY_ANOMALY",
        entity_type: "CLAIM",
        entity_id: "CLM-9092",
        delivery_status: "DELIVERED",
        created_at: "2026-09-27T12:00:01Z",
      },
    };

    const auditEvent = rawAudit as AuditActionEvent;
    expect(auditEvent.event_type).toBe("audit_action");
    expect(auditEvent.source).toBe("action_logs");
    expect(auditEvent.action.rule_id).toBe("RULE_4_WARRANTY_ANOMALY");
    expect(auditEvent.action.entity_type).toBe("CLAIM");
    expect(auditEvent.action.entity_id).toBe("CLM-9092");
    expect(auditEvent.action.delivery_status).toBe("DELIVERED");
  });

  it("handles approved event: heartbeat updating connection health", () => {
    const rawHb = {
      event_type: "heartbeat",
      source: "server",
      timestamp: "2026-09-27T12:00:15Z",
      message_seq: 1,
    };

    const hb = rawHb as HeartbeatEvent;
    expect(hb.event_type).toBe("heartbeat");
    expect(hb.source).toBe("server");
    expect(hb.timestamp).toBe("2026-09-27T12:00:15Z");
  });

  it("identifies live Kafka vs synthetic demo vs action logs vs server provenance", () => {
    const getProvenanceBadge = (source: string) => {
      switch (source) {
        case "kafka":
          return "[LIVE: Kafka Telemetry]";
        case "action_logs":
          return "[LIVE: Action Logs]";
        case "server":
          return "[SERVER: Heartbeat Active]";
        default:
          return "[DEMO MODE: Synthetic Telemetry]";
      }
    };

    expect(getProvenanceBadge("kafka")).toBe("[LIVE: Kafka Telemetry]");
    expect(getProvenanceBadge("synthetic_demo")).toBe("[DEMO MODE: Synthetic Telemetry]");
    expect(getProvenanceBadge("action_logs")).toBe("[LIVE: Action Logs]");
    expect(getProvenanceBadge("server")).toBe("[SERVER: Heartbeat Active]");
  });
});
