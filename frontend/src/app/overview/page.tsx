"use client";

import React, { useState } from "react";
import {
  Truck,
  AlertTriangle,
  Activity,
  TrendingUp,
  FileCheck2,
  Zap,
  ShieldCheck,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import { useOverviewMetrics, useFailureRisk, useModelGovernance } from "@/hooks/usePredictions";
import { StatCard } from "@/components/common/StatCard";
import { ErrorBanner, SkeletonTable } from "@/components/common/EmptyState";
import { RiskTierBarChart } from "@/components/charts/RiskTierBarChart";
import { ModelGovernanceDrawer } from "@/components/governance/ModelGovernanceDrawer";

export default function OverviewPage() {
  const { metrics, loading: metricsLoading, error: metricsError, refetch: refetchMetrics } = useOverviewMetrics();
  const { predictions, loading: riskLoading } = useFailureRisk({ limit: 100 });
  const { governance, loading: govLoading } = useModelGovernance();
  const [govDrawerOpen, setGovDrawerOpen] = useState(false);

  // Compute risk tier distribution from real predictions
  const tierCounts: Record<string, number> = {
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
  };
  predictions.forEach((p) => {
    if (tierCounts[p.risk_tier] !== undefined) {
      tierCounts[p.risk_tier]++;
    }
  });

  const chartData = [
    { tier: "CRITICAL", count: tierCounts.CRITICAL },
    { tier: "HIGH", count: tierCounts.HIGH },
    { tier: "MEDIUM", count: tierCounts.MEDIUM },
    { tier: "LOW", count: tierCounts.LOW },
  ];

  return (
    <div className="space-y-8">
      {/* Header section */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Executive Overview & Operational Health
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Real-time fleet telemetry, predictive maintenance, and automated warranty anomaly surveillance.
          </p>
        </div>

        {/* Governance Trigger */}
        <button
          onClick={() => setGovDrawerOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl border border-blue-900/60 bg-blue-950/40 px-4 py-2.5 text-xs font-semibold text-blue-300 hover:bg-blue-900/50 transition shadow-sm"
        >
          <ShieldCheck className="h-4 w-4 text-blue-400" />
          <span>Model Governance Registry</span>
        </button>
      </div>

      {/* Error state */}
      {metricsError && (
        <ErrorBanner message={metricsError} onRetry={refetchMetrics} />
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          title="Fleet Size"
          value={metrics ? metrics.total_vehicles : metricsLoading ? "..." : "—"}
          subtitle="Monitored VIN units"
          icon={Truck}
          variant="default"
        />
        <StatCard
          title="Critical Risk"
          value={metrics ? metrics.critical_risk_vehicles : metricsLoading ? "..." : "—"}
          subtitle="Area 1 priority queue"
          icon={AlertTriangle}
          variant="critical"
        />
        <StatCard
          title="Active Anomalies"
          value={metrics ? metrics.active_sensor_anomalies : metricsLoading ? "..." : "—"}
          subtitle="Area 2 sensor faults"
          icon={Activity}
          variant="warning"
        />
        <StatCard
          title="Demand Surges"
          value={metrics ? metrics.surge_demand_regions : metricsLoading ? "..." : "—"}
          subtitle="Area 3 capacity alerts"
          icon={TrendingUp}
          variant="info"
        />
        <StatCard
          title="Flagged Claims"
          value={metrics ? metrics.flagged_warranty_claims : metricsLoading ? "..." : "—"}
          subtitle="Area 4 audit outliers"
          icon={FileCheck2}
          variant="critical"
        />
        <StatCard
          title="Action Logs"
          value={metrics ? metrics.recent_actions_count : metricsLoading ? "..." : "—"}
          subtitle="Automated dispatches"
          icon={Zap}
          variant="success"
        />
      </div>

      {/* Middle Section: Chart and Quick Actions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Risk Distribution Chart */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 lg:col-span-2">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Fleet Failure Risk Distribution
              </h2>
              <p className="text-xs text-slate-400">
                Area 1 gradient boosting risk tier breakdown across total active fleet
              </p>
            </div>
            <Link
              href="/failure-risk"
              className="flex items-center gap-1 text-xs font-semibold text-blue-400 hover:text-blue-300"
            >
              View Queue <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="pt-4">
            {riskLoading ? (
              <div className="h-64 flex items-center justify-center text-xs text-slate-500">
                Loading risk distribution...
              </div>
            ) : (
              <RiskTierBarChart data={chartData} />
            )}
          </div>
        </div>

        {/* Model Governance Quick Overview Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Governance Thresholds
              </h2>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              Approved Phase 5 calibration and proposed Phase 6 automation triggers
            </p>

            <div className="mt-4 space-y-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Area 2 Sensor Anomaly</span>
                  <span className="rounded bg-emerald-950/80 px-1.5 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-800">
                    FROZEN
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  Threshold:{" "}
                  <strong className="text-white font-mono">
                    {governance?.area_2_sensor_anomaly.threshold_value ?? "Loading..."}
                  </strong>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Phase 5 Method B Calibration</div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Area 1 Failure Risk</span>
                  <span className="rounded bg-amber-950/80 px-1.5 py-0.5 text-[10px] font-bold text-amber-400 border border-amber-800">
                    PROPOSED
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  Trigger:{" "}
                  <strong className="text-white font-mono">
                    {governance?.area_1_failure_risk.threshold_value ?? "Loading..."}
                  </strong>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Automated Work Order Threshold</div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Area 3 Demand Surge</span>
                  <span className="rounded bg-amber-950/80 px-1.5 py-0.5 text-[10px] font-bold text-amber-400 border border-amber-800">
                    PROPOSED
                  </span>
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  Surge Warning:{" "}
                  <strong className="text-white font-mono">
                    {governance?.area_3_service_demand.threshold_value !== undefined
                      ? `+${Number(governance.area_3_service_demand.threshold_value) * 100}%`
                      : "Loading..."}
                  </strong>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Capacity Buffer Warning</div>
              </div>
            </div>
          </div>

          <button
            onClick={() => setGovDrawerOpen(true)}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
          >
            <span>Open Governance Registry</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Model Governance Slide-over Drawer */}
      <ModelGovernanceDrawer
        isOpen={govDrawerOpen}
        onClose={() => setGovDrawerOpen(false)}
        governance={governance}
        loading={govLoading}
      />
    </div>
  );
}
