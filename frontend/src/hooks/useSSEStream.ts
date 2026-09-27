"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthRole } from "./useAuthRole";
import {
  AuditActionEvent,
  HeartbeatEvent,
  SSEEventPayload,
  TelemetryPulseEvent,
} from "@/types/audit";

export type ConnectionStatus = "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "ERROR";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useSSEStream() {
  const { apiKey } = useAuthRole();
  const [status, setStatus] = useState<ConnectionStatus>("DISCONNECTED");
  const [source, setSource] = useState<"kafka" | "synthetic_demo" | "action_logs" | "server" | null>(null);
  const [events, setEvents] = useState<SSEEventPayload[]>([]);
  const [latestTelemetry, setLatestTelemetry] = useState<TelemetryPulseEvent | null>(null);
  const [latestAction, setLatestAction] = useState<AuditActionEvent | null>(null);
  const [lastHeartbeat, setLastHeartbeat] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastEventIdRef = useRef<string | null>(null);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  useEffect(() => {
    if (!apiKey) {
      setStatus("DISCONNECTED");
      return;
    }

    let isMounted = true;

    const connect = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      setStatus("CONNECTING");

      let streamUrl = `${BASE_URL}/api/v1/stream/events?api_key=${encodeURIComponent(apiKey)}`;
      if (lastEventIdRef.current) {
        streamUrl += `&last_event_id=${encodeURIComponent(lastEventIdRef.current)}`;
      }

      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        if (!isMounted) return;
        setStatus("CONNECTED");
      };

      // 1. telemetry_pulse event listener
      es.addEventListener("telemetry_pulse", (e: MessageEvent) => {
        if (!isMounted) return;
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId;
        }
        try {
          const payload = JSON.parse(e.data) as TelemetryPulseEvent;
          if (payload.source) {
            setSource(payload.source as "kafka" | "synthetic_demo");
          }
          setLatestTelemetry(payload);
          setEvents((prev) => [{ type: "telemetry_pulse", data: payload }, ...prev.slice(0, 49)]);
        } catch (err) {
          console.error("Failed to parse telemetry_pulse event", err);
        }
      });

      // 2. audit_action event listener
      es.addEventListener("audit_action", (e: MessageEvent) => {
        if (!isMounted) return;
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId;
        }
        try {
          const payload = JSON.parse(e.data) as AuditActionEvent;
          if (payload.source) {
            setSource(payload.source as "action_logs");
          }
          setLatestAction(payload);
          setEvents((prev) => [{ type: "audit_action", data: payload }, ...prev.slice(0, 49)]);
        } catch (err) {
          console.error("Failed to parse audit_action event", err);
        }
      });

      // 3. heartbeat event listener
      es.addEventListener("heartbeat", (e: MessageEvent) => {
        if (!isMounted) return;
        if (e.lastEventId) {
          lastEventIdRef.current = e.lastEventId;
        }
        try {
          const payload = JSON.parse(e.data) as HeartbeatEvent;
          if (payload.source) {
            setSource(payload.source as "server");
          }
          setLastHeartbeat(payload.timestamp || new Date().toISOString());
        } catch {
          setLastHeartbeat(new Date().toISOString());
        }
      });

      es.onerror = () => {
        if (!isMounted) return;
        setStatus("ERROR");
        es.close();
        if (!reconnectTimerRef.current) {
          reconnectTimerRef.current = setTimeout(() => {
            reconnectTimerRef.current = null;
            if (isMounted) {
              connect();
            }
          }, 5000);
        }
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setStatus("DISCONNECTED");
    };
  }, [apiKey]);

  return {
    isConnected: status === "CONNECTED",
    status,
    source,
    events,
    latestTelemetry,
    latestAction,
    lastHeartbeat,
    clearEvents,
  };
}
