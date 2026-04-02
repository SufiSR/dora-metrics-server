import type { PeriodType } from "@/types/api";

export const queryKeys = {
  metricsCurrent: (period: PeriodType) =>
    ["metrics", "current", period] as const,

  metricsHistory: (period: PeriodType) =>
    ["metrics", "history", period] as const,

  syncStatus: () => ["sync", "status"] as const,

  repositories: () => ["repositories"] as const,
} as const;
