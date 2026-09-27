"use client";

import React from "react";
import { ShieldCheck, X, FileText, CheckCircle2, AlertCircle } from "lucide-react";
import { ModelGovernanceResponse, ModelGovernanceItem } from "@/types/ml";
import { formatDate } from "@/lib/utils";

interface ModelGovernanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  governance: ModelGovernanceResponse | null;
  loading: boolean;
}

export function ModelGovernanceDrawer({
  isOpen,
  onClose,
  governance,
  loading,
}: ModelGovernanceDrawerProps) {
  if (!isOpen) return null;

  const areas: ModelGovernanceItem[] = governance
    ? [
        governance.area_1_failure_risk,
        governance.area_2_sensor_anomaly,
        governance.area_3_service_demand,
        governance.area_4_warranty_anomaly,
      ]
    : [];

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col border-l border-slate-800 bg-slate-950 p-6 shadow-2xl backdrop-blur-xl animate-in slide-in-from-right duration-200">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-emerald-400" />
          <div>
            <h2 className="text-base font-bold text-white">Model Governance Registry</h2>
            <p className="text-xs text-slate-400">Formal Phase 5 & 6 Calibration & Threshold Manifests</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-900 hover:text-slate-200"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto space-y-4 pr-1">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-slate-400 text-xs">
            Loading ratified model governance manifests...
          </div>
        ) : !governance ? (
          <div className="text-xs text-rose-400 p-4">Failed to load governance registry.</div>
        ) : (
          areas.map((item, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    {item.area_name}
                  </span>
                  <div className="text-xs text-slate-400">
                    Model: <span className="font-semibold text-slate-200">{item.model_name}</span> (v{item.version})
                  </div>
                </div>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold border ${
                    item.is_frozen
                      ? "border-emerald-800 bg-emerald-950/60 text-emerald-300"
                      : "border-amber-800 bg-amber-950/60 text-amber-300"
                  }`}
                >
                  {item.is_frozen ? (
                    <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                  ) : (
                    <AlertCircle className="h-3 w-3 text-amber-400" />
                  )}
                  {item.governance_display}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 rounded-lg bg-slate-950 p-2.5 text-xs">
                <div>
                  <span className="text-[11px] text-slate-400 block">{item.primary_metric_name}</span>
                  <span className="font-mono font-semibold text-slate-200">
                    {item.primary_metric_display}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">{item.threshold_label}</span>
                  <span className="font-mono font-semibold text-blue-300">
                    {item.threshold_value !== undefined && item.threshold_value !== null
                      ? String(item.threshold_value)
                      : "—"}
                  </span>
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 text-[11px] text-slate-400">
                <div className="flex items-center gap-1.5 text-slate-300 font-medium mb-1">
                  <FileText className="h-3.5 w-3.5 text-slate-400" />
                  <span>Manifest Provenance</span>
                </div>
                <div className="font-mono text-[10px] text-slate-400 break-all">
                  {item.manifest_path}
                </div>
                <div className="mt-1 text-[10px] text-slate-400">
                  {item.manifest_provenance}
                </div>
              </div>
            </div>
          ))
        )}

        {governance?.timestamp && (
          <div className="text-right text-[11px] text-slate-500 pt-2">
            Verified as of: {formatDate(governance.timestamp)}
          </div>
        )}
      </div>
    </div>
  );
}
