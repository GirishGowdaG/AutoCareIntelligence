import React from "react";
import { AlertCircle, Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
}

export function EmptyState({
  title = "No data found",
  description = "No records match the selected filters or query parameters.",
  icon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
      <div className="rounded-full bg-slate-800 p-3 text-slate-400">
        {icon || <Inbox className="h-6 w-6" />}
      </div>
      <h3 className="mt-4 text-sm font-semibold text-slate-200">{title}</h3>
      <p className="mt-1 text-xs text-slate-400 max-w-sm">{description}</p>
    </div>
  );
}

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-rose-900/80 bg-rose-950/40 p-4 text-rose-200">
      <div className="flex items-center gap-3">
        <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
        <span className="text-xs font-medium">{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-rose-900/60 px-3 py-1.5 text-xs font-semibold text-rose-100 hover:bg-rose-800 transition"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-4 animate-pulse">
      <div className="h-8 bg-slate-800 rounded mb-4" />
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
            {Array.from({ length: cols }).map((_, c) => (
              <div key={c} className="h-6 bg-slate-800/60 rounded" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
