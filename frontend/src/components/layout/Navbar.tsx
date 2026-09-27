"use client";

import React, { useState, useEffect } from "react";
import {
  Bell,
  Key,
  Activity,
  Shield,
  Check,
  ChevronDown,
} from "lucide-react";
import { useAuthRole } from "@/hooks/useAuthRole";
import { UserRole } from "@/types/api";
import { apiClient } from "@/lib/api-client";

interface NavbarProps {
  onToggleAlerts: () => void;
  unreadCount?: number;
  sseStatus?: string;
  sseSource?: string | null;
}

export function Navbar({ onToggleAlerts, unreadCount = 0, sseStatus, sseSource }: NavbarProps) {
  const { role, setRole, apiKey, setApiKey } = useAuthRole();
  const [healthStatus, setHealthStatus] = useState<string>("checking");
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [keyInput, setKeyInput] = useState(apiKey);
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getHealth()
      .then((res) => {
        if (isMounted) setHealthStatus(res.status);
      })
      .catch(() => {
        if (isMounted) setHealthStatus("error");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSaveKey = () => {
    setApiKey(keyInput.trim());
    setShowKeyModal(false);
  };

  const roles: { role: UserRole; label: string; desc: string }[] = [
    { role: "Admin", label: "Admin", desc: "Full executive & audit privileges" },
    { role: "DealerServiceManager", label: "Dealer Service Manager", desc: "Operations & demand forecast" },
    { role: "FleetAnalyst", label: "Fleet Analyst", desc: "Analytics & warranty audit" },
  ];

  return (
    <>
      <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 backdrop-blur">
        {/* Left: Branding & Health */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 font-bold text-white shadow-md shadow-blue-600/20">
              AC
            </div>
            <div>
              <span className="font-bold tracking-tight text-white">AutoCare Intelligence</span>
              <span className="ml-2 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700">
                v1.0.0
              </span>
            </div>
          </div>

          {/* System Health Indicator */}
          <div className="hidden items-center gap-2 rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1 text-xs sm:flex">
            <span
              className={`h-2 w-2 rounded-full ${
                healthStatus === "healthy"
                  ? "bg-emerald-400 animate-pulse"
                  : healthStatus === "degraded"
                  ? "bg-amber-400"
                  : "bg-rose-400"
              }`}
            />
            <span className="text-slate-300 capitalize font-medium">{healthStatus}</span>
          </div>

          {/* SSE Stream Source Badge */}
          {sseStatus === "CONNECTED" && (
            <div className="hidden lg:flex items-center gap-1.5 rounded-full border border-blue-900/60 bg-blue-950/40 px-3 py-1 text-[11px] font-medium text-blue-300">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-ping" />
              {sseSource === "kafka" ? "[LIVE: Kafka Telemetry]" : "[DEMO MODE: Synthetic Telemetry]"}
            </div>
          )}
        </div>

        {/* Right: Persona Switcher, API Key, Alert Center */}
        <div className="flex items-center gap-3">
          {/* Persona Switcher Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowRoleDropdown(!showRoleDropdown)}
              className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-slate-700 transition"
            >
              <Shield className="h-3.5 w-3.5 text-blue-400" />
              <span>Persona: <strong className="text-white">{role}</strong></span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>

            {showRoleDropdown && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl border border-slate-800 bg-slate-900 p-2 shadow-xl z-50">
                <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Select Active Persona
                </div>
                {roles.map((r) => (
                  <button
                    key={r.role}
                    onClick={() => {
                      setRole(r.role);
                      setShowRoleDropdown(false);
                    }}
                    className={`flex w-full items-start justify-between rounded-lg p-2 text-left transition ${
                      role === r.role ? "bg-blue-950/60 text-blue-200 border border-blue-800/60" : "hover:bg-slate-800 text-slate-300"
                    }`}
                  >
                    <div>
                      <div className="text-xs font-semibold">{r.label}</div>
                      <div className="text-[11px] text-slate-400">{r.desc}</div>
                    </div>
                    {role === r.role && <Check className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* API Key Config Button */}
          <button
            onClick={() => setShowKeyModal(true)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              apiKey
                ? "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700"
                : "border-amber-700/80 bg-amber-950/60 text-amber-200 animate-pulse hover:bg-amber-900/60"
            }`}
          >
            <Key className="h-3.5 w-3.5 text-amber-400" />
            <span className="hidden sm:inline">{apiKey ? "API Key Set" : "Configure API Key"}</span>
          </button>

          {/* Alert Center Drawer Trigger */}
          <button
            onClick={onToggleAlerts}
            className="relative rounded-lg border border-slate-800 bg-slate-900 p-2 text-slate-300 hover:border-slate-700 hover:text-white transition"
            aria-label="Toggle Alert Center"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-600 text-[10px] font-bold text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>
        </div>
      </header>

      {/* API Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-950/80 p-2 text-blue-400 border border-blue-800">
                <Key className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Configure Active API Key</h3>
                <p className="text-xs text-slate-400">
                  Operates in demo mode with session storage. Never stored in source code.
                </p>
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                X-API-Key for {role}
              </label>
              <input
                type="password"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                placeholder="Enter authorized API key..."
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
              <p className="mt-1 text-[11px] text-slate-400">
                For demo execution with local backend, use the respective secret key configured in your backend environment.
              </p>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setShowKeyModal(false)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveKey}
                className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-500"
              >
                Save Key
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
