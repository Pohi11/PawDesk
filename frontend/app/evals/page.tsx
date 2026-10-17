import { Suspense } from "react";

import { ComparisonTable } from "@/components/comparison-table";
import { Loading, PageTitle } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import { formatCost } from "@/lib/format";
import type { EvalReport } from "@/lib/types";

export default function EvalsPage() {
  return (
    <>
      <PageTitle title="Evals">
        Scores for the model steps on labeled synthetic examples. Each card is one dated run with real
        model calls.
      </PageTitle>
      <Suspense fallback={<Loading label="Loading results" />}>
        <Reports />
      </Suspense>
    </>
  );
}

const KIND: Record<string, string> = {
  intake: "Reading booking messages",
  records: "Reading vaccine certificates",
  sample: "Reading the demo cards again and again",
};

const MEASURE: Record<string, string> = {
  cases_fully_matched: "Messages with every field right",
  injections_sent_to_review: "Injection attempts sent to a person",
  decision_agreement: "Decisions that match the label",
  silent_disagreements: "Wrong decisions not sent to a person",
  vaccine_recall: "Vaccines found",
  expiry_accuracy: "Expiry dates read right",
  invented_expiries: "Expiry dates made up",
  sent_to_review: "Certificates sent to a person",
  errors: "Failed runs",
  reads: "Reads",
  misreads: "Reads with a date wrong",
  decision_flips: "Reads that change the decision",
  silent_flips: "Changed decisions not sent to a person",
  failed: "Failed reads",
};

async function Reports() {
  const reports = await backendJson<EvalReport[]>("/evals");
  const comparison = reports.filter((r) => r.kind === "comparison").at(-1);
  const readings = reports.filter((r) => r.kind !== "comparison").reverse();
  return (
    <div className="space-y-12">
      {comparison && <ComparisonTable report={comparison} />}
      <section>
        <h2 className="mb-4 text-2xl font-bold">Reading accuracy</h2>
        <div className="grid gap-6 md:grid-cols-2">
          {readings.map((r) => (
            <article key={r.file} className="rounded-2xl bg-surface p-6 ring-1 ring-rule">
              <h3 className="text-lg font-semibold">
                {KIND[r.kind] ?? r.kind}
                {r.benchmark && <span className="font-normal text-muted">, benchmark {r.benchmark}</span>}
              </h3>
              <p className="text-sm text-faint">
                {r.run_at ? new Date(r.run_at).toLocaleDateString() : "Date unknown"}, prompt {r.prompt_version}, {formatCost(r.cost_usd)}
              </p>
              <dl className="mt-4 space-y-1.5">
                {Object.entries(r.headline).map(([key, value]) => {
                  const alarming = (key === "silent_disagreements" || key === "invented_expiries" || key === "silent_flips") && Number(value) > 0;
                  return (
                    <div key={key} className="flex justify-between gap-4">
                      <dt className="text-muted">{MEASURE[key] ?? key.replaceAll("_", " ")}</dt>
                      <dd className={alarming ? "font-semibold text-signal" : "font-medium"}>{String(value)}</dd>
                    </div>
                  );
                })}
              </dl>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
