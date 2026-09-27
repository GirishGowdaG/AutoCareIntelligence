"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { VehicleDetail, VehicleSummary } from "@/types/vehicles";
import { useAuthRole } from "./useAuthRole";

export function useVehicles(filters?: { limit?: number; offset?: number; make?: string; state?: string }) {
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
  }, [apiKey, filters?.limit, filters?.offset, filters?.make, filters?.state]);

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
      const data = await apiClient.getVehicleDetail(vehicleId, apiKey);
      setVehicle(data);
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
