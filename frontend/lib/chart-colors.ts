"use client";

/**
 * Reads the current resolved CSS custom property values so Recharts
 * (which doesn't understand CSS variables) gets the correct colors for
 * whichever theme is currently active.
 *
 * Must be called inside a useEffect or event handler (client-side only).
 */
export function getChartColors(): {
  primary: string;
  grid: string;
  axisLabel: string;
  tooltipBg: string;
  tooltipText: string;
} {
  const style = getComputedStyle(document.documentElement);
  const get = (name: string) => style.getPropertyValue(name).trim();

  return {
    primary:    get("--color-primary")    || "#4648d4",
    grid:       get("--color-surface-container") || "#edeeef",
    axisLabel:  get("--color-on-surface-variant") || "#464554",
    tooltipBg:  get("--color-inverse-surface") || "#2e3132",
    tooltipText: get("--color-inverse-on-surface") || "#f0f1f2",
  };
}
