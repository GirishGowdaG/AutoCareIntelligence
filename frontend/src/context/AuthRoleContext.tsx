"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserRole } from "@/types/api";

interface AuthRoleContextType {
  role: UserRole;
  apiKey: string;
  setRole: (role: UserRole) => void;
  setApiKey: (key: string) => void;
  canAccessWarranty: boolean;
  canAccessAuditLogs: boolean;
  isConfigured: boolean;
}

const AuthRoleContext = createContext<AuthRoleContextType | undefined>(undefined);

const ROLE_STORAGE_KEY = "autocare_active_role";
const KEY_STORAGE_KEY = "autocare_active_key";

export function AuthRoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<UserRole>("Admin");
  const [apiKey, setApiKeyState] = useState<string>("");
  const [initialized, setInitialized] = useState<boolean>(false);

  useEffect(() => {
    try {
      const storedRole = sessionStorage.getItem(ROLE_STORAGE_KEY) as UserRole | null;
      const storedKey = sessionStorage.getItem(KEY_STORAGE_KEY);
      if (storedRole && ["Admin", "DealerServiceManager", "FleetAnalyst"].includes(storedRole)) {
        setRoleState(storedRole);
      }
      if (storedKey) {
        setApiKeyState(storedKey);
      }
    } catch {
      // sessionStorage may fail in some environments
    } finally {
      setInitialized(true);
    }
  }, []);

  const setRole = (newRole: UserRole) => {
    setRoleState(newRole);
    try {
      sessionStorage.setItem(ROLE_STORAGE_KEY, newRole);
    } catch {
      // ignore
    }
  };

  const setApiKey = (newKey: string) => {
    setApiKeyState(newKey);
    try {
      sessionStorage.setItem(KEY_STORAGE_KEY, newKey);
    } catch {
      // ignore
    }
  };

  const canAccessWarranty = role === "Admin" || role === "FleetAnalyst";
  const canAccessAuditLogs = role === "Admin";
  const isConfigured = Boolean(apiKey && apiKey.trim().length > 0);

  if (!initialized) {
    return null;
  }

  return (
    <AuthRoleContext.Provider
      value={{
        role,
        apiKey,
        setRole,
        setApiKey,
        canAccessWarranty,
        canAccessAuditLogs,
        isConfigured,
      }}
    >
      {children}
    </AuthRoleContext.Provider>
  );
}

export function useAuthRole(): AuthRoleContextType {
  const ctx = useContext(AuthRoleContext);
  if (!ctx) {
    throw new Error("useAuthRole must be used within an AuthRoleProvider");
  }
  return ctx;
}
