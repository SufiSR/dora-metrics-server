"use client";

import { useSyncStatus } from "@/lib/hooks";
import { formatDateTime, isOlderThan } from "@/lib/date-utils";

const STALE_THRESHOLD_MS = 1000 * 60 * 60 * 26; // 26 hours

export function StaleBanner() {
  const { data, isError, isLoading } = useSyncStatus();

  if (isLoading) return null;

  const last = data?.last_sync;
  const status = data?.pipeline_in_progress ? "RUNNING" : last?.status;
  const isFailed = status === "FAILED";
  const isPartial = status === "PARTIAL_FAILURE";
  const lastOkAt =
    data?.last_successful_sync_at ?? last?.finished_at ?? null;
  const isStale = lastOkAt
    ? isOlderThan(lastOkAt, STALE_THRESHOLD_MS)
    : false;
  const errDetail = last?.error_message?.trim() || null;

  if (!isFailed && !isPartial && !isStale && !isError) return null;

  const message = isError
    ? "Unable to retrieve sync status."
    : isFailed
      ? `Last sync failed${errDetail ? `: ${errDetail}` : "."}`
      : isPartial
        ? `Last sync completed with partial failures${errDetail ? `: ${errDetail}` : "."}`
        : `Data may be stale — last successful sync was ${
            lastOkAt ? formatDateTime(lastOkAt) : "unknown"
          }.`;

  return (
    <div
      role="alert"
      className="flex items-center gap-3 px-4 py-3 rounded-xl bg-error-container text-on-error-container text-xs font-editorial"
    >
      <span className="material-symbols-outlined text-base shrink-0">warning</span>
      <span>{message}</span>
    </div>
  );
}
