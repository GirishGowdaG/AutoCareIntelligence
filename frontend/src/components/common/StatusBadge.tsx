import React from "react";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
  className?: string;
}

export function StatusBadge({ status, size = "md", className }: StatusBadgeProps) {
  if (!status) return null;
  const norm = status.toUpperCase();

  let styles = "bg-slate-800 text-slate-300 border-slate-700";

  // Risk tiers
  if (norm === "CRITICAL") {
    styles = "bg-rose-950/80 text-rose-300 border-rose-800/80";
  } else if (norm === "HIGH") {
    styles = "bg-amber-950/80 text-amber-300 border-amber-800/80";
  } else if (norm === "MEDIUM") {
    styles = "bg-yellow-950/80 text-yellow-300 border-yellow-800/80";
  } else if (norm === "LOW") {
    styles = "bg-emerald-950/80 text-emerald-300 border-emerald-800/80";
  }
  // Delivery status
  else if (norm === "DELIVERED") {
    styles = "bg-emerald-950/80 text-emerald-300 border-emerald-800/80";
  } else if (norm === "MOCK_LOGGED") {
    styles = "bg-blue-950/80 text-blue-300 border-blue-800/80";
  } else if (norm === "FAILED") {
    styles = "bg-rose-950/80 text-rose-300 border-rose-800/80";
  }
  // Boolean or flags
  else if (norm === "SURGE" || norm === "ANOMALY" || norm === "OUTLIER" || norm === "AUDIT REQUIRED") {
    styles = "bg-rose-950/80 text-rose-300 border-rose-800/80";
  } else if (norm === "NORMAL" || norm === "NOMINAL" || norm === "PASS") {
    styles = "bg-emerald-950/80 text-emerald-300 border-emerald-800/80";
  } else if (norm === "HEALTHY" || norm === "CONNECTED") {
    styles = "bg-emerald-950/80 text-emerald-300 border-emerald-800/80";
  } else if (norm === "DEGRADED") {
    styles = "bg-amber-950/80 text-amber-300 border-amber-800/80";
  }

  const sizeStyles = {
    sm: "px-2 py-0.5 text-[11px]",
    md: "px-2.5 py-1 text-xs",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-semibold border uppercase tracking-wider",
        sizeStyles[size],
        styles,
        className
      )}
    >
      {status}
    </span>
  );
}
