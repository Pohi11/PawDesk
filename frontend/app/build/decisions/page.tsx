import { BuildNav } from "@/components/build-nav";
import { Md } from "@/components/markdown";
import { PageTitle } from "@/components/ui";
import data from "@/content/walkthrough.json";
import { type Walkthrough, decisionAnchor } from "@/lib/walkthrough";

const walkthrough = data as unknown as Walkthrough;

export default function DecisionsPage() {
  return (
    <>
      <PageTitle title="Decision records">
        Each record states its context, the options considered, the decision, and its consequences.
        Records are never rewritten: a changed decision gets a new record that supersedes the old
        one.
      </PageTitle>
      <BuildNav />

      <nav className="mb-8 space-y-1 text-sm">
        {walkthrough.decisions.map((d) => (
          <a key={d.number} href={`#${decisionAnchor(d.number)}`} className="block text-code hover:underline">
            {d.number}: {d.title}
          </a>
        ))}
      </nav>

      <div className="space-y-6">
        {walkthrough.decisions.map((d) => (
          <article
            key={d.number}
            id={decisionAnchor(d.number)}
            className="scroll-mt-6 rounded-2xl bg-surface p-6 ring-1 ring-rule target:ring-2 target:ring-code"
          >
            <details open>
              <summary className="cursor-pointer">
                <span className="font-mono text-faint">{d.number}</span>{" "}
                <span className="font-semibold">{d.title}</span>
                <span className="ml-3 text-xs text-muted">
                  {d.status}, {d.date}
                </span>
              </summary>
              <div className="mt-4">
                {/* The record's own title and header bullets are shown above. */}
                <Md>{d.markdown.replace(/^# .*\n+(- \*\*\w+:\*\* .*\n)*/m, "")}</Md>
              </div>
            </details>
          </article>
        ))}
      </div>
    </>
  );
}
