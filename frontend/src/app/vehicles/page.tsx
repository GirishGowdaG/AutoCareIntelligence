"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Truck, Search, ChevronLeft, ChevronRight, ArrowRight } from "lucide-react";
import { useVehicles } from "@/hooks/useVehicles";
import { ErrorBanner, SkeletonTable, EmptyState } from "@/components/common/EmptyState";

export default function VehiclesPage() {
  const [offset, setOffset] = useState(0);
  const limit = 15;
  const [makeFilter, setMakeFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");

  const { vehicles, total, loading, error, refetch } = useVehicles({
    limit,
    offset,
    make: makeFilter || undefined,
    state: stateFilter || undefined,
  });

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Truck className="h-6 w-6 text-blue-400" />
            <span>Fleet Inventory & Diagnostic Records</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Active fleet vehicle assets, specifications, and telemetry diagnostic linkage.
          </p>
        </div>
        <div className="text-xs text-slate-400">
          Total Fleet Assets: <strong className="text-white font-mono">{total}</strong>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filters:</span>
        </div>

        <input
          type="text"
          placeholder="Filter by Make (e.g. Ford)..."
          value={makeFilter}
          onChange={(e) => {
            setMakeFilter(e.target.value);
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
        />

        <input
          type="text"
          placeholder="Filter by State (e.g. TX)..."
          value={stateFilter}
          onChange={(e) => {
            setStateFilter(e.target.value);
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
        />

        {(makeFilter || stateFilter) && (
          <button
            onClick={() => {
              setMakeFilter("");
              setStateFilter("");
              setOffset(0);
            }}
            className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-4"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Error state */}
      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Table section */}
      {loading ? (
        <SkeletonTable rows={10} cols={7} />
      ) : vehicles.length === 0 ? (
        <EmptyState
          title="No vehicles found"
          description="Try modifying your search criteria or resetting filters."
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4">Vehicle ID</th>
                  <th className="py-3.5 px-4">Make</th>
                  <th className="py-3.5 px-4">Model</th>
                  <th className="py-3.5 px-4">Year</th>
                  <th className="py-3.5 px-4">Body Class</th>
                  <th className="py-3.5 px-4">Engine Type</th>
                  <th className="py-3.5 px-4">State</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {vehicles.map((v) => (
                  <tr key={v.vehicle_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-semibold text-white">
                      {v.vehicle_id}
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-200">{v.make}</td>
                    <td className="py-3 px-4 font-sans text-slate-200">{v.model_name}</td>
                    <td className="py-3 px-4">{v.model_year}</td>
                    <td className="py-3 px-4 font-sans text-slate-400">{v.body_class}</td>
                    <td className="py-3 px-4 font-sans text-slate-400">{v.engine_type}</td>
                    <td className="py-3 px-4">
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-300 border border-slate-700">
                        {v.state}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/vehicles/${encodeURIComponent(v.vehicle_id)}`}
                        className="inline-flex items-center gap-1 font-sans text-xs font-semibold text-blue-400 hover:text-blue-300"
                      >
                        <span>Diagnostics</span>
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 bg-slate-950/60 text-xs text-slate-400">
            <div>
              Showing {total > 0 ? offset + 1 : 0} to {Math.min(offset + limit, total)} of {total} vehicles
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
