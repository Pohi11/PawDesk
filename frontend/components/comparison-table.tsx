import { type Architecture, type ArchitectureHeadline, comparisonRows } from "@/lib/comparison";
import { formatCost } from "@/lib/format";
import type { EvalReport } from "@/lib/types";

export function ComparisonTable({ report }: { report: EvalReport }) {
  const headline = report.headline as unknown as Record<Architecture, ArchitectureHeadline>;
  const rows = comparisonRows(headline);
  const cell = (side: Architecture, better: Architecture | null, value: string) => (
    <td className={`px-5 py-3 text-right ${better === side ? "font-semibold text-kennel" : "text-muted"}`}>
      {value}
      {better === side && <span className="sr-only"> (better)</span>}
    </td>
  );

  return (
    <section className="rounded-2xl bg-surface ring-1 ring-rule">
      <div className="px-6 pt-6">
        <h2 className="text-2xl font-bold">PawDesk against a single autonomous agent</h2>
        <p className="mt-2 max-w-2xl text-muted">
          Both ran the same {headline.hybrid.cases} booking requests with one model and one set of checking
          tools. Each request&apos;s right answer comes from running the checks on its true facts. An unsafe
          confirmation counts a reply that confirmed a booking the checks would have stopped.
        </p>
      </div>
      <table className="mt-4 w-full">
        <thead>
          <tr className="border-b border-rule text-left text-sm text-muted">
            <th className="px-6 py-2 font-medium">
              <span className="sr-only">Measure</span>
            </th>
            <th className="px-5 py-2 text-right font-medium text-ink">PawDesk</th>
            <th className="px-5 py-2 text-right font-medium text-ink">Autonomous agent</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {rows.map((r) => (
            <tr key={r.label} className={r.label === "Unsafe confirmations" ? "bg-signal-soft/50" : undefined}>
              <td className="px-6 py-3">{r.label}</td>
              {cell("hybrid", r.better, r.hybrid)}
              {cell("autonomous", r.better, r.autonomous)}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-6 py-4 text-sm text-faint">
        One run, {report.run_at ? new Date(report.run_at).toLocaleDateString() : "date unknown"}, costing {formatCost(report.cost_usd)} in total.
      </p>
    </section>
  );
}
