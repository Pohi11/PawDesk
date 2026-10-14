import { Suspense } from "react";

import { ComparisonTable } from "@/components/comparison-table";
import { Loading, PageHeader } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import { formatCost } from "@/lib/format";
import type { EvalReport } from "@/lib/types";

export default function EvalsPage() {
  return (
    <>
      <PageHeader title="Evals">
        Every evaluation run, oldest first. Each is a dated report from a real run over a labeled
        benchmark of synthetic data; nothing is estimated. Decision agreement and silent
        disagreements (wrong and not flagged) are the safety numbers for vaccine reading.
      </PageHeader>
      <Suspense fallback={<Loading label="Loading reports…" />}>
        <Reports />
      </Suspense>
    </>
  );
}

async function Reports() {
  const reports = await backendJson<EvalReport[]>("/evals");
  const comparison = reports.filter((r) => r.kind === "comparison").at(-1);
  return (
    <div className="space-y-6">
      {comparison && <ComparisonTable report={comparison} />}
      <ReportTable reports={reports} />
    </div>
  );
}

function ReportTable({ reports }: { reports: EvalReport[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-zinc-50 text-left text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-4 py-2">Run</th>
            <th className="px-4 py-2">Kind</th>
            <th className="px-4 py-2">Benchmark</th>
            <th className="px-4 py-2">Prompt</th>
            <th className="px-4 py-2">Results</th>
            <th className="px-4 py-2 text-right">Cost</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 align-top">
          {reports.map((r) => (
            <tr key={r.file}>
              <td className="px-4 py-2 text-zinc-500">
                {r.run_at ? new Date(r.run_at).toLocaleString() : "—"}
              </td>
              <td className="px-4 py-2 font-medium">{r.kind}</td>
              <td className="px-4 py-2">{r.benchmark ?? "—"}</td>
              <td className="px-4 py-2 font-mono text-xs">
                {r.prompt_version}
                <div className="text-zinc-400">{r.model}</div>
              </td>
              <td className="px-4 py-2">
                {r.kind === "comparison" ? (
                  <span className="text-xs text-zinc-500">side by side above</span>
                ) : (
                <dl className="grid grid-cols-[auto_auto] gap-x-3 text-xs">
                  {Object.entries(r.headline).map(([key, value]) => (
                    <div key={key} className="contents">
                      <dt className="text-zinc-500">{key.replaceAll("_", " ")}</dt>
                      <dd
                        className={`tabular-nums ${key === "silent_disagreements" && Number(value) > 0 ? "font-semibold text-red-700" : ""}`}
                      >
                        {String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
                )}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">{formatCost(r.cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
