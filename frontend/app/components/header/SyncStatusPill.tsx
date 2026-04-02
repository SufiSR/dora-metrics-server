"use client";

import { useSyncStatus } from "@/lib/hooks";
import { formatDistanceToNow } from "@/lib/date-utils";

export function SyncStatusPill() {
  const { data, isError } = useSyncStatus();

  if (isError || !data?.last_sync_at) {
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

  const ageMs = Date.now() - new Date(data.last_sync_at).getTime();
  const isStale = ageMs > 1000 * 60 * 60 * 26; // >26h
  const isFailed =
    data.status === "FAILED" || data.status === "PARTIAL_FAILURE";

  const colorClass =
    isStale || isFailed
      ? "bg-error-container text-on-error-container"
      : "bg-surface-container-low text-primary";

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full border-b border-primary/10 ${colorClass}`}
      title={`Last sync: ${data.last_sync_at}`}
    >
      <span
        className={[
          "material-symbols-outlined text-sm",
          data.status === "RUNNING" ? "animate-spin" : "",
        ].join(" ")}
      >
        {data.status === "RUNNING" ? "sync" : isFailed ? "sync_problem" : "sync"}
      </span>
      <span className="text-[10px] font-editorial uppercase tracking-wider font-bold">
        {data.status === "RUNNING"
          ? "Syncing…"
          : `Synced ${formatDistanceToNow(data.last_sync_at)}`}
      </span>
    </div>
  );
}
