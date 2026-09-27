"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AlertTriangle, Filter, ChevronLeft, ChevronRight, ArrowRight, ShieldCheck } from "lucide-react";
import { useFailureRisk, useModelGovernance } from "@/hooks/usePredictions";
import { ErrorBanner, SkeletonTable, EmptyState } from "@/components/common/EmptyState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { formatDate } from "@/lib/utils";

export default function FailureRiskPage() {
  const [tierFilter, setTierFilter] = useState<string>("");
  const [offset, setOffset] = useState<number>(0);
  const limit = 15;

  const { predictions, total, loading, error, refetch } = useFailureRisk({
    limit,
    offset,
    risk_tier: tierFilter || undefined,
  });

  const { governance } = useModelGovernance();

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <AlertTriangle className="h-6 w-6 text-rose-400" />
            <span>Area 1: Failure Risk Priority Radar</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Gradient boosted component failure probability scoring and predictive maintenance triage.
          </p>
        </div>

        {/* Dynamic Threshold Provenance Badge */}
        <div className="flex items-center gap-2 rounded-xl border border-amber-900/60 bg-amber-950/30 px-3.5 py-2 text-xs">
          <ShieldCheck className="h-4 w-4 text-amber-400 shrink-0" />
          <div>
            <span className="text-amber-200 font-semibold block">PROPOSED INITIAL THRESHOLD</span>
            <span className="text-[11px] text-amber-300/80">
              Proposed Initial Trigger:{" "}
              <strong className="font-mono text-white">
                {governance?.area_1_failure_risk.threshold_value ?? "Loading..."}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filter by Tier:</span>
        </div>

        {["", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((tier) => (
          <button
            key={tier}
            onClick={() => {
              setTierFilter(tier);
              setOffset(0);
            }}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition border ${
              tierFilter === tier
                ? "bg-blue-600 text-white border-blue-500"
                : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
            }`}
          >
            {tier === "" ? "ALL TIERS" : tier}
          </button>
        ))}

        <div className="ml-auto text-xs text-slate-400">
          Showing <strong className="text-white font-mono">{total}</strong> prioritized assets
        </div>
      </div>

      {/* Error state */}
      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Data Table */}
      {loading ? (
        <SkeletonTable rows={10} cols={6} />
      ) : predictions.length === 0 ? (
        <EmptyState
          title="No predictions found"
          description="No vehicle records match the selected risk tier filter."
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4">Vehicle ID</th>
                  <th className="py-3.5 px-4">Failure Probability</th>
                  <th className="py-3.5 px-4">Risk Tier</th>
                  <th className="py-3.5 px-4">Predicted Component</th>
                  <th className="py-3.5 px-4">Prediction Time</th>
                  <th className="py-3.5 px-4">Model Version</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {predictions.map((p) => {
                  const probPct = (p.failure_probability * 100).toFixed(1);
                  return (
                    <tr key={p.vehicle_id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-semibold text-white">
                        {p.vehicle_id}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-16 overflow-hidden rounded-full bg-slate-800">
                            <div
                              className={`h-full ${
                                p.risk_tier === "CRITICAL"
                                  ? "bg-rose-500"
                                  : p.risk_tier === "HIGH"
                                  ? "bg-amber-500"
                                  : "bg-blue-500"
                              }`}
                              style={{ width: `${Math.min(p.failure_probability * 100, 100)}%` }}
                            />
                          </div>
                          <span className="font-bold text-slate-100">{probPct}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={p.risk_tier} size="sm" />
                      </td>
                      <td className="py-3 px-4 font-sans font-medium text-slate-200">
                        {p.predicted_component}
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-400">
                        {formatDate(p.prediction_timestamp)}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {p.model_version}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          href={`/vehicles/${encodeURIComponent(p.vehicle_id)}`}
                          className="inline-flex items-center gap-1 font-sans text-xs font-semibold text-blue-400 hover:text-blue-300"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
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
