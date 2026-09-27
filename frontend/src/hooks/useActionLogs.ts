"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { ActionAuditRecord } from "@/types/audit";
import { useAuthRole } from "./useAuthRole";

export function useActionLogs(filters?: {
  limit?: number;
  offset?: number;
  entity_type?: string;
  delivery_status?: string;
}) {
  const { apiKey } = useAuthRole();
  const [logs, setLogs] = useState<ActionAuditRecord[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const res = await apiClient.getActionAuditLogs(apiKey, filters);
      setLogs(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
        setStatus(err.status);
      } else {
        setError("Failed to load audit action logs");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey, filters?.limit, filters?.offset, filters?.entity_type, filters?.delivery_status]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return { logs, total, loading, error, status, refetch: fetchLogs };
}
