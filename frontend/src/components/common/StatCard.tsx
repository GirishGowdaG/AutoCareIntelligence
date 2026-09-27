import React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  variant?: "default" | "critical" | "warning" | "success" | "info";
  badge?: string;
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  badge,
  className,
}: StatCardProps) {
  const variantStyles = {
    default: "border-slate-800 bg-slate-900/60 text-slate-100",
    critical: "border-rose-900/60 bg-rose-950/20 text-rose-200",
    warning: "border-amber-900/60 bg-amber-950/20 text-amber-200",
    success: "border-emerald-900/60 bg-emerald-950/20 text-emerald-200",
    info: "border-blue-900/60 bg-blue-950/20 text-blue-200",
  };

  const iconStyles = {
    default: "text-slate-400 bg-slate-800/80",
    critical: "text-rose-400 bg-rose-900/40",
    warning: "text-amber-400 bg-amber-900/40",
    success: "text-emerald-400 bg-emerald-900/40",
    info: "text-blue-400 bg-blue-900/40",
  };

  return (
    <div
      className={cn(
        "relative rounded-xl border p-5 shadow-sm transition-all hover:border-slate-700",
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && (
          <div className={cn("rounded-lg p-2", iconStyles[variant])}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-white">{value}</span>
        {badge && (
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-300 border border-slate-700">
            {badge}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
}
