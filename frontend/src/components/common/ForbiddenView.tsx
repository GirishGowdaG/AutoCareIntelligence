"use client";

import React from "react";
import { ShieldAlert, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useAuthRole } from "@/hooks/useAuthRole";
import { UserRole } from "@/types/api";

interface ForbiddenViewProps {
  requiredRole?: string;
  resourceName?: string;
}

export function ForbiddenView({
  requiredRole = "Admin",
  resourceName = "this module",
}: ForbiddenViewProps) {
  const { role, setRole } = useAuthRole();

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center p-6">
      <div className="rounded-full bg-rose-950/60 p-4 border border-rose-800 text-rose-400">
        <ShieldAlert className="h-10 w-10" />
      </div>
      <h2 className="mt-4 text-xl font-bold tracking-tight text-white">403 — Access Forbidden</h2>
      <p className="mt-2 max-w-md text-sm text-slate-400">
        Your current active persona (<span className="font-semibold text-slate-200">{role}</span>) does
        not have RBAC authorization to access {resourceName}.
      </p>
      <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-xs text-slate-400">
        Required Permission: <span className="font-medium text-amber-300">{requiredRole}</span>
      </div>

      <div className="mt-6 flex items-center gap-3">
        <Link
          href="/overview"
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Overview
        </Link>
        {role !== "Admin" && (
          <button
            onClick={() => setRole("Admin" as UserRole)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 transition"
          >
            Switch to Admin Persona
          </button>
        )}
      </div>
    </div>
  );
}
