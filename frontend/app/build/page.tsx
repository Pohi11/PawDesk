import Link from "next/link";

import { BuildNav, RequirementBadge } from "@/components/build-nav";
import { Md } from "@/components/markdown";
import { PageHeader, Stat } from "@/components/ui";
import data from "@/content/walkthrough.json";
import {
  type Walkthrough,
  currentRequirement,
  decisionHref,
  requirementHref,
} from "@/lib/walkthrough";

const walkthrough = data as unknown as Walkthrough;

export default function BuildPage() {
  const { totals, changes } = walkthrough;
  return (
    <>
      <PageHeader title="How PawDesk was built">
        Generated from the repository itself: the archived spec changes, the current requirements,
        the decision records, and the latest test reports. Every number and link below comes from
        those files.
      </PageHeader>
      <BuildNav />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Spec changes" value={totals.changes} hint="archived, in order" />
        <Stat
          label="Requirements verified"
          value={`${totals.verified}/${totals.requirements}`}
          hint="every scenario-backed requirement has a passing test"
        />
        <Stat
          label="Tests"
          value={totals.tests.backend + totals.tests.frontend + (totals.tests.e2e ?? 0)}
          hint={`${totals.tests.backend} backend · ${totals.tests.frontend} frontend · ${totals.tests.e2e ?? 0} end-to-end · ${totals.linked_tests} linked to a requirement`}
        />
        <Stat label="Decision records" value={walkthrough.decisions.length} />
      </div>
      <p className="mt-2 text-xs text-zinc-500">
        Generated {new Date(walkthrough.generated_at).toLocaleString()} · backend report{" "}
        {walkthrough.reports.backend ?? "missing"} · frontend report {walkthrough.reports.frontend ?? "missing"} ·
        end-to-end report {walkthrough.reports.e2e ?? "missing"}
      </p>

      <section className="mt-8 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Method</h2>
        <div className="mt-3 grid gap-6 text-sm text-zinc-700 md:grid-cols-2">
          <Method title="Every change starts as a spec">
            Each phase is an OpenSpec change: a proposal (why), requirements with WHEN/THEN
            scenarios (what), a design (how, and the options weighed), and tasks that each name the
            test that proves them. When the work is done, the change is archived and its
            requirements merge into the living specs.
          </Method>
          <Method title="Decisions are written down once">
            Choices that outlive a single change get a numbered decision record: context, options
            considered, decision, consequences. Records are never rewritten; a changed mind is a
            new record.
          </Method>
          <Method title="Tests name the requirement they verify">
            Backend tests carry a marker and frontend tests a tag naming their requirement. Both
            land in standard JUnit reports, so every requirement below links to its tests and
            their latest result, and a coverage check fails the build on any gap.
          </Method>
          <Method title="Models are measured, not trusted">
            Deterministic rules stay in code. Steps that use a model are evaluated on labeled,
            synthetic benchmarks with dated reports, counting the dangerous errors (invented
            dates, silent wrong decisions) separately. Every model call is traced with its exact
            cost.
          </Method>
        </div>
      </section>

      <h2 className="mt-10 mb-4 text-lg font-semibold">Change timeline</h2>
      <ol className="relative space-y-6 border-l border-zinc-200 pl-6">
        {changes.map((change) => (
          <li key={change.id} className="relative">
            <span className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-white bg-blue-500" />
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <h3 className="text-base font-semibold">{change.title}</h3>
                <span className="text-xs text-zinc-500">{change.date}</span>
                <span className="text-xs text-zinc-400">
                  {change.tasks.flatMap((g) => g.items).filter((i) => i.done).length}/
                  {change.tasks.flatMap((g) => g.items).length} tasks
                </span>
              </div>
              <div className="mt-2">
                <Md>{change.why}</Md>
              </div>

              <details className="mt-3">
                <summary className="cursor-pointer text-sm font-medium text-zinc-600">
                  What changed, requirements, decisions, tasks
                </summary>
                <div className="mt-3 space-y-4">
                  <Md>{change.what_changes}</Md>

                  {change.requirements.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                        Requirements
                      </h4>
                      <ul className="mt-1 space-y-1 text-sm">
                        {change.requirements.map((ref) => {
                          const current = currentRequirement(walkthrough, ref.capability, ref.name);
                          return (
                            <li key={`${ref.kind}-${ref.capability}-${ref.name}`} className="flex flex-wrap items-center gap-2">
                              <span className="w-16 text-xs text-zinc-400">{ref.kind}</span>
                              {current ? (
                                <Link href={requirementHref(ref.capability, ref.name)} className="text-blue-700 hover:underline">
                                  {ref.name}
                                </Link>
                              ) : (
                                <span className="text-zinc-500">{ref.name}</span>
                              )}
                              <span className="text-xs text-zinc-400">{ref.capability}</span>
                              {current && <RequirementBadge status={current.status} />}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}

                  {change.decisions.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                        Decisions relied on
                      </h4>
                      <ul className="mt-1 flex flex-wrap gap-2 text-sm">
                        {change.decisions.map((n) => {
                          const record = walkthrough.decisions.find((d) => d.number === n);
                          return (
                            <li key={n}>
                              <Link href={decisionHref(n)} className="rounded bg-zinc-100 px-2 py-0.5 text-blue-700 hover:underline">
                                {n} {record ? `· ${record.title}` : ""}
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Tasks</h4>
                    {change.tasks.map((group) => (
                      <div key={group.title} className="mt-2">
                        <div className="text-xs font-medium text-zinc-600">{group.title}</div>
                        <ul className="mt-1 space-y-1">
                          {group.items.map((item) => (
                            <li key={item.id} className="flex gap-2 text-xs text-zinc-700">
                              <span className={item.done ? "text-emerald-600" : "text-zinc-400"}>
                                {item.done ? "✓" : "○"}
                              </span>
                              <span className="font-mono text-zinc-400">{item.id}</span>
                              <span>{item.text}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </details>
            </div>
          </li>
        ))}
      </ol>
    </>
  );
}

function Method({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="font-semibold text-zinc-900">{title}</h3>
      <p className="mt-1 leading-relaxed">{children}</p>
    </div>
  );
}
