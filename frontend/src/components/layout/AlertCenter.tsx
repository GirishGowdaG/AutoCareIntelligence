"use client";

import React from "react";
import {
  X,
  Radio,
  Activity,
  Zap,
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
            {source === "kafka"
              ? "[LIVE: Kafka Telemetry]"
              : source === "action_logs"
              ? "[LIVE: Action Logs]"
              : source === "server"
              ? "[SERVER: Heartbeat Active]"
              : "[DEMO MODE: Synthetic Telemetry]"}
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
            <p className="text-xs">Listening for real-time telemetry pulses and audit action events...</p>
          </div>
        ) : (
          events.map((evt, idx) => {
            // 1. telemetry_pulse event card
            if (evt.type === "telemetry_pulse") {
              const pulse = evt.data;
              const tel = pulse.data;
              const vehicleId = tel.vehicle_id || "VH001";
              return (
                <div
                  key={`tel-${idx}-${pulse.timestamp}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 transition hover:border-slate-700"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                      <Activity className="h-4 w-4 text-blue-400" />
                      <span>Telemetry Pulse</span>
                    </div>
                    <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-300 border border-slate-700">
                      {pulse.source === "kafka" ? "KAFKA" : "SYNTHETIC DEMO"}
                    </span>
                  </div>

                  <div className="mt-2 text-xs text-slate-400">
                    Vehicle: <span className="font-mono text-slate-200">{vehicleId}</span>
                  </div>

                  <div className="mt-2 grid grid-cols-4 gap-2 rounded-lg bg-slate-950 p-2 text-center text-[11px]">
                    <div>
                      <div className="text-slate-500 text-[10px]">RPM</div>
                      <div className="font-mono font-medium text-slate-300">{tel.rpm}</div>
                    </div>
                    <div>
                      <div className="text-slate-500 text-[10px]">Temp</div>
                      <div className="font-mono font-medium text-slate-300">{tel.temperature}°C</div>
                    </div>
                    <div>
                      <div className="text-slate-500 text-[10px]">Battery</div>
                      <div className="font-mono font-medium text-slate-300">{tel.battery}V</div>
                    </div>
                    <div>
                      <div className="text-slate-500 text-[10px]">Vibration</div>
                      <div className="font-mono font-medium text-slate-300">{tel.vibration}</div>
                    </div>
                  </div>

                  <div className="mt-2 flex items-center justify-between pt-1 text-[11px] text-slate-500 border-t border-slate-850">
                    <span>{formatDate(pulse.timestamp)}</span>
                    <Link
                      href={`/sensor-anomalies?vehicle_id=${encodeURIComponent(vehicleId)}`}
                      onClick={onClose}
                      className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                    >
                      Monitor <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              );
            }

            // 2. audit_action event card
            if (evt.type === "audit_action") {
              const audit = evt.data;
              const action = audit.action;
              return (
                <div
                  key={`act-${idx}-${audit.timestamp}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-3.5 transition hover:border-slate-700"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                      <Zap className="h-4 w-4 text-amber-400" />
                      <span>{action.rule_id}</span>
                    </div>
                    {action.delivery_status && (
                      <StatusBadge status={action.delivery_status} size="sm" />
                    )}
                  </div>

                  <div className="mt-2 text-xs text-slate-400">
                    Target: <span className="font-mono text-slate-200">{action.entity_type} {action.entity_id}</span>
                  </div>

                  {action.action_taken && (
                    <div className="mt-1 text-xs text-slate-300 font-sans">
                      {action.action_taken}
                    </div>
                  )}

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
