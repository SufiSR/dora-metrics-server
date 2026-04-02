"use client";

import { useSyncStatus } from "@/lib/hooks";
import { formatDistanceToNow } from "@/lib/date-utils";
import type { SyncRunStatus, SyncStatusResponse } from "@/types/api";

function resolveSyncDisplay(data: SyncStatusResponse): {
  status: SyncRunStatus;
  lastSyncAt: string | null;
  details: string | null;
} {
  if (data.pipeline_in_progress) {
    return {
      status: "RUNNING",
      lastSyncAt: data.pipeline_run_started_at,
      details: null,
    };
  }
  const last = data.last_sync;
  const lastSyncAt =
    data.last_successful_sync_at ??
    last?.finished_at ??
    last?.started_at ??
    null;
  const status = (last?.status as SyncRunStatus) ?? "FAILED";
  return {
    status,
    lastSyncAt,
    details: last?.error_message ?? null,
  };
}

export function SyncStatusPill() {
  const { data, isError } = useSyncStatus();

  if (isError || !data) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-error-container">
        <span className="material-symbols-outlined text-sm text-on-error-container">
          sync_problem
        </span>
        <span className="text-[10px] font-editorial uppercase tracking-wider font-bold text-on-error-container">
          Sync Unknown
        </span>
      </div>
    );
  }

  const { status, lastSyncAt, details } = resolveSyncDisplay(data);

  if (status === "RUNNING") {
    return (
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-full border-b border-primary/10 bg-surface-container-low text-primary"
        title={
          lastSyncAt
            ? `Pipeline started ${lastSyncAt}`
            : "Synchronization in progress"
        }
      >
        <span className="material-symbols-outlined text-sm animate-spin">sync</span>
        <span className="text-[10px] font-editorial uppercase tracking-wider font-bold">
          Syncing…
        </span>
      </div>
    );
  }

  if (!lastSyncAt) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-error-container">
        <span className="material-symbols-outlined text-sm text-on-error-container">
          sync_problem
        </span>
        <span className="text-[10px] font-editorial uppercase tracking-wider font-bold text-on-error-container">
          Sync Unknown
        </span>
      </div>
    );
  }

  const ageMs = Date.now() - new Date(lastSyncAt).getTime();
  const isStale = ageMs > 1000 * 60 * 60 * 26; // >26h
  const isFailed = status === "FAILED" || status === "PARTIAL_FAILURE";

  const colorClass =
    isStale || isFailed
      ? "bg-error-container text-on-error-container"
      : "bg-surface-container-low text-primary";

  const titleParts = [`Last sync: ${lastSyncAt}`];
  if (details) titleParts.push(details);

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full border-b border-primary/10 ${colorClass}`}
      title={titleParts.join(" — ")}
    >
      <span
        className={[
          "material-symbols-outlined text-sm",
          isFailed ? "sync_problem" : "sync",
        ].join(" ")}
      >
        {isFailed ? "sync_problem" : "sync"}
      </span>
      <span className="text-[10px] font-editorial uppercase tracking-wider font-bold">
        {isFailed
          ? status === "PARTIAL_FAILURE"
            ? "Partial sync"
            : "Sync failed"
          : `Synced ${formatDistanceToNow(lastSyncAt)}`}
      </span>
    </div>
  );
}
