/**
 * /embed — minimal chrome dashboard for Confluence iframe embedding.
 * No header, no footer. Only the metric grid, trend chart, and stale banner.
 * Theme is detected from system preference (no toggle in embed mode).
 */
import { MetricGrid } from "../components/dashboard/MetricGrid";
import { TrendChart } from "../components/dashboard/TrendChart";
import { StaleBanner } from "../components/dashboard/StaleBanner";
import { MetricModal } from "../components/dashboard/MetricModal";

export default function EmbedPage() {
  return (
    <main className="bg-background text-on-background min-h-screen p-6 space-y-8">
      <StaleBanner />
      <MetricGrid />
      <TrendChart />
      <MetricModal />
    </main>
  );
}
