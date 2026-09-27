"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Truck,
  AlertTriangle,
  Activity,
  TrendingUp,
  FileCheck2,
  ScrollText,
  Lock,
} from "lucide-react";
import { useAuthRole } from "@/hooks/useAuthRole";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const { role, canAccessWarranty, canAccessAuditLogs } = useAuthRole();

  const navigation = [
    {
      name: "Overview",
      href: "/overview",
      icon: LayoutDashboard,
      allowed: true,
    },
    {
      name: "Fleet Health",
      href: "/vehicles",
      icon: Truck,
      allowed: true,
    },
    {
      name: "Failure Risk",
      href: "/failure-risk",
      icon: AlertTriangle,
      allowed: true,
    },
    {
      name: "Sensor Anomalies",
      href: "/sensor-anomalies",
      icon: Activity,
      allowed: true,
    },
    {
      name: "Demand Forecast",
      href: "/demand-forecast",
      icon: TrendingUp,
      allowed: true,
    },
    {
      name: "Warranty Audit",
      href: "/warranty-audit",
      icon: FileCheck2,
      allowed: canAccessWarranty,
      restrictedMsg: "Admin / Analyst Only",
    },
    {
      name: "Automation Logs",
      href: "/audit-logs",
      icon: ScrollText,
      allowed: canAccessAuditLogs,
      restrictedMsg: "Admin Only",
    },
  ];

  return (
    <aside className="hidden md:flex w-64 flex-col border-r border-slate-800 bg-slate-950 p-4">
      <div className="mb-4 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Analytical Modules
      </div>

      <nav className="flex-1 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/overview" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition",
                isActive
                  ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              )}
            >
              <div className="flex items-center gap-3">
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition",
                    isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"
                  )}
                />
                <span>{item.name}</span>
              </div>

              {!item.allowed && (
                <span className="flex items-center gap-1 rounded bg-slate-900 px-1.5 py-0.5 text-[10px] text-slate-400 border border-slate-800" title={item.restrictedMsg}>
                  <Lock className="h-3 w-3 text-amber-500" />
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 mt-auto">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Governance Boundary
        </div>
        <p className="mt-1 text-[11px] text-slate-400 leading-relaxed">
          Read-only PostgreSQL access. ML models and thresholds are immutable at runtime.
        </p>
      </div>
    </aside>
  );
}
