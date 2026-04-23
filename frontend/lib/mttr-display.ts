/** Display helpers for MTTR Alpha (minutes). */

export function formatMttrMinutes(minutes: number | null): string {
  if (minutes === null) return "—";
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 24 * 60) return `${(minutes / 60).toFixed(1)}h`;
  return `${(minutes / (24 * 60)).toFixed(1)}d`;
}

/** Prefer hours when over 60m; include raw minutes in tooltip-style copy. */
export function formatMttrMinutesDetail(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  if (minutes < 1440) return `${(minutes / 60).toFixed(1)} h (${minutes} min)`;
  return `${(minutes / 1440).toFixed(1)} d (${minutes} min)`;
}
