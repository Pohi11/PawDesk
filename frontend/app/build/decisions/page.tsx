import { BuildNav } from "@/components/build-nav";
import { Md } from "@/components/markdown";
import { PageHeader } from "@/components/ui";
import data from "@/content/walkthrough.json";
import { type Walkthrough, decisionAnchor } from "@/lib/walkthrough";

const walkthrough = data as unknown as Walkthrough;

export default function DecisionsPage() {
  return (
    <>
      <PageHeader title="Decision records">
        Each record states its context, the options considered, the decision, and its consequences.
        Records are never rewritten: a changed decision gets a new record that supersedes the old
        one.
      </PageHeader>
      <BuildNav />

      <nav className="mb-8 space-y-1 text-sm">
        {walkthrough.decisions.map((d) => (
          <a key={d.number} href={`#${decisionAnchor(d.number)}`} className="block text-blue-700 hover:underline">
            {d.number} · {d.title}
          </a>
        ))}
      </nav>

      <div className="space-y-6">
        {walkthrough.decisions.map((d) => (
          <article
            key={d.number}
            id={decisionAnchor(d.number)}
            className="scroll-mt-6 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm target:ring-2 target:ring-blue-400"
          >
            <details open>
              <summary className="cursor-pointer">
                <span className="font-mono text-zinc-400">{d.number}</span>{" "}
                <span className="font-semibold">{d.title}</span>
                <span className="ml-3 text-xs text-zinc-500">
                  {d.date} · {d.status}
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
