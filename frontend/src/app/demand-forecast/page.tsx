"use client";

import React, { useState } from "react";
import { TrendingUp, Filter, ShieldCheck, ChevronLeft, ChevronRight, AlertTriangle } from "lucide-react";
import { useDemandForecast, useModelGovernance } from "@/hooks/usePredictions";
import { ErrorBanner, SkeletonTable, EmptyState } from "@/components/common/EmptyState";
import { DemandForecastBandChart } from "@/components/charts/DemandForecastBandChart";
import { StatusBadge } from "@/components/common/StatusBadge";
import { formatDate } from "@/lib/utils";

export default function DemandForecastPage() {
  const [dealerFilter, setDealerFilter] = useState<string>("");
  const [surgeOnly, setSurgeOnly] = useState<boolean>(false);
  const [offset, setOffset] = useState<number>(0);
  const limit = 15;

  const { forecasts, total, loading, error, refetch } = useDemandForecast({
    limit,
    offset,
    dealer_id: dealerFilter || undefined,
    is_surge: surgeOnly ? true : undefined,
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
            <TrendingUp className="h-6 w-6 text-blue-400" />
            <span>Area 3: Service Demand Forecast & Capacity Horizon</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Time-series service demand volume forecasting with 80% confidence intervals and capacity surge alerts.
          </p>
        </div>

        {/* Dynamic Proposed Threshold Badge */}
        <div className="flex items-center gap-2 rounded-xl border border-amber-900/60 bg-amber-950/30 px-3.5 py-2 text-xs">
          <ShieldCheck className="h-4 w-4 text-amber-400 shrink-0" />
          <div>
            <span className="text-amber-200 font-semibold block">PROPOSED INITIAL THRESHOLD</span>
            <span className="text-[11px] text-amber-300/80">
              Proposed Surge Warning:{" "}
              <strong className="font-mono text-white">
                {governance?.area_3_service_demand.threshold_value !== undefined
                  ? `+${Number(governance.area_3_service_demand.threshold_value) * 100}%`
                  : "Loading..."}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Demand Horizon & Confidence Band
            </h2>
            <p className="text-[11px] text-slate-400">
              Predicted service volume trajectory and 80% prediction intervals
            </p>
          </div>
          {forecasts.some((f) => f.is_surge) && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-900/80 bg-rose-950/40 px-3 py-1 text-[11px] font-semibold text-rose-300">
              <AlertTriangle className="h-3 w-3 text-rose-400" />
              Surge Events Detected
            </span>
          )}
        </div>

        {loading ? (
          <div className="h-72 flex items-center justify-center text-xs text-slate-500">
            Loading forecast chart...
          </div>
        ) : forecasts.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-xs text-slate-500">
            No forecast points available for the selected parameters.
          </div>
        ) : (
          <DemandForecastBandChart data={forecasts} />
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filters:</span>
        </div>

        <input
          type="text"
          placeholder="Filter by Dealer ID (e.g. DLR-01)..."
          value={dealerFilter}
          onChange={(e) => {
            setDealerFilter(e.target.value);
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none font-mono"
        />

        <button
          onClick={() => {
            setSurgeOnly(!surgeOnly);
            setOffset(0);
          }}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition border ${
            surgeOnly
              ? "bg-rose-950/80 text-rose-300 border-rose-800"
              : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
          }`}
        >
          {surgeOnly ? "SHOWING SURGE DAYS ONLY" : "SHOW ALL DAYS"}
        </button>

        {dealerFilter && (
          <button
            onClick={() => {
              setDealerFilter("");
              setOffset(0);
            }}
            className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-4"
          >
            Clear Filter
          </button>
        )}

        <div className="ml-auto text-xs text-slate-400">
          Total Horizons: <strong className="text-white font-mono">{total}</strong>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Data Table */}
      {loading ? (
        <SkeletonTable rows={10} cols={7} />
      ) : forecasts.length === 0 ? (
        <EmptyState
          title="No forecast records found"
          description="No forecasts match the selected filter conditions."
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4">Forecast Date</th>
                  <th className="py-3.5 px-4">Dealer ID</th>
                  <th className="py-3.5 px-4">Predicted Demand</th>
                  <th className="py-3.5 px-4">Lower Bound (80%)</th>
                  <th className="py-3.5 px-4">Upper Bound (80%)</th>
                  <th className="py-3.5 px-4">Surge Warning</th>
                  <th className="py-3.5 px-4">Model Version</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {forecasts.map((f) => (
                  <tr key={f.forecast_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-sans font-medium text-white">
                      {String(f.forecast_date).split("T")[0]}
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-semibold">{f.dealer_id}</td>
                    <td className="py-3 px-4 font-bold text-blue-300">
                      {(f.predicted_volume ?? 0).toFixed(1)} units
                    </td>
                    <td className="py-3 px-4 text-slate-400">{(f.lower_bound_80 ?? 0).toFixed(1)}</td>
                    <td className="py-3 px-4 text-slate-400">{(f.upper_bound_80 ?? 0).toFixed(1)}</td>
                    <td className="py-3 px-4">
                      {f.is_surge ? (
                        <StatusBadge status="SURGE" size="sm" />
                      ) : (
                        <StatusBadge status="NORMAL" size="sm" />
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{f.model_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 bg-slate-950/60 text-xs text-slate-400">
            <div>
              Showing {total > 0 ? offset + 1 : 0} to {Math.min(offset + limit, total)} of {total} horizons
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
