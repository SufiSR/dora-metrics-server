import type { DoraLevel } from "@/types/api";

interface DoraBadgeProps {
  level: DoraLevel;
}

const BADGE_STYLES: Record<DoraLevel, string> = {
  ELITE:   "bg-primary text-on-primary",
  HIGH:    "bg-secondary-container text-on-secondary-container",
  MEDIUM:  "bg-tertiary-fixed text-on-tertiary-fixed-variant",
  LOW:     "bg-error-container text-on-error-container",
  UNKNOWN: "bg-surface-container text-on-surface-variant",
};

export function DoraBadge({ level }: DoraBadgeProps) {
  return (
    <span
      className={[
        "text-[10px] px-2 py-0.5 rounded-md font-editorial font-bold uppercase tracking-widest",
        BADGE_STYLES[level] ?? BADGE_STYLES.UNKNOWN,
      ].join(" ")}
    >
      {level}
    </span>
  );
}
