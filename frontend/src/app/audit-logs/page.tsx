"use client";

import React, { useState } from "react";
import { ScrollText, Filter, ChevronLeft, ChevronRight, ShieldCheck, Shield } from "lucide-react";
import { useActionLogs } from "@/hooks/useActionLogs";
import { useAuthRole } from "@/hooks/useAuthRole";
import { ErrorBanner, SkeletonTable, EmptyState } from "@/components/common/EmptyState";
import { ForbiddenView } from "@/components/common/ForbiddenView";
import { StatusBadge } from "@/components/common/StatusBadge";
import { formatDate } from "@/lib/utils";

export default function AuditLogsPage() {
  const { canAccessAuditLogs } = useAuthRole();
  const [entityFilter, setEntityFilter] = useState<string>("");
  const [deliveryFilter, setDeliveryFilter] = useState<string>("");
  const [offset, setOffset] = useState<number>(0);
  const limit = 15;

  const { logs, total, loading, error, status, refetch } = useActionLogs({
    limit,
    offset,
    entity_type: entityFilter || undefined,
    delivery_status: deliveryFilter || undefined,
  });

  // Strict RBAC: Admin only
  if (!canAccessAuditLogs || status === 403) {
    return (
      <ForbiddenView
        requiredRole="Admin"
        resourceName="Decision Automation Action Audit Logs"
      />
    );
  }

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <ScrollText className="h-6 w-6 text-purple-400" />
            <span>Decision Automation Action Audit Trail</span>
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Immutable audit record of all automated prescriptive workflows, dispatches, and notifications.
          </p>
        </div>

        {/* Admin RBAC Badge */}
        <div className="flex items-center gap-2 rounded-xl border border-purple-900/60 bg-purple-950/30 px-3.5 py-2 text-xs">
          <Shield className="h-4 w-4 text-purple-400 shrink-0" />
          <div>
            <span className="text-purple-200 font-semibold block">ADMINISTRATOR ACCESS</span>
            <span className="text-[11px] text-purple-300/80">Full audit privileges verified</span>
          </div>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filters:</span>
        </div>

        {/* Entity Type Filter */}
        <select
          value={entityFilter}
          onChange={(e) => {
            setEntityFilter(e.target.value);
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-blue-500 focus:outline-none"
        >
          <option value="">All Entities</option>
          <option value="VEHICLE">VEHICLE</option>
          <option value="DEALER">DEALER</option>
          <option value="CLAIM">CLAIM</option>
        </select>

        {/* Delivery Status Filter */}
        <select
          value={deliveryFilter}
          onChange={(e) => {
            setDeliveryFilter(e.target.value);
            setOffset(0);
          }}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white focus:border-blue-500 focus:outline-none"
        >
          <option value="">All Delivery Statuses</option>
          <option value="DELIVERED">DELIVERED</option>
          <option value="MOCK_LOGGED">MOCK_LOGGED</option>
          <option value="FAILED">FAILED</option>
        </select>

        {(entityFilter || deliveryFilter) && (
          <button
            onClick={() => {
              setEntityFilter("");
              setDeliveryFilter("");
              setOffset(0);
            }}
            className="text-xs text-blue-400 hover:text-blue-300 underline underline-offset-4"
          >
            Clear Filters
          </button>
        )}

        <div className="ml-auto text-xs text-slate-400">
          Total Logs: <strong className="text-white font-mono">{total}</strong>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Data Table */}
      {loading ? (
        <SkeletonTable rows={10} cols={7} />
      ) : logs.length === 0 ? (
        <EmptyState
          title="No action logs found"
          description="No automated decision actions match the selected filter criteria."
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4">Trigger Timestamp</th>
                  <th className="py-3.5 px-4">Action ID</th>
                  <th className="py-3.5 px-4">Rule ID</th>
                  <th className="py-3.5 px-4">Target Entity</th>
                  <th className="py-3.5 px-4">Action Taken</th>
                  <th className="py-3.5 px-4">Channel</th>
                  <th className="py-3.5 px-4 text-center">Delivery Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {logs.map((log) => (
                  <tr key={log.action_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-sans text-slate-400">
                      {formatDate(log.trigger_timestamp || log.created_at)}
                    </td>
                    <td className="py-3 px-4 text-white font-semibold">{log.action_id}</td>
                    <td className="py-3 px-4 text-blue-300 font-semibold">{log.rule_id}</td>
                    <td className="py-3 px-4 text-slate-200">
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400 border border-slate-700 mr-1.5">
                        {log.entity_type}
                      </span>
                      {log.entity_id}
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-200">{log.action_taken}</td>
                    <td className="py-3 px-4 font-sans text-slate-400">
                      <span className="rounded bg-slate-800/80 px-2 py-0.5 text-[11px] font-mono text-slate-300 border border-slate-700">
                        {log.channel_dispatched}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center font-sans">
                      <StatusBadge status={log.delivery_status} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 bg-slate-950/60 text-xs text-slate-400">
            <div>
              Showing {total > 0 ? offset + 1 : 0} to {Math.min(offset + limit, total)} of {total} audit records
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
