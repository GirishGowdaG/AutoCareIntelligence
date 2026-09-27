"use client";

import React, { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Activity, ShieldCheck, Filter, ChevronLeft, ChevronRight, CheckCircle2, Radio } from "lucide-react";
import { useSensorAnomalies } from "@/hooks/usePredictions";
import { useSSEStream } from "@/hooks/useSSEStream";
import { ErrorBanner, SkeletonTable, EmptyState } from "@/components/common/EmptyState";
import { LiveTelemetryGauges } from "@/components/charts/LiveTelemetryGauges";
import { StatusBadge } from "@/components/common/StatusBadge";
import { formatDate } from "@/lib/utils";
import { TelemetryData } from "@/types/audit";

export default function SensorAnomaliesPage() {
  const searchParams = useSearchParams();
  const initialVehicleId = searchParams.get("vehicle_id") || "";

  const [vehicleIdFilter, setVehicleIdFilter] = useState<string>(initialVehicleId);
  const [anomalyOnly, setAnomalyOnly] = useState<boolean>(false);
  const [offset, setOffset] = useState<number>(0);
  const limit = 15;

  const { records, total, frozenThreshold, loading, error, refetch } = useSensorAnomalies({
    limit,
    offset,
    vehicle_id: vehicleIdFilter || undefined,
    is_anomaly: anomalyOnly ? true : undefined,
  });

  const { latestTelemetry, isConnected, source } = useSSEStream();

  // Active CAN-bus telemetry data from live SSE stream or standard operational baseline
  const activeTelemetry: TelemetryData = latestTelemetry?.data || {
    vehicle_id: vehicleIdFilter || "VH001",
    rpm: 2450,
    temperature: 92.5,
    battery: 13.8,
    vibration: 1.25,
  };

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Activity className="h-6 w-6 text-teal-400" />
            <span>Area 2: CAN-Bus Sensor Anomaly Monitor</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Unsupervised reconstruction error scoring and live telemetry pulse threshold surveillance.
          </p>
        </div>

        {/* Frozen Threshold Badge */}
        <div className="flex items-center gap-2 rounded-xl border border-emerald-900/60 bg-emerald-950/30 px-3.5 py-2 text-xs">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <div>
            <span className="text-emerald-200 font-semibold block">FROZEN / APPROVED</span>
            <span className="text-[11px] text-emerald-300/80">
              Frozen Calibration Threshold:{" "}
              <strong className="font-mono text-white">
                {frozenThreshold !== null ? frozenThreshold.toFixed(6) : "Loading..."}
              </strong>{" "}
              (Phase 5 Method B)
            </span>
          </div>
        </div>
      </div>

      {/* Live Telemetry Gauges Section */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Radio className="h-4 w-4 text-blue-400 animate-pulse" />
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Live CAN-Bus Telemetry Pulse Instrument Cluster
              </h2>
              <p className="text-[11px] text-slate-400">
                Displaying real-time sensor parameters: RPM, Temperature (°C), Battery Voltage (V), and Vibration
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span
              className={`h-2 w-2 rounded-full ${
                isConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            <span>
              {source === "kafka"
                ? "[LIVE: Kafka Telemetry]"
                : "[DEMO MODE: Synthetic Telemetry]"}
            </span>
          </div>
        </div>

        {/* 4 Approved Gauges */}
        <LiveTelemetryGauges reading={activeTelemetry} />
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filters:</span>
        </div>

        <input
          type="text"
          placeholder="Filter by Vehicle ID (e.g. VEH-001)..."
          value={vehicleIdFilter}
          onChange={(e) => {
            setVehicleIdFilter(e.target.value);
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none font-mono"
        />

        <button
          onClick={() => {
            setAnomalyOnly(!anomalyOnly);
            setOffset(0);
          }}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition border ${
            anomalyOnly
              ? "bg-rose-950/80 text-rose-300 border-rose-800"
              : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
          }`}
        >
          {anomalyOnly ? "SHOWING ANOMALIES ONLY" : "SHOW ALL SNAPSHOTS"}
        </button>

        {vehicleIdFilter && (
          <button
            onClick={() => {
              setVehicleIdFilter("");
              setOffset(0);
            }}
            className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-4"
          >
            Clear Filter
          </button>
        )}

        <div className="ml-auto text-xs text-slate-400">
          Total Snapshots: <strong className="text-white font-mono">{total}</strong>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Data Table */}
      {loading ? (
        <SkeletonTable rows={10} cols={6} />
      ) : records.length === 0 ? (
        <EmptyState
          title="No sensor anomaly records found"
          description="No telemetry snapshot records match the given criteria."
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4">Vehicle ID</th>
                  <th className="py-3.5 px-4">Window Timestamp</th>
                  <th className="py-3.5 px-4">Anomaly Score</th>
                  <th className="py-3.5 px-4">Classification</th>
                  <th className="py-3.5 px-4">Frozen Calibration Target</th>
                  <th className="py-3.5 px-4">Model Version</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {records.map((r) => (
                  <tr key={r.anomaly_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-semibold text-white">
                      {r.vehicle_id}
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-400">
                      {formatDate(r.window_timestamp || r.detected_at)}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`font-bold ${
                          r.is_anomaly ? "text-rose-400" : "text-slate-200"
                        }`}
                      >
                        {r.anomaly_score.toFixed(6)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {r.is_anomaly ? (
                        <StatusBadge status="ANOMALY" size="sm" />
                      ) : (
                        <StatusBadge status="NORMAL" size="sm" />
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-xs">
                      {frozenThreshold !== null ? (
                        <span>
                          {r.anomaly_score > frozenThreshold ? (
                            <span className="text-rose-400 font-semibold">&gt; {frozenThreshold.toFixed(6)}</span>
                          ) : (
                            <span className="text-emerald-400 font-semibold">&le; {frozenThreshold.toFixed(6)}</span>
                          )}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-sans">{r.model_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 bg-slate-950/60 text-xs text-slate-400">
            <div>
              Showing {total > 0 ? offset + 1 : 0} to {Math.min(offset + limit, total)} of {total} records
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
                className="rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-slate-300 disabled:opacity-40 hover:bg-slate-800"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="px-2 font-mono">
                {currentPage} / {totalPages}
              </span>
              <button
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}
                className="rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-slate-300 disabled:opacity-40 hover:bg-slate-800"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
