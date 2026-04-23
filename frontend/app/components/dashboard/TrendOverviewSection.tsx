"use client";

import { useUIStore } from "@/lib/store";
import { CfrReleaseDrilldownPanel } from "./CfrReleaseDrilldownPanel";
import { DeploymentSwimlaneTimeline } from "./DeploymentSwimlaneTimeline";
import { MttrAlphaDrilldownPanel } from "./MttrAlphaDrilldownPanel";
import { MttrAlphaTimeToFixSpread } from "./MttrAlphaTimeToFixSpread";
import { ReleaseDrilldownPanel } from "./ReleaseDrilldownPanel";
import { TrendChart } from "./TrendChart";

/**
 * TrendChart metric switch drives the contextual block below: swimlane, release drill-down,
 * CFR failed releases, or (for MTTR Alpha) time-to-fix spread + incident drill-down.
 */
export function TrendOverviewSection() {
  const trendMetric = useUIStore((s) => s.trendOverviewMetric);

  return (
    <div className="space-y-10">
      <TrendChart />
      {trendMetric === "deployment_frequency" && <DeploymentSwimlaneTimeline />}
      {trendMetric === "lead_time_for_changes" && <ReleaseDrilldownPanel />}
      {trendMetric === "change_failure_rate" && <CfrReleaseDrilldownPanel />}
      {trendMetric === "mttr_alpha" && (
        <>
          <MttrAlphaTimeToFixSpread />
          <MttrAlphaDrilldownPanel />
        </>
      )}
    </div>
  );
}
