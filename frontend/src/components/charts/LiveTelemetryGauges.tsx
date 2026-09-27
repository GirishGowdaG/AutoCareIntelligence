"use client";

import React from "react";
import { Gauge, Zap, Thermometer, AlertCircle } from "lucide-react";
import { LiveSensorEvent } from "@/types/audit";
import { SensorAnomalyRecord } from "@/types/ml";

interface LiveTelemetryGaugesProps {
  reading: LiveSensorEvent | SensorAnomalyRecord | null;
  frozenThreshold?: number | null;
}

export function LiveTelemetryGauges({ reading, frozenThreshold }: LiveTelemetryGaugesProps) {
  if (!reading) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/40 text-xs text-slate-500">
        Waiting for CAN-bus telemetry data stream...
      </div>
    );
  }

  const rpm = reading.rpm ?? 0;
  const speed = reading.speed_kmh ?? 0;
  const coolant = reading.coolant_temp_c ?? 0;
  const score = reading.anomaly_score ?? 0;
  const isAnomaly = reading.is_anomaly ?? (frozenThreshold ? score > frozenThreshold : false);

  // Normalization percentages
  const rpmPct = Math.min(Math.max((rpm / 6000) * 100, 0), 100);
  const speedPct = Math.min(Math.max((speed / 160) * 100, 0), 100);
  const coolantPct = Math.min(Math.max(((coolant - 40) / 90) * 100, 0), 100);
  const scorePct = Math.min(Math.max((score / 1.0) * 100, 0), 100);

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {/* RPM Gauge */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">Engine Speed</span>
          <Gauge className="h-4 w-4 text-blue-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-2xl font-bold font-mono text-white">{rpm}</span>
          <span className="text-xs text-slate-400">RPM</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full transition-all duration-300 ${
              rpm > 4500 ? "bg-rose-500" : rpm > 3200 ? "bg-amber-500" : "bg-blue-500"
            }`}
            style={{ width: `${rpmPct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 font-mono">
          <span>0</span>
          <span>3000</span>
          <span>6000</span>
        </div>
      </div>

      {/* Vehicle Speed Gauge */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">Vehicle Speed</span>
          <Zap className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-2xl font-bold font-mono text-white">{speed.toFixed(1)}</span>
          <span className="text-xs text-slate-400">km/h</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full bg-emerald-500 transition-all duration-300"
            style={{ width: `${speedPct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 font-mono">
          <span>0</span>
          <span>80</span>
          <span>160</span>
        </div>
      </div>

      {/* Coolant Temp Gauge */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">Coolant Temp</span>
          <Thermometer className="h-4 w-4 text-amber-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-2xl font-bold font-mono text-white">{coolant.toFixed(1)}</span>
          <span className="text-xs text-slate-400">°C</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full transition-all duration-300 ${
              coolant > 105 ? "bg-rose-500" : coolant > 95 ? "bg-amber-500" : "bg-teal-500"
            }`}
            style={{ width: `${coolantPct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 font-mono">
          <span>40°C</span>
          <span>90°C</span>
          <span>130°C</span>
        </div>
      </div>

      {/* Anomaly Score Gauge */}
      <div
        className={`rounded-xl border p-4 transition ${
          isAnomaly
            ? "border-rose-800 bg-rose-950/30"
            : "border-slate-800 bg-slate-900/60"
        }`}
      >
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">Anomaly Score</span>
          <AlertCircle
            className={`h-4 w-4 ${isAnomaly ? "text-rose-400 animate-bounce" : "text-slate-400"}`}
          />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span
            className={`text-2xl font-bold font-mono ${
              isAnomaly ? "text-rose-400" : "text-white"
            }`}
          >
            {score.toFixed(4)}
          </span>
          {isAnomaly && (
            <span className="rounded bg-rose-900/80 px-1.5 py-0.5 text-[10px] font-bold text-rose-200">
              FAULT
            </span>
          )}
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full transition-all duration-300 ${
              isAnomaly ? "bg-rose-500" : "bg-blue-500"
            }`}
            style={{ width: `${scorePct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 font-mono">
          <span>0.0</span>
          <span>{frozenThreshold ? frozenThreshold.toFixed(4) : "Threshold"}</span>
          <span>1.0</span>
        </div>
      </div>
    </div>
  );
}
