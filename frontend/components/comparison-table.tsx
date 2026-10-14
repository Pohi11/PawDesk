import { type Architecture, type ArchitectureHeadline, comparisonRows } from "@/lib/comparison";
import { formatCost } from "@/lib/format";
import type { EvalReport } from "@/lib/types";

import { Card } from "./ui";

export function ComparisonTable({ report }: { report: EvalReport }) {
  const headline = report.headline as unknown as Record<Architecture, ArchitectureHeadline>;
  const rows = comparisonRows(headline);
  const cell = (side: Architecture, better: Architecture | null, value: string) => (
    <td className={`px-4 py-2 text-right tabular-nums ${better === side ? "font-semibold text-emerald-700" : ""}`}>
      {value}
    </td>
  );

  return (
    <Card
      title={`Architecture comparison: ${headline.hybrid.cases} cases, ${report.run_at ? new Date(report.run_at).toLocaleString() : ""}`}
    >
      <p className="mb-3 max-w-3xl text-sm text-zinc-600">
        The same booking cases, the same model, and the same deterministic checking tools. Expected
        outcomes come from running the checks on each case&apos;s true facts. An unsafe confirmation
        is a booking confirmed that should not have been.
      </p>
      <table className="w-full max-w-2xl text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-4 py-2">Metric</th>
            <th className="px-4 py-2 text-right">Hybrid workflow</th>
            <th className="px-4 py-2 text-right">Autonomous agent</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {rows.map((r) => (
            <tr key={r.label}>
              <td className="px-4 py-2">{r.label}</td>
              {cell("hybrid", r.better, r.hybrid)}
              {cell("autonomous", r.better, r.autonomous)}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-zinc-500">
        Total cost of the run {formatCost(report.cost_usd)} · {report.prompt_version} · {report.model}
      </p>
    </Card>
  );
}
