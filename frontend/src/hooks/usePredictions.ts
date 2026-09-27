"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { OverviewMetricsResponse } from "@/types/api";
import {
  FailureRiskPrediction,
  ModelGovernanceResponse,
  SensorAnomalyRecord,
  ServiceDemandForecast,
  WarrantyAnomalyRecord,
} from "@/types/ml";
import { useAuthRole } from "./useAuthRole";

export function useOverviewMetrics() {
  const { apiKey } = useAuthRole();
  const [metrics, setMetrics] = useState<OverviewMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getOverviewMetrics(apiKey);
      setMetrics(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to load overview metrics");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { metrics, loading, error, refetch: fetchMetrics };
}

export function useFailureRisk(filters?: { limit?: number; offset?: number; risk_tier?: string }) {
  const { apiKey } = useAuthRole();
  const [predictions, setPredictions] = useState<FailureRiskPrediction[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRisk = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getFailureRisk(apiKey, filters);
      setPredictions(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to load failure risk predictions");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey, filters?.limit, filters?.offset, filters?.risk_tier]);

  useEffect(() => {
    fetchRisk();
  }, [fetchRisk]);

  return { predictions, total, loading, error, refetch: fetchRisk };
}

export function useSensorAnomalies(filters?: {
  limit?: number;
  offset?: number;
  is_anomaly?: boolean;
  vehicle_id?: string;
}) {
  const { apiKey } = useAuthRole();
  const [records, setRecords] = useState<SensorAnomalyRecord[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [frozenThreshold, setFrozenThreshold] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnomalies = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getSensorAnomalies(apiKey, filters);
      setRecords(res.items);
      setTotal(res.total);
      setFrozenThreshold(res.frozen_threshold);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to load sensor anomalies");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey, filters?.limit, filters?.offset, filters?.is_anomaly, filters?.vehicle_id]);

  useEffect(() => {
    fetchAnomalies();
  }, [fetchAnomalies]);

  return { records, total, frozenThreshold, loading, error, refetch: fetchAnomalies };
}

export function useDemandForecast(filters?: {
  limit?: number;
  offset?: number;
  dealer_id?: string;
  is_surge?: boolean;
}) {
  const { apiKey } = useAuthRole();
  const [forecasts, setForecasts] = useState<ServiceDemandForecast[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchForecast = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getServiceDemandForecast(apiKey, filters);
      setForecasts(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to load demand forecasts");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey, filters?.limit, filters?.offset, filters?.dealer_id, filters?.is_surge]);

  useEffect(() => {
    fetchForecast();
  }, [fetchForecast]);

  return { forecasts, total, loading, error, refetch: fetchForecast };
}

export function useWarrantyAnomalies(filters?: {
  limit?: number;
  offset?: number;
  dealer_id?: string;
}) {
  const { apiKey } = useAuthRole();
  const [records, setRecords] = useState<WarrantyAnomalyRecord[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);

  const fetchWarranty = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const res = await apiClient.getWarrantyAnomalies(apiKey, filters);
      setRecords(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
        setStatus(err.status);
      } else {
        setError("Failed to load warranty anomalies");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey, filters?.limit, filters?.offset, filters?.dealer_id]);

  useEffect(() => {
    fetchWarranty();
  }, [fetchWarranty]);

  return { records, total, loading, error, status, refetch: fetchWarranty };
}

export function useModelGovernance() {
  const { apiKey } = useAuthRole();
  const [governance, setGovernance] = useState<ModelGovernanceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGovernance = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getModelGovernanceStatus(apiKey);
      setGovernance(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("Failed to load model governance status");
      }
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    fetchGovernance();
  }, [fetchGovernance]);

  return { governance, loading, error, refetch: fetchGovernance };
}
