"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipProps,
} from "recharts";
import { useMetricsHistory } from "@/lib/hooks";
import { useUIStore, type TrendOverviewMetric } from "@/lib/store";
import { getChartColors } from "@/lib/chart-colors";
import type { MetricDataPoint } from "@/types/api";

const METRIC_OPTIONS: { key: TrendOverviewMetric; label: string }[] = [
  { key: "deployment_frequency",    label: "Deployment Frequency" },
  { key: "lead_time_for_changes",   label: "Median Lead Time" },
  { key: "change_failure_rate",     label: "Failure Rate" },
  { key: "mttr_alpha",              label: "MTTR Alpha" },
];

interface ChartColors {
  primary: string;
  leadDev: string;
  leadWait: string;
  grid: string;
  axisLabel: string;
  tooltipBg: string;
  tooltipText: string;
}

function CustomTooltip(
  props: TooltipProps<number, string> & {
    colors: ChartColors;
    unit: string;
    activeMetric: TrendOverviewMetric;
  }
) {
  const { active, colors, unit, activeMetric } = props;
  // Recharts injects payload/label at runtime but types differ by version
  const payload = (props as { payload?: Array<{ dataKey?: string; value?: number }> }).payload;
  const label = (props as { label?: string }).label;
  if (!active || !payload?.length) return null;
  const value = payload[0]?.value;
  const devHours =
    activeMetric === "lead_time_for_changes"
      ? payload.find((p) => p.dataKey === "lead_time_dev_review_hours")?.value
      : undefined;
  const waitHours =
    activeMetric === "lead_time_for_changes"
      ? payload.find((p) => p.dataKey === "lead_time_release_wait_hours")?.value
      : undefined;
  const totalHours =
    activeMetric === "lead_time_for_changes"
      ? (Number(devHours ?? 0) + Number(waitHours ?? 0))
      : undefined;
  return (
    <div
      className="px-3 py-2 rounded-lg text-[11px] font-editorial font-bold shadow-xl"
      style={{ background: colors.tooltipBg, color: colors.tooltipText }}
    >
      <p>{label}</p>
      {activeMetric === "lead_time_for_changes" ? (
        <div className="text-[12px] mt-0.5 space-y-0.5">
          <p>
            Dev/review: {devHours !== undefined ? Number(devHours).toFixed(2) : "—"}{" "}
            <span className="font-normal text-[10px] opacity-70">h</span>
          </p>
          <p>
            Release wait: {waitHours !== undefined ? Number(waitHours).toFixed(2) : "—"}{" "}
            <span className="font-normal text-[10px] opacity-70">h</span>
          </p>
          <p>
            Total lead: {totalHours !== undefined ? totalHours.toFixed(2) : "—"}{" "}
            <span className="font-normal text-[10px] opacity-70">h</span>
          </p>
        </div>
      ) : (
        <p className="text-[13px] mt-0.5">
          {value !== undefined ? Number(value).toFixed(2) : "—"}{" "}
          <span className="font-normal text-[10px] opacity-70">{unit}</span>
        </p>
      )}
    </div>
  );
}

function formatAxisDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const METRIC_UNITS: Record<TrendOverviewMetric, string> = {
  deployment_frequency:  "dep/week",
  lead_time_for_changes: "h",
  change_failure_rate:   "%",
  mttr_alpha:            "min",
};

const METRIC_FOOTNOTES: Record<TrendOverviewMetric, string> = {
  deployment_frequency:
    "Customer-release tags per week. Swimlane below lists release events on the timeline.",
  lead_time_for_changes:
    "Weekly medians from snapshot data, stacked into dev/review and release wait (same release-only MR exclusion as the Median Lead Time KPI when that filter is enabled). Hover a period for segment values and total lead.",
  change_failure_rate:
    "Share of customer releases in the window with at least one linked healthy production bug.",
  mttr_alpha:
    "Median minutes from bug creation to first customer release containing the fix (Critical/Blocker scope per config).",
};

export function TrendChart() {
  const period = useUIStore((s) => s.period);
  const activeMetric = useUIStore((s) => s.trendOverviewMetric);
  const setTrendOverviewMetric = useUIStore((s) => s.setTrendOverviewMetric);
  const { data, isLoading } = useMetricsHistory();
  const { resolvedTheme } = useTheme();
  const [colors, setColors] = useState<ChartColors>({
    primary:     "#4648d4",
    leadDev:     "#4648d4",
    leadWait:    "#7c7ef0",
    grid:        "#edeeef",
    axisLabel:   "#464554",
    tooltipBg:   "#2e3132",
    tooltipText: "#f0f1f2",
  });

  // Re-read CSS vars whenever theme changes
  useEffect(() => {
    const nextColors = getChartColors();
    setColors({
      ...nextColors,
      leadDev: nextColors.primary,
      leadWait: "#8b8df0",
    });
  }, [resolvedTheme]);

  const points: MetricDataPoint[] = data?.data_points ?? [];
  const unit = METRIC_UNITS[activeMetric];

  return (
    <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[40px_40px_40px_0px_rgba(25,28,29,0.04)] dark:shadow-[0px_4px_24px_0px_rgba(0,0,0,0.4)]">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-editorial font-bold tracking-tight text-on-surface">
            Trend Overview
          </h2>
          <p className="text-xs font-editorial text-on-surface-variant uppercase tracking-widest mt-1">
            {period === "30d"
              ? "Last 30 days"
              : period === "quarterly"
              ? "Quarterly"
              : "Yearly"}{" "}
            · {METRIC_OPTIONS.find((m) => m.key === activeMetric)?.label}
          </p>
          <p className="text-[10px] text-on-surface-variant font-editorial leading-snug max-w-xl mt-2">
            {METRIC_FOOTNOTES[activeMetric]}
          </p>
        </div>

        {/* Metric switcher */}
        <div className="flex items-center gap-1 bg-surface-container rounded-lg p-1 flex-wrap">
          {METRIC_OPTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTrendOverviewMetric(key)}
              className={[
                "px-3 py-1 text-[10px] font-editorial font-bold rounded-md transition-all duration-150 uppercase tracking-wider",
                activeMetric === key
                  ? "bg-surface-container-lowest text-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface",
              ].join(" ")}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="h-[300px] w-full">
        {isLoading ? (
          <div className="h-full w-full bg-surface-container animate-pulse rounded-lg" />
        ) : points.length === 0 ? (
          <div className="h-full flex items-center justify-center text-on-surface-variant font-editorial text-sm">
            No data available for this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
              <defs>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={colors.primary} stopOpacity={0.15} />
                  <stop offset="95%" stopColor={colors.primary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="0"
                stroke={colors.grid}
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tickFormatter={formatAxisDate}
                tick={{ fontSize: 10, fill: colors.axisLabel, fontFamily: "Space Grotesk" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: colors.axisLabel, fontFamily: "Space Grotesk" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                content={
                  <CustomTooltip colors={colors} unit={unit} activeMetric={activeMetric} />
                }
                cursor={{ stroke: colors.grid, strokeWidth: 1 }}
              />
              {activeMetric === "lead_time_for_changes" && (
                <Legend
                  wrapperStyle={{ fontSize: "10px", fontFamily: "Space Grotesk" }}
                  formatter={(value) => <span style={{ color: colors.axisLabel }}>{value}</span>}
                />
              )}
              {activeMetric === "lead_time_for_changes" ? (
                <>
                  <Area
                    type="monotone"
                    dataKey="lead_time_dev_review_hours"
                    stackId="leadSplit"
                    name="Dev/review"
                    stroke={colors.leadDev}
                    strokeWidth={2}
                    fill={colors.leadDev}
                    fillOpacity={0.22}
                    dot={{ r: 2.5, fill: colors.leadDev, stroke: colors.leadDev, strokeWidth: 0 }}
                    activeDot={{ r: 5, fill: colors.leadDev, strokeWidth: 0 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="lead_time_release_wait_hours"
                    stackId="leadSplit"
                    name="Release wait"
                    stroke={colors.leadWait}
                    strokeWidth={2}
                    fill={colors.leadWait}
                    fillOpacity={0.28}
                    dot={{ r: 2.5, fill: colors.leadWait, stroke: colors.leadWait, strokeWidth: 0 }}
                    activeDot={{ r: 5, fill: colors.leadWait, strokeWidth: 0 }}
                  />
                </>
              ) : (
                <Area
                  type="monotone"
                  dataKey={activeMetric}
                  stroke={colors.primary}
                  strokeWidth={2.5}
                  fill="url(#areaGradient)"
                  dot={{ r: 2.5, fill: colors.primary, stroke: colors.primary, strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: colors.primary, strokeWidth: 0 }}
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
