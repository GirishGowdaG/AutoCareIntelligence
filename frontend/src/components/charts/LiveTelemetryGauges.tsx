"use client";

import React from "react";
import { Gauge, Thermometer, BatteryCharging, Activity } from "lucide-react";
import { TelemetryData } from "@/types/audit";

interface LiveTelemetryGaugesProps {
  reading: TelemetryData | null;
}

export function LiveTelemetryGauges({ reading }: LiveTelemetryGaugesProps) {
  if (!reading) {
    return (
      <div className="flex h-48 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/40 text-xs text-slate-500">
        Waiting for CAN-bus telemetry pulse stream...
      </div>
    );
  }

  const rpm = reading.rpm ?? 0;
  const temperature = reading.temperature ?? 0;
  const battery = reading.battery ?? 0;
  const vibration = reading.vibration ?? 0;

  // Normalization percentages for visual gauge progress bars
  const rpmPct = Math.min(Math.max((rpm / 6000) * 100, 0), 100);
  const tempPct = Math.min(Math.max((temperature / 130) * 100, 0), 100);
  const batteryPct = Math.min(Math.max(((battery - 9) / (16 - 9)) * 100, 0), 100);
  const vibrationPct = Math.min(Math.max((vibration / 5.0) * 100, 0), 100);

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {/* 1. RPM Gauge */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">RPM</span>
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

      {/* 2. Temperature Gauge */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">Temperature (°C)</span>
          <Thermometer className="h-4 w-4 text-amber-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-2xl font-bold font-mono text-white">
            {typeof temperature === "number" ? temperature.toFixed(1) : temperature}
          </span>
          <span className="text-xs text-slate-400">°C</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full transition-all duration-300 ${
              temperature > 105 ? "bg-rose-500" : temperature > 95 ? "bg-amber-500" : "bg-teal-500"
            }`}
            style={{ width: `${tempPct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 font-mono">
          <span>0°C</span>
          <span>65°C</span>
          <span>130°C</span>
        </div>
      </div>

      {/* 3. Battery Voltage Gauge */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">Battery Voltage (V)</span>
          <BatteryCharging className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-2xl font-bold font-mono text-white">
            {typeof battery === "number" ? battery.toFixed(1) : battery}
          </span>
          <span className="text-xs text-slate-400">V</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full transition-all duration-300 ${
              battery < 11.5 ? "bg-rose-500" : battery < 12.2 ? "bg-amber-500" : "bg-emerald-500"
            }`}
            style={{ width: `${batteryPct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 font-mono">
          <span>9.0V</span>
          <span>12.5V</span>
          <span>16.0V</span>
        </div>
      </div>

      {/* 4. Vibration Gauge */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider">Vibration</span>
          <Activity className="h-4 w-4 text-purple-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-2xl font-bold font-mono text-white">
            {typeof vibration === "number" ? vibration.toFixed(2) : vibration}
          </span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full transition-all duration-300 ${
              vibration > 3.0 ? "bg-rose-500" : vibration > 2.0 ? "bg-amber-500" : "bg-purple-500"
            }`}
            style={{ width: `${vibrationPct}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 font-mono">
          <span>0.0</span>
          <span>2.5</span>
          <span>5.0</span>
        </div>
      </div>
    </div>
  );
}
