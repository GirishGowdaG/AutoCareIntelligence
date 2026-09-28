"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { VehicleDetail, VehicleSummary } from "@/types/vehicles";
import { useAuthRole } from "./useAuthRole";

export function useVehicles(filters?: { limit?: number; offset?: number; status?: string }) {
  const { apiKey } = useAuthRole();
  const [vehicles, setVehicles] = useState<VehicleSummary[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVehicles = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getVehicles(apiKey, filters);
      setVehicles(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to fetch vehicles");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey, filters?.limit, filters?.offset, filters?.status]);

  useEffect(() => {
    fetchVehicles();
  }, [fetchVehicles]);

  return { vehicles, total, loading, error, refetch: fetchVehicles };
}

export function useVehicleDetail(vehicleId: string) {
  const { apiKey } = useAuthRole();
  const [vehicle, setVehicle] = useState<VehicleDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!apiKey || !vehicleId) return;
    setLoading(true);
    setError(null);
    try {
      const [spec, diagRes] = await Promise.all([
        apiClient.getVehicleDetail(vehicleId, apiKey),
        apiClient
          .getVehicleDiagnostics(vehicleId, apiKey)
          .catch(() => ({ total_records: 0, diagnostics: [], vehicle_id: vehicleId })),
      ]);
      setVehicle({
        ...spec,
        diagnostics: diagRes.diagnostics || [],
      });
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to fetch vehicle diagnostics");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey, vehicleId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  return { vehicle, loading, error, refetch: fetchDetail };
}
