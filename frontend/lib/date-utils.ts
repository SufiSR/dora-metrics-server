/**
 * Returns a human-readable relative time string (e.g. "2m ago", "3h ago").
 * Used for sync status pill.
 */
export function formatDistanceToNow(isoDateString: string): string {
  const ms = Date.now() - new Date(isoDateString).getTime();
  const seconds = Math.floor(ms / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/**
 * Returns true if the ISO date string is older than the given threshold in ms.
 */
export function isOlderThan(isoDateString: string, thresholdMs: number): boolean {
  return Date.now() - new Date(isoDateString).getTime() > thresholdMs;
}

/**
 * Formats an ISO date string as a short locale date + time.
 */
export function formatDateTime(isoDateString: string): string {
  return new Date(isoDateString).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}
