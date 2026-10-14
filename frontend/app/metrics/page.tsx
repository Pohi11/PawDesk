import { Suspense } from "react";

import { MetricsCharts } from "@/components/metrics-charts";
import { Loading, PageHeader, Stat } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import { formatCost } from "@/lib/format";
import type { Metrics } from "@/lib/types";

export default function MetricsPage() {
  return (
    <>
      <PageHeader title="Metrics">
        Cost and latency come from the spans every run records: model costs exactly as the provider
        reported them, durations from span timestamps. Nothing here is estimated.
      </PageHeader>
      <Suspense fallback={<Loading label="Loading metrics…" />}>
        <Overview />
      </Suspense>
    </>
  );
}

async function Overview() {
  const metrics = await backendJson<Metrics>("/metrics");
  const { cost, run_seconds: runs, flag_rate: flags } = metrics;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Total model cost" value={formatCost(cost.total_usd)} hint={`${cost.requests_with_cost} requests`} />
        <Stat label="Avg cost per request" value={formatCost(cost.average_per_request_usd)} />
        <Stat
          label="Run duration"
          value={runs.p50 === null ? "—" : `${runs.p50.toFixed(1)} s`}
          hint={runs.p95 === null ? `${runs.runs} runs` : `median · p95 ${runs.p95.toFixed(1)} s · ${runs.runs} runs`}
        />
        <Stat
          label="Flag rate"
          value={flags.rate === null ? "—" : `${Math.round(flags.rate * 100)}%`}
          hint={`${flags.flagged} of ${flags.drafted} drafted replies`}
        />
      </div>
      <MetricsCharts metrics={metrics} />
    </div>
  );
}
