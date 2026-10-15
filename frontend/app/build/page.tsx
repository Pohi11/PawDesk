import Link from "next/link";

import { BuildNav, RequirementBadge } from "@/components/build-nav";
import { Md } from "@/components/markdown";
import { Figure, PageTitle } from "@/components/ui";
import data from "@/content/walkthrough.json";
import { type Walkthrough, currentRequirement, decisionHref, requirementHref } from "@/lib/walkthrough";

const walkthrough = data as unknown as Walkthrough;

const METHOD = [
  {
    title: "Each change starts as a spec",
    text: "Each piece of work is an OpenSpec change. It holds a proposal, requirements written as when-then scenarios, a design that weighs the options, and tasks that each name the test proving them. A finished change is archived, and its requirements join the current specs.",
  },
  {
    title: "Decisions get a numbered record",
    text: "A choice that outlives one change gets a record with its context, the options, the decision, and the consequences. A committed record stays as written. A new record replaces it when the decision changes.",
  },
  {
    title: "Tests name the requirement they prove",
    text: "Backend, frontend, and browser tests each name the requirement they verify. Each requirement below links to its tests and their latest result, and the build fails when a requirement has no passing test.",
  },
  {
    title: "Model steps are scored and traced",
    text: "Rules with a right answer stay in code. Model steps are scored on labeled synthetic examples, with the dangerous errors counted separately, and each model call is traced with the cost the provider reported.",
  },
];

export default function BuildPage() {
  const { totals, changes } = walkthrough;
  const tests = totals.tests.backend + totals.tests.frontend + (totals.tests.e2e ?? 0);
  return (
    <>
      <PageTitle title="How PawDesk was built">
        The changes, requirements, tests, and decision records on these pages come from the repository
        and the latest test run. The method section below is written by hand.
      </PageTitle>
      <BuildNav />

      <div className="grid grid-cols-2 gap-x-8 gap-y-6 md:grid-cols-4">
        <Figure label="Requirements proven" value={`${totals.verified} of ${totals.requirements}`} />
        <Figure label="Tests" value={tests} note={`${totals.linked_tests} prove a named requirement`} />
        <Figure label="Changes" value={totals.changes} />
        <Figure label="Decision records" value={walkthrough.decisions.length} />
      </div>
      <p className="mt-3 text-sm text-faint">
        Generated {new Date(walkthrough.generated_at).toLocaleString()} from the latest test results.
      </p>

      <section className="mt-14 grid gap-x-10 gap-y-8 md:grid-cols-2">
        {METHOD.map((m) => (
          <div key={m.title}>
            <h2 className="text-xl font-semibold">{m.title}</h2>
            <p className="mt-2 leading-relaxed text-muted">{m.text}</p>
          </div>
        ))}
      </section>

      <h2 className="mt-16 mb-6 text-3xl font-bold">Changes, in order</h2>
      <ol className="space-y-4 border-l-2 border-rule pl-8">
        {changes.map((change) => {
          const items = change.tasks.flatMap((g) => g.items);
          return (
            <li key={change.id} className="relative">
              <span aria-hidden className="absolute top-2 -left-[41px] h-4 w-4 rounded-full border-4 border-paper bg-kennel" />
              <article className="rounded-2xl bg-surface p-6 ring-1 ring-rule">
                <p className="text-sm text-faint">{new Date(`${change.date}T00:00:00`).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}</p>
                <h3 className="mt-0.5 text-xl font-semibold">{change.title}</h3>
                <div className="mt-2">
                  <Md>{change.why}</Md>
                </div>
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm font-medium text-code">
                    What changed, {change.requirements.length} requirements, {items.filter((i) => i.done).length} of {items.length} tasks
                  </summary>
                  <div className="mt-4 space-y-5">
                    <Md>{change.what_changes}</Md>
                    {change.requirements.length > 0 && (
                      <div>
                        <h4 className="font-medium">Requirements</h4>
                        <ul className="mt-2 space-y-1.5 text-sm">
                          {change.requirements.map((ref) => {
                            const current = currentRequirement(walkthrough, ref.capability, ref.name);
                            return (
                              <li key={`${ref.kind}-${ref.capability}-${ref.name}`} className="flex flex-wrap items-center gap-2">
                                <span className="w-16 text-faint">{ref.kind}</span>
                                {current ? (
                                  <Link href={requirementHref(ref.capability, ref.name)} className="text-code hover:underline">
                                    {ref.name}
                                  </Link>
                                ) : (
                                  <span className="text-muted">{ref.name}</span>
                                )}
                                {current && <RequirementBadge status={current.status} />}
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
                    {change.decisions.length > 0 && (
                      <div>
                        <h4 className="font-medium">Decisions it relied on</h4>
                        <ul className="mt-2 space-y-1 text-sm">
                          {change.decisions.map((n) => {
                            const record = walkthrough.decisions.find((d) => d.number === n);
                            return (
                              <li key={n}>
                                <Link href={decisionHref(n)} className="text-code hover:underline">
                                  {n}: {record?.title ?? "decision record"}
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
                    <div>
                      <h4 className="font-medium">Tasks</h4>
                      <ul className="mt-2 space-y-1.5">
                        {items.map((item) => (
                          <li key={item.id} className="flex gap-2 text-sm">
                            <span className={item.done ? "text-kennel" : "text-faint"}>{item.done ? "✓" : "○"}</span>
                            <span className="text-muted">{item.text}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </details>
              </article>
            </li>
          );
        })}
      </ol>
    </>
  );
}
