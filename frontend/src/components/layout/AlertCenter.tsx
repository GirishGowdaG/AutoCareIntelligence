"use client";

import React from "react";
import {
  X,
  Radio,
  Activity,
  Zap,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { SSEEventPayload } from "@/types/audit";
import { formatDate } from "@/lib/utils";
import { StatusBadge } from "../common/StatusBadge";

interface AlertCenterProps {
  isOpen: boolean;
  onClose: () => void;
  events: SSEEventPayload[];
  onClear: () => void;
  status: string;
  source: string | null;
  lastHeartbeat: string | null;
}

export function AlertCenter({
  isOpen,
  onClose,
  events,
  onClear,
  status,
  source,
  lastHeartbeat,
}: AlertCenterProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-slate-800 bg-slate-950 p-6 shadow-2xl backdrop-blur-xl animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          <Radio className="h-5 w-5 text-blue-400 animate-pulse" />
          <h2 className="text-base font-bold text-white">Alert Center</h2>
        </div>
        <div className="flex items-center gap-2">
          {events.length > 0 && (
            <button
              onClick={onClear}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              title="Clear alerts"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Stream Provenance & Heartbeat Bar */}
      <div className="mt-3 flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${
              status === "CONNECTED"
                ? "bg-emerald-400"
                : status === "CONNECTING"
                ? "bg-amber-400 animate-pulse"
                : "bg-rose-400"
            }`}
          />
          <span className="font-semibold text-slate-200 capitalize">
            {source === "kafka" ? "[LIVE: Kafka Telemetry]" : "[DEMO MODE: Synthetic Telemetry]"}
          </span>
        </div>
        <span className="text-[11px] text-slate-500">
          Heartbeat: {lastHeartbeat ? formatDate(lastHeartbeat) : "Pending"}
        </span>
      </div>

      {/* Event Stream List */}
      <div className="mt-4 flex-1 overflow-y-auto space-y-3 pr-1">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center text-slate-500">
            <Radio className="h-8 w-8 text-slate-600 mb-2" />
            <p className="text-xs">Listening for real-time telemetry and automation events...</p>
          </div>
        ) : (
          events.map((evt, idx) => {
            if (evt.type === "sensor_reading") {
              const item = evt.data;
              return (
                <div
                  key={`sensor-${idx}-${item.timestamp}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 transition hover:border-slate-700"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                      <Activity className="h-4 w-4 text-blue-400" />
                      <span>CAN-Bus Reading</span>
                    </div>
                    {item.is_anomaly ? (
                      <StatusBadge status="ANOMALY" size="sm" />
                    ) : (
                      <StatusBadge status="NORMAL" size="sm" />
                    )}
                  </div>

                  <div className="mt-2 text-xs text-slate-400">
                    Vehicle: <span className="font-mono text-slate-200">{item.vehicle_id}</span>
                  </div>

                  <div className="mt-2 grid grid-cols-3 gap-2 rounded-lg bg-slate-950 p-2 text-center text-[11px]">
                    <div>
                      <div className="text-slate-500">RPM</div>
                      <div className="font-mono font-medium text-slate-300">{item.rpm}</div>
                    </div>
                    <div>
                      <div className="text-slate-500">Speed</div>
                      <div className="font-mono font-medium text-slate-300">{item.speed_kmh} km/h</div>
                    </div>
                    <div>
                      <div className="text-slate-500">Coolant</div>
                      <div className="font-mono font-medium text-slate-300">{item.coolant_temp_c}°C</div>
                    </div>
                  </div>

                  <div className="mt-2 flex items-center justify-between pt-1 text-[11px] text-slate-500 border-t border-slate-850">
                    <span>Score: {item.anomaly_score.toFixed(4)}</span>
                    <Link
                      href={`/sensor-anomalies?vehicle_id=${encodeURIComponent(item.vehicle_id)}`}
                      onClick={onClose}
                      className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                    >
                      Inspect <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              );
            }

            if (evt.type === "action_event") {
              const action = evt.data;
              return (
                <div
                  key={`action-${idx}-${action.executed_at}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 transition hover:border-slate-700"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                      <Zap className="h-4 w-4 text-amber-400" />
                      <span>{action.rule_id}</span>
                    </div>
                    <StatusBadge status={action.delivery_status} size="sm" />
                  </div>

                  <div className="mt-2 text-xs text-slate-400">
                    Target: <span className="font-mono text-slate-200">{action.entity_type} {action.entity_id}</span>
                  </div>

                  <div className="mt-1 text-xs text-slate-400">
                    Type: <span className="text-slate-300">{action.action_type}</span> ({action.priority})
                  </div>

                  {action.entity_type === "CLAIM" && (
                    <div className="mt-2 flex items-center justify-between pt-1 text-[11px] border-t border-slate-850">
                      <span className="text-slate-400">Claim ID: {action.entity_id}</span>
                      <Link
                        href={`/warranty-audit?claim_id=${encodeURIComponent(action.entity_id)}`}
                        onClick={onClose}
                        className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                      >
                        Inspect Claim <ArrowRight className="h-3 w-3" />
                      </Link>
                    </div>
                  )}
                </div>
              );
            }

            return null;
          })
        )}
      </div>
    </div>
  );
}
