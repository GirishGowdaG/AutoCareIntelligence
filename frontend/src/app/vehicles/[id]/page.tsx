"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Truck, AlertCircle, CheckCircle, Activity } from "lucide-react";
import { useVehicleDetail } from "@/hooks/useVehicles";
import { ErrorBanner, SkeletonTable, EmptyState } from "@/components/common/EmptyState";
import { formatDate } from "@/lib/utils";
import { StatusBadge } from "@/components/common/StatusBadge";

export default function VehicleDetailPage() {
  const params = useParams();
  const vehicleId = params.id as string;
  const { vehicle, loading, error, refetch } = useVehicleDetail(vehicleId);

  return (
    <div className="space-y-6">
      {/* Header and Back navigation */}
      <div>
        <Link
          href="/vehicles"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 transition mb-3"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Fleet List
        </Link>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            <Truck className="h-7 w-7 text-blue-400" />
            <span>Vehicle Diagnostics: <span className="font-mono text-blue-300">{vehicleId}</span></span>
          </h1>
          <Link
            href={`/sensor-anomalies?vehicle_id=${encodeURIComponent(vehicleId)}`}
            className="inline-flex items-center gap-2 rounded-xl border border-blue-900/60 bg-blue-950/40 px-3.5 py-2 text-xs font-semibold text-blue-300 hover:bg-blue-900/50"
          >
            <Activity className="h-4 w-4 text-blue-400" />
            <span>CAN-Bus Telemetry Stream</span>
          </Link>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {loading ? (
        <SkeletonTable rows={5} cols={4} />
      ) : !vehicle ? (
        <EmptyState title="Vehicle not found" description="The requested vehicle record could not be loaded." />
      ) : (
        <>
          {/* Vehicle Metadata Specification Card */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Model</span>
              <p className="mt-1 text-sm font-bold text-white">{vehicle.model_name || "—"}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Trim / Variant</span>
              <p className="mt-1 text-sm font-bold text-white">{vehicle.variant || "—"}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Manufacture Year</span>
              <p className="mt-1 text-sm font-bold text-white">{vehicle.manufacture_year || "—"}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Vehicle Class</span>
              <p className="mt-1 text-sm font-bold text-white">{vehicle.vehicle_class || "—"}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Powertrain</span>
              <p className="mt-1 text-sm font-bold text-white">{vehicle.powertrain_type || "—"}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Curb Weight</span>
              <p className="mt-1 text-sm font-bold text-white">{vehicle.curb_weight_kg ? `${vehicle.curb_weight_kg} kg` : "—"}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Dealership</span>
              <p className="mt-1 text-sm font-bold text-white truncate" title={vehicle.selling_dealer_name ?? undefined}>{vehicle.selling_dealer_name || "—"}</p>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Status</span>
              <p className="mt-1 text-sm font-bold text-emerald-400">{vehicle.status || "ACTIVE"}</p>
            </div>
          </div>

          {/* Diagnostic Trouble Code Snapshots */}
          {(() => {
            const diagnostics = vehicle.diagnostics || [];
            return (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div>
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                      Diagnostic Snapshot Records
                    </h2>
                    <p className="text-xs text-slate-400">
                      OBD-II Diagnostic Trouble Codes (DTC) and component severity history
                    </p>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {diagnostics.length} Records
                  </span>
                </div>

                {diagnostics.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500">
                    No active DTC fault codes recorded for this vehicle.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                        <tr>
                          <th className="py-3 px-4">Timestamp</th>
                          <th className="py-3 px-4">DTC Code</th>
                          <th className="py-3 px-4">Subsystem Component</th>
                          <th className="py-3 px-4">Severity</th>
                          <th className="py-3 px-4 font-mono text-slate-500">Diagnostic ID</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                        {diagnostics.map((diag) => (
                          <tr key={diag.diagnostic_id} className="hover:bg-slate-800/40 transition">
                            <td className="py-3 px-4 font-sans text-slate-400">
                              {formatDate(diag.timestamp)}
                            </td>
                        <td className="py-3 px-4">
                          {diag.dtc_code ? (
                            <span className="font-bold text-rose-400 bg-rose-950/80 px-2 py-0.5 rounded border border-rose-900/60 font-mono">
                              {diag.dtc_code}
                            </span>
                          ) : (
                            <span className="text-slate-500 font-sans">None</span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-sans text-slate-200">
                          {diag.component || "General System"}
                        </td>
                        <td className="py-3 px-4">
                          {diag.severity ? (
                            <StatusBadge status={diag.severity} size="sm" />
                          ) : (
                            <span className="text-slate-500 font-sans">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                          {diag.diagnostic_id}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
