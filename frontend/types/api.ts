// ─────────────────────────────────────────────────────────────────────────────
// API response types — aligned with backend OpenAPI schema (DEVOPS-440)
// ─────────────────────────────────────────────────────────────────────────────

export type DoraLevel = "ELITE" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
export type SyncStatus = "SUCCESS" | "PARTIAL_FAILURE" | "FAILED" | "RUNNING";
export type PeriodType = "30d" | "quarterly" | "yearly";

// ── Metrics current ──────────────────────────────────────────────────────────

export interface MetricValue {
  value: number | null;
  unit: string;
  dora_level: DoraLevel;
  trend_pct: number | null;
}

export interface MetricsCurrentResponse {
  generated_at: string; // ISO 8601
  period_label: string;
  deployment_frequency: MetricValue;
  lead_time_for_changes: MetricValue;
  change_failure_rate: MetricValue;
  mttr_alpha: MetricValue;
  lead_post_production?: MetricValue;
  logged_vs_calendar?: {
    logged_hours: number | null;
    calendar_days: number | null;
  };
}

// ── Metrics history ──────────────────────────────────────────────────────────

export interface MetricDataPoint {
  date: string; // ISO 8601 date
  deployment_frequency: number | null;
  lead_time_for_changes: number | null;
  change_failure_rate: number | null;
  mttr_alpha: number | null;
}

export interface MetricsHistoryResponse {
  period: PeriodType;
  data_points: MetricDataPoint[];
}

// ── Sync status ──────────────────────────────────────────────────────────────

export interface SyncStatusResponse {
  last_sync_at: string | null;
  status: SyncStatus;
  next_sync_at: string | null;
  details: string | null;
}

// ── Repositories ─────────────────────────────────────────────────────────────

export interface RepositoryMetrics {
  repository_path: string;
  deployment_frequency: number | null;
  lead_time_for_changes: number | null;
  change_failure_rate: number | null;
  mttr_alpha: number | null;
  dora_level: DoraLevel;
}

export interface RepositoriesResponse {
  repositories: RepositoryMetrics[];
}

// ── Error response ────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
  status: number;
}
