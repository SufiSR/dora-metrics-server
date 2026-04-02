"use client";

import { useSyncStatus } from "@/lib/hooks";
import { formatDateTime, isOlderThan } from "@/lib/date-utils";

const STALE_THRESHOLD_MS = 1000 * 60 * 60 * 26; // 26 hours

export function StaleBanner() {
  const { data, isError, isLoading } = useSyncStatus();

  if (isLoading) return null;

  const isFailed  = data?.status === "FAILED";
  const isPartial = data?.status === "PARTIAL_FAILURE";
  const isStale   = data?.last_sync_at
    ? isOlderThan(data.last_sync_at, STALE_THRESHOLD_MS)
    : false;

  if (!isFailed && !isPartial && !isStale && !isError) return null;

  const message = isError
    ? "Unable to retrieve sync status."
    : isFailed
    ? `Last sync failed${data?.details ? `: ${data.details}` : "."}`
    : isPartial
    ? `Last sync completed with partial failures${data?.details ? `: ${data.details}` : "."}`
    : `Data may be stale — last successful sync was ${
        data?.last_sync_at ? formatDateTime(data.last_sync_at) : "unknown"
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
