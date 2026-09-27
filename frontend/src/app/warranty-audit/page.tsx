"use client";

import React, { useState } from "react";
import { useSearchParams } from "next/navigation";
import { FileCheck2, ShieldAlert, Filter, ChevronLeft, ChevronRight, ShieldCheck, AlertCircle } from "lucide-react";
import { useWarrantyAnomalies, useModelGovernance } from "@/hooks/usePredictions";
import { useAuthRole } from "@/hooks/useAuthRole";
import { ErrorBanner, SkeletonTable, EmptyState } from "@/components/common/EmptyState";
import { ForbiddenView } from "@/components/common/ForbiddenView";
import { StatusBadge } from "@/components/common/StatusBadge";
import { formatCurrency } from "@/lib/utils";

export default function WarrantyAuditPage() {
  const searchParams = useSearchParams();
  const targetClaimId = searchParams.get("claim_id") || "";

  const { role, canAccessWarranty } = useAuthRole();
  const [dealerFilter, setDealerFilter] = useState<string>("");
  const [claimSearch, setClaimSearch] = useState<string>(targetClaimId);
  const [offset, setOffset] = useState<number>(0);
  const limit = 15;

  const { records, total, loading, error, status, refetch } = useWarrantyAnomalies({
    limit,
    offset,
    dealer_id: dealerFilter || undefined,
  });

  const { governance } = useModelGovernance();

  // RBAC check: DealerServiceManager is forbidden
  if (!canAccessWarranty || status === 403) {
    return (
      <ForbiddenView
        requiredRole="Admin or FleetAnalyst"
        resourceName="Warranty Anomaly Forensic Audit"
      />
    );
  }

  // Client-side filtering for claim_id (since Stage 2 backend does not have claim_id query parameter)
  const filteredRecords = claimSearch.trim()
    ? records.filter((r) => r.claim_id.toLowerCase().includes(claimSearch.trim().toLowerCase()))
    : records;

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  // Format proposed threshold display dynamically
  const threshVal = governance?.area_4_warranty_anomaly.threshold_value;
  const topPercent = threshVal !== undefined && typeof threshVal === "number"
    ? `${((1 - threshVal) * 100).toFixed(0)}%`
    : "Top Outliers";

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <FileCheck2 className="h-6 w-6 text-rose-400" />
            <span>Area 4: Warranty Anomaly Forensic Audit Queue</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Unsupervised statistical outlier scoring for warranty claims prioritization and investigation.
          </p>
        </div>

        {/* Dynamic Proposed Threshold Badge */}
        <div className="flex items-center gap-2 rounded-xl border border-amber-900/60 bg-amber-950/30 px-3.5 py-2 text-xs">
          <ShieldCheck className="h-4 w-4 text-amber-400 shrink-0" />
          <div>
            <span className="text-amber-200 font-semibold block">PROPOSED INITIAL THRESHOLD</span>
            <span className="text-[11px] text-amber-300/80">
              Proposed Audit Threshold:{" "}
              <strong className="font-mono text-white">
                {threshVal !== undefined ? `Top ${topPercent} Outliers (Score >= ${threshVal})` : "Loading..."}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* Statutory Legal Disclaimer Banner */}
      <div className="flex items-start gap-3 rounded-2xl border border-blue-900/60 bg-blue-950/40 p-4 text-blue-200">
        <ShieldAlert className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <strong className="font-semibold text-white">STATUTORY GOVERNANCE NOTICE:</strong>{" "}
          Unsupervised statistical outlier detection for audit prioritization only. Does not constitute proof of dealer fraud or misconduct. All claims require independent forensic review before administrative action.
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filters:</span>
        </div>

        <input
          type="text"
          placeholder="Client-side Claim ID search..."
          value={claimSearch}
          onChange={(e) => setClaimSearch(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none font-mono"
        />

        <input
          type="text"
          placeholder="Backend Dealer ID (e.g. DLR-01)..."
          value={dealerFilter}
          onChange={(e) => {
            setDealerFilter(e.target.value);
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none font-mono"
        />

        {(claimSearch || dealerFilter) && (
          <button
            onClick={() => {
              setClaimSearch("");
              setDealerFilter("");
              setOffset(0);
            }}
            className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-4"
          >
            Clear Filters
          </button>
        )}

        <div className="ml-auto text-xs text-slate-400">
          Total Flagged: <strong className="text-white font-mono">{total}</strong>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Data Table */}
      {loading ? (
        <SkeletonTable rows={10} cols={8} />
      ) : filteredRecords.length === 0 ? (
        <EmptyState
          title="No flagged warranty claims"
          description="No warranty claim outlier records match the current filter parameters."
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4">Claim ID</th>
                  <th className="py-3.5 px-4">Dealer ID</th>
                  <th className="py-3.5 px-4">Vehicle ID</th>
                  <th className="py-3.5 px-4">Anomaly Score</th>
                  <th className="py-3.5 px-4">Claim Total</th>
                  <th className="py-3.5 px-4">Labor Hours</th>
                  <th className="py-3.5 px-4">Parts Cost</th>
                  <th className="py-3.5 px-4">Labor Cost</th>
                  <th className="py-3.5 px-4 text-center">Audit Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {filteredRecords.map((c) => {
                  const isHighlighted = targetClaimId && c.claim_id === targetClaimId;
                  return (
                    <tr
                      key={c.claim_id}
                      className={`transition ${
                        isHighlighted
                          ? "bg-rose-950/40 border-l-4 border-rose-500 font-bold"
                          : "hover:bg-slate-800/40"
                      }`}
                    >
                      <td className="py-3 px-4 text-white">
                        {c.claim_id}
                        {isHighlighted && (
                          <span className="ml-2 rounded bg-rose-600 px-1.5 py-0.2 text-[9px] text-white uppercase font-sans">
                            Targeted
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-300">{c.dealer_id}</td>
                      <td className="py-3 px-4 text-slate-300">{c.vehicle_id}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`font-bold ${
                            c.is_outlier ? "text-rose-400" : "text-slate-300"
                          }`}
                        >
                          {c.anomaly_score.toFixed(4)}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-bold text-white font-sans">
                        {formatCurrency(c.claim_amount)}
                      </td>
                      <td className="py-3 px-4 text-slate-300">{c.labor_hours.toFixed(1)} hrs</td>
                      <td className="py-3 px-4 font-sans text-slate-400">
                        {formatCurrency(c.parts_cost)}
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-400">
                        {formatCurrency(c.labor_cost)}
                      </td>
                      <td className="py-3 px-4 text-center font-sans">
                        {c.audit_recommended ? (
                          <StatusBadge status="AUDIT REQUIRED" size="sm" />
                        ) : (
                          <StatusBadge status="NORMAL" size="sm" />
                        )}
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
              Showing {total > 0 ? offset + 1 : 0} to {Math.min(offset + limit, total)} of {total} claims
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
