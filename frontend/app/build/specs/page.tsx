import { BuildNav, RequirementBadge } from "@/components/build-nav";
import { Md } from "@/components/markdown";
import { PageTitle } from "@/components/ui";
import data from "@/content/walkthrough.json";
import { type Walkthrough, requirementAnchor } from "@/lib/walkthrough";

const walkthrough = data as unknown as Walkthrough;

const RESULT: Record<string, string> = {
  passed: "text-kennel",
  failed: "text-error",
  skipped: "text-faint",
};

export default function SpecsPage() {
  return (
    <>
      <PageTitle title="Specs and tests">
        The current requirements by capability. Each one shows its WHEN/THEN scenarios and the tests
        that name it, with each test&apos;s latest result.
      </PageTitle>
      <BuildNav />

      <nav className="mb-8 flex flex-wrap gap-2 text-xs">
        {walkthrough.specs.map((c) => (
          <a key={c.capability} href={`#cap-${c.capability}`} className="rounded bg-wash px-2 py-1 text-ink hover:bg-rule">
            {c.capability} ({c.requirements.length})
          </a>
        ))}
      </nav>

      <div className="space-y-10">
        {walkthrough.specs.map((capability) => (
          <section key={capability.capability} id={`cap-${capability.capability}`} className="scroll-mt-6">
            <h2 className="font-mono text-lg font-semibold">{capability.capability}</h2>
            <div className="mt-1">
              <Md>{capability.purpose}</Md>
            </div>
            <div className="mt-4 space-y-4">
              {capability.requirements.map((req) => (
                <article
                  key={req.name}
                  id={requirementAnchor(capability.capability, req.name)}
                  className="scroll-mt-6 rounded-2xl bg-surface p-5 ring-1 ring-rule target:ring-2 target:ring-code"
                >
                  <header className="flex flex-wrap items-center gap-3">
                    <h3 className="font-semibold">{req.name}</h3>
                    <RequirementBadge status={req.status} />
                  </header>
                  <div className="mt-2">
                    <Md>{req.text}</Md>
                  </div>
                  <div className="mt-3 grid gap-4 lg:grid-cols-2">
                    <div className="min-w-0">
                      <h4 className="text-sm font-medium">Scenarios</h4>
                      <ul className="mt-1 space-y-2">
                        {req.scenarios.map((s) => (
                          <li key={s.name} className="rounded-lg bg-wash p-2">
                            <div className="text-xs font-medium">{s.name}</div>
                            {s.steps.map((step) => (
                              <Md key={step} compact>
                                {step}
                              </Md>
                            ))}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-sm font-medium">
                        Tests ({req.tests.length})
                      </h4>
                      <ul className="mt-1 space-y-1">
                        {req.tests.map((t) => (
                          <li key={`${t.suite}-${t.id}`} className="flex items-baseline gap-2 text-xs">
                            <span className={`w-12 shrink-0 font-medium ${RESULT[t.status]}`}>{t.status}</span>
                            <span className="w-14 shrink-0 text-faint">{t.suite}</span>
                            <span className="break-all font-mono text-ink">{t.id}</span>
                            <span className="ml-auto shrink-0 tabular-nums text-faint">
                              {t.seconds.toFixed(2)} s
                            </span>
                          </li>
                        ))}
                        {req.tests.length === 0 && <li className="text-xs text-signal">No linked test.</li>}
                      </ul>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}
