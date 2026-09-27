"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthRole } from "./useAuthRole";
import {
  LiveActionEvent,
  LiveSensorEvent,
  SSEEventPayload,
} from "@/types/audit";

export type ConnectionStatus = "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "ERROR";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useSSEStream() {
  const { apiKey } = useAuthRole();
  const [status, setStatus] = useState<ConnectionStatus>("DISCONNECTED");
  const [source, setSource] = useState<"kafka" | "synthetic_demo" | null>(null);
  const [events, setEvents] = useState<SSEEventPayload[]>([]);
  const [latestSensorEvent, setLatestSensorEvent] = useState<LiveSensorEvent | null>(null);
  const [latestActionEvent, setLatestActionEvent] = useState<LiveActionEvent | null>(null);
  const [lastHeartbeat, setLastHeartbeat] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

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

      const streamUrl = `${BASE_URL}/api/v1/stream/events?api_key=${encodeURIComponent(apiKey)}`;
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        if (!isMounted) return;
        setStatus("CONNECTED");
      };

      es.addEventListener("sensor_reading", (e: MessageEvent) => {
        if (!isMounted) return;
        try {
          const payload = JSON.parse(e.data) as LiveSensorEvent;
          if (payload.source === "kafka" || payload.source === "synthetic_demo") {
            setSource(payload.source);
          }
          setLatestSensorEvent(payload);
          setEvents((prev) => [{ type: "sensor_reading", data: payload }, ...prev.slice(0, 49)]);
        } catch (err) {
          console.error("Failed to parse sensor_reading event", err);
        }
      });

      es.addEventListener("action_event", (e: MessageEvent) => {
        if (!isMounted) return;
        try {
          const payload = JSON.parse(e.data) as LiveActionEvent;
          if (payload.source === "kafka" || payload.source === "synthetic_demo") {
            setSource(payload.source);
          }
          setLatestActionEvent(payload);
          setEvents((prev) => [{ type: "action_event", data: payload }, ...prev.slice(0, 49)]);
        } catch (err) {
          console.error("Failed to parse action_event event", err);
        }
      });

      es.addEventListener("heartbeat", (e: MessageEvent) => {
        if (!isMounted) return;
        try {
          const payload = JSON.parse(e.data);
          setLastHeartbeat(payload.timestamp || new Date().toISOString());
        } catch {
          setLastHeartbeat(new Date().toISOString());
        }
      });

      es.onerror = () => {
        if (!isMounted) return;
        setStatus("ERROR");
        es.close();
        // Exponential backoff reconnect
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
    latestSensorEvent,
    latestActionEvent,
    lastHeartbeat,
    clearEvents,
  };
}
