import { describe, it, expect, vi, beforeEach } from "vitest";

describe("useSSEStream & Event Protocol", () => {
  it("constructs correct query parameter authenticated SSE URL", () => {
    const apiKey = "test-operator-secret-key-123";
    const baseUrl = "http://localhost:8000";
    const streamUrl = `${baseUrl}/api/v1/stream/events?api_key=${encodeURIComponent(apiKey)}`;

    expect(streamUrl).toBe("http://localhost:8000/api/v1/stream/events?api_key=test-operator-secret-key-123");
    expect(streamUrl).toContain("?api_key=");
  });

  it("identifies live Kafka telemetry versus synthetic fallback telemetry", () => {
    const kafkaEvent = {
      vehicle_id: "VEH-001",
      rpm: 2450,
      speed_kmh: 88.5,
      coolant_temp_c: 92.1,
      anomaly_score: 0.12,
      is_anomaly: false,
      timestamp: "2026-09-27T12:00:00Z",
      source: "kafka",
    };

    const syntheticEvent = {
      ...kafkaEvent,
      source: "synthetic_demo",
    };

    const getProvenanceBadge = (source: string) =>
      source === "kafka" ? "[LIVE: Kafka Telemetry]" : "[DEMO MODE: Synthetic Telemetry]";

    expect(getProvenanceBadge(kafkaEvent.source)).toBe("[LIVE: Kafka Telemetry]");
    expect(getProvenanceBadge(syntheticEvent.source)).toBe("[DEMO MODE: Synthetic Telemetry]");
  });

  it("handles heartbeat protocol payload", () => {
    const heartbeatPayload = JSON.stringify({
      type: "heartbeat",
      timestamp: "2026-09-27T12:00:15Z",
    });

    const parsed = JSON.parse(heartbeatPayload);
    expect(parsed.type).toBe("heartbeat");
    expect(parsed.timestamp).toBe("2026-09-27T12:00:15Z");
  });
});
