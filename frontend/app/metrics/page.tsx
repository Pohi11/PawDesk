import { Suspense } from "react";

import { MetricsCharts } from "@/components/metrics-charts";
import { Figure, Loading, PageTitle } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import { formatCost } from "@/lib/format";
import type { Metrics } from "@/lib/types";

export default function MetricsPage() {
  return (
    <>
      <PageTitle title="Metrics">
        Costs are exactly what the model provider reported, and times come from each step&apos;s
        recorded start and end. Nothing here is estimated.
      </PageTitle>
      <Suspense fallback={<Loading label="Loading metrics" />}>
        <Overview />
      </Suspense>
    </>
  );
}

async function Overview() {
  const metrics = await backendJson<Metrics>("/metrics");
  const { cost, run_seconds: runs, flag_rate: flags } = metrics;
  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 gap-x-8 gap-y-6 md:grid-cols-4">
        <Figure label="Average cost per request" value={formatCost(cost.average_per_request_usd)} note={`${formatCost(cost.total_usd)} across ${cost.requests_with_cost} requests`} />
        <Figure label="Typical run" value={runs.p50 === null ? "None yet" : `${runs.p50.toFixed(1)} s`} note={runs.p95 === null ? undefined : `95% finish within ${runs.p95.toFixed(1)} s`} />
        <Figure
          label="Sent to a person"
          value={flags.rate === null ? "None yet" : `${Math.round(flags.rate * 100)}%`}
          note={`${flags.flagged} of ${flags.drafted} replies`}
        />
        <Figure label="Runs measured" value={runs.runs} />
      </div>
      <MetricsCharts metrics={metrics} />
    </div>
  );
}
