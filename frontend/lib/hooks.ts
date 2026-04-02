"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./api-client";
import { queryKeys } from "./query-keys";
import { useUIStore } from "./store";

export function useMetricsCurrent() {
  const period = useUIStore((s) => s.period);
  return useQuery({
    queryKey: queryKeys.metricsCurrent(period),
    queryFn: () => apiClient.getMetricsCurrent(period),
  });
}

export function useMetricsHistory() {
  const period = useUIStore((s) => s.period);
  return useQuery({
    queryKey: queryKeys.metricsHistory(period),
    queryFn: () => apiClient.getMetricsHistory(period),
  });
}

export function useSyncStatus() {
  return useQuery({
    queryKey: queryKeys.syncStatus(),
    queryFn: () => apiClient.getSyncStatus(),
    staleTime: 1000 * 60 * 5, // sync status refreshes more frequently (5 min)
    refetchInterval: 1000 * 60 * 5,
  });
}

export function useRepositories() {
  return useQuery({
    queryKey: queryKeys.repositories(),
    queryFn: () => apiClient.getRepositories(),
  });
}
