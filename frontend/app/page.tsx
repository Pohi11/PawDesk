import Link from "next/link";
import { Suspense } from "react";

import { Loading, PageHeader, Stat, StatusBadge } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import { formatCost } from "@/lib/format";
import type { Metrics, RequestRow } from "@/lib/types";

export default function Home() {
  return (
    <>
      <PageHeader title="Requests">
        Every booking request PawDesk has handled, newest first. Open one to see its run: which
        steps ran, what each model was asked and answered, and what it cost.
      </PageHeader>
      {/* Live data: streamed in at request time behind Suspense (Cache Components). */}
      <Suspense fallback={<Loading label="Loading requests…" />}>
        <Overview />
      </Suspense>
    </>
  );
}

async function Overview() {
  const [metrics, rows] = await Promise.all([
    backendJson<Metrics>("/metrics"),
    backendJson<RequestRow[]>("/requests?limit=50"),
  ]);
  const flagRate = metrics.flag_rate.rate;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Requests" value={rows.length} hint="most recent 50" />
        <Stat
          label="Avg cost per request"
          value={formatCost(metrics.cost.average_per_request_usd)}
          hint={`total ${formatCost(metrics.cost.total_usd)}`}
        />
        <Stat
          label="Median run"
          value={metrics.run_seconds.p50 === null ? "—" : `${metrics.run_seconds.p50.toFixed(1)} s`}
          hint={metrics.run_seconds.p95 === null ? undefined : `p95 ${metrics.run_seconds.p95.toFixed(1)} s`}
        />
        <Stat
          label="Flagged for review"
          value={flagRate === null ? "—" : `${Math.round(flagRate * 100)}%`}
          hint={`${metrics.flag_rate.flagged} of ${metrics.flag_rate.drafted} drafted`}
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-left text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-4 py-2">Received</th>
              <th className="px-4 py-2">Owner</th>
              <th className="px-4 py-2">Pet</th>
              <th className="px-4 py-2">Service</th>
              <th className="px-4 py-2">Dates</th>
              <th className="px-4 py-2">State</th>
              <th className="px-4 py-2 text-right">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {rows.map((row) => (
              <tr key={row.id} className="hover:bg-zinc-50">
                <td className="px-4 py-2 text-zinc-500">
                  <Link href={`/requests/${row.id}`} className="hover:underline">
                    {new Date(row.created_at).toLocaleString()}
                  </Link>
                </td>
                <td className="px-4 py-2">{row.owner}</td>
                <td className="px-4 py-2">{row.pet ?? <span className="text-zinc-400">unknown</span>}</td>
                <td className="px-4 py-2">{row.service ?? "—"}</td>
                <td className="px-4 py-2 tabular-nums">
                  {row.start_date ? `${row.start_date} → ${row.end_date}` : "—"}
                </td>
                <td className="px-4 py-2">
                  <StatusBadge status={row.status} />
                  {row.flagged && <span className="ml-2 text-xs text-amber-700">flagged</span>}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">{formatCost(row.cost_usd)}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                  No requests yet. <Link href="/demo" className="underline">Submit a demo request</Link>.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
