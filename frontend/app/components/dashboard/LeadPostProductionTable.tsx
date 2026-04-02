"use client";

import { useMetricsCurrent } from "@/lib/hooks";
import { DoraBadge } from "./DoraBadge";

export function LeadPostProductionTable() {
  const { data, isLoading } = useMetricsCurrent();

  const leadPost = data?.lead_post_production;
  const loggedVsCalendar = data?.logged_vs_calendar;

  return (
    <div className="bg-surface-container-lowest p-8 rounded-xl shadow-[40px_40px_40px_0px_rgba(25,28,29,0.04)] dark:shadow-[0px_4px_24px_0px_rgba(0,0,0,0.4)]">
      <div className="mb-6">
        <h2 className="text-lg font-editorial font-bold tracking-tight text-on-surface">
          Extended Metrics
        </h2>
        <p className="text-xs font-editorial text-on-surface-variant uppercase tracking-widest mt-1">
          Phase 1.5 — partial data, full charts in next phase
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-12 bg-surface-container animate-pulse rounded-lg"
            />
          ))}
        </div>
      ) : !leadPost && !loggedVsCalendar ? (
        <div className="flex items-center gap-3 py-6 text-on-surface-variant text-sm font-editorial">
          <span className="material-symbols-outlined text-outline">hourglass_empty</span>
          <span>
            Data pending — Lead Post-Production and worklog metrics will appear
            here once the backend provides them.
          </span>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] font-editorial uppercase tracking-widest text-outline">
              <th className="text-left pb-3">Metric</th>
              <th className="text-right pb-3">Value</th>
              <th className="text-right pb-3">DORA Level</th>
            </tr>
          </thead>
          <tbody className="space-y-2">
            {leadPost && (
              <tr className="hover:bg-surface-container-low transition-colors">
                <td className="py-3 text-on-surface">Lead Post-Production</td>
                <td className="py-3 text-right font-editorial font-bold text-on-surface">
                  {leadPost.value !== null
                    ? `${leadPost.value.toFixed(1)} ${leadPost.unit}`
                    : "—"}
                </td>
                <td className="py-3 text-right">
                  <DoraBadge level={leadPost.dora_level} />
                </td>
              </tr>
            )}
            {loggedVsCalendar && (
              <tr className="hover:bg-surface-container-low transition-colors">
                <td className="py-3 text-on-surface">
                  Logged vs. Calendar Time
                </td>
                <td className="py-3 text-right font-editorial font-bold text-on-surface">
                  {loggedVsCalendar.logged_hours !== null
                    ? `${loggedVsCalendar.logged_hours}h logged`
                    : "—"}
                  {loggedVsCalendar.calendar_days !== null && (
                    <span className="text-on-surface-variant font-normal ml-1">
                      / {loggedVsCalendar.calendar_days}d calendar
                    </span>
                  )}
                </td>
                <td className="py-3 text-right">—</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
