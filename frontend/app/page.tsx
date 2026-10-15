import Link from "next/link";
import { type ReactNode, Suspense } from "react";

import { DemoPanel } from "@/components/demo-panel";
import { KindDot, Loading, StateTag } from "@/components/ui";
import data from "@/content/walkthrough.json";
import { backendJson } from "@/lib/backend";
import type { DemoSample, SpanKind } from "@/lib/types";
import type { Walkthrough } from "@/lib/walkthrough";

const walkthrough = data as unknown as Walkthrough;

// The home page (spec: run-dashboard): an introduction with one worked request, the Try
// panel, then what a visitor reads after trying it. Counts come from the walkthrough; the
// rest is hand-written and has to match the code. The worked example quotes the clean
// sample and the outcome the end-to-end test asserts for it.

const link = "text-code underline decoration-code/30 underline-offset-2 hover:decoration-code";

const STEPS: { title: string; who: SpanKind[]; text: ReactNode }[] = [
  {
    title: "Read",
    who: ["llm"],
    text: "A model pulls the pet, the service, and the dates out of the message. A second call reads the photo of the vaccine card.",
  },
  {
    title: "Check",
    who: ["code"],
    text: "Code compares each required vaccine's expiry date with the stay, then looks for a free kennel that fits the pet's size.",
  },
  {
    title: "Find options",
    who: ["llm", "tool"],
    text: "When a check fails, an agent with read-only tools suggests a fix: other dates, a larger kennel, or an updated vaccine record. Code runs the checks again on each suggestion.",
  },
  {
    title: "Write the reply",
    who: ["llm"],
    text: "A model writes to the pet parent from the checked facts. It never sees their original message, so instructions hidden in that message can't reach it.",
  },
  {
    title: "Send or hold",
    who: ["code", "human"],
    text: (
      <>
        Code scans the draft for promises the desk can&apos;t keep. A clean reply goes out and
        reserves the kennel in one database transaction. A flagged one waits in the{" "}
        <Link href="/reviews" className={link}>review queue</Link> until someone on staff approves,
        edits, or declines it.
      </>
    ),
  },
];

const WHO: Record<SpanKind, string> = { llm: "model", code: "code", tool: "tools", human: "staff" };

const GUARANTEES: ReactNode[] = [
  "Only the checks or a staff member can approve a booking. The lifecycle code refuses an approval from anywhere else, a model included.",
  "Postgres refuses two reservations for the same kennel on the same night, so a race between two requests can't double-book it.",
  "A run that crashes picks up at the step it stopped on and doesn't pay again for model calls it already finished.",
  <>
    Each model call, tool call, and step is saved with its input, output, tokens, billed cost, and
    timing. Open any request on the <Link href="/requests" className={link}>requests list</Link> to
    inspect them.
  </>,
];

const POSTING: { skill: string; here: ReactNode }[] = [
  {
    skill: "Python, FastAPI",
    here: "The API, the workflow, and the checks. Pydantic validates each model response before the code uses it.",
  },
  {
    skill: "TypeScript, React",
    here: "This dashboard, in Next.js 16 and React 19 with Tailwind CSS. React Flow draws the run graph and Recharts draws the metrics.",
  },
  {
    skill: "REST APIs and integrations",
    here: "FastAPI endpoints with live run updates over server-sent events. Model calls go to DeepSeek V4.1 Flash through OpenRouter. The browser reaches the API only through a proxy with an allowlist.",
  },
  {
    skill: "PostgreSQL and data modeling",
    here: "Postgres 18 with SQLAlchemy and Alembic migrations. The schema models owners, pets, vaccine records, kennels, reservations, and the steps of each run.",
  },
  {
    skill: "Docker and CI/CD",
    here: "Docker Compose runs the full stack. A GitHub Actions workflow runs lint, type checks, the tests, the build, and a gitleaks secret scan.",
  },
  {
    skill: "Automated testing",
    here: "pytest against a real Postgres, Vitest for the dashboard's logic, and Playwright end-to-end runs that replay recorded model responses so they cost nothing.",
  },
  {
    skill: "Secure coding",
    here: "Pet parents' messages and photos count as untrusted input. Code flags prompt injections, and the API key stays on the server.",
  },
  {
    skill: "Accessibility",
    here: "You can reach each step of a run by keyboard, and screen readers announce its summary. Layouts hold at phone width.",
  },
];

export default function Home() {
  return (
    <>
      <Intro />

      <section id="try" aria-labelledby="try-heading" className="scroll-mt-6">
        <h2 id="try-heading" className="text-3xl font-bold">
          Try a request
        </h2>
        <p className="mt-2 mb-8 max-w-2xl leading-relaxed text-muted">
          Pick a sample or make one up, then watch each step run with real model calls. The desk
          treats today as March 3, 2027, so the vaccine cards&apos; dates line up with the stays.
        </p>
        <Suspense fallback={<Loading label="Loading samples" />}>
          <Samples />
        </Suspense>
      </section>

      <HowItWorks />
      <About />
      <Method />

      <p className="mt-24 border-t border-rule pt-6 text-sm text-faint">
        The pet parents, pets, and vaccine cards on this site are made up.
      </p>
    </>
  );
}

async function Samples() {
  const samples = await backendJson<DemoSample[]>("/demo/samples");
  return <DemoPanel samples={samples} />;
}

function Intro() {
  return (
    <section className="mb-20 grid items-start gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-14">
      <div className="lg:pt-6">
        <h1 className="text-4xl leading-[1.05] font-extrabold sm:text-5xl">
          PawDesk reads booking requests and drafts the replies.
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-muted">
          Pet parents write in to book boarding, daycare, or grooming, with a photo of the vaccine
          card attached. PawDesk checks the vaccines against your rules, finds a free kennel, and
          writes back. When a vaccine has lapsed or someone hides instructions in a message, the
          reply waits for someone on your staff.
        </p>
        <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-3">
          <a href="#try" className="rounded-full bg-ink px-5 py-2.5 font-medium text-white hover:brightness-125">
            Try a request
          </a>
          <a href="#how" className={link}>
            How it works
          </a>
        </div>
        <p className="mt-8 text-sm text-muted">
          I built PawDesk to show full stack work and AI-driven development.{" "}
          <a href="#about" className={link}>
            Why and how
          </a>
        </p>
      </div>
      <WorkedExample />
    </section>
  );
}

function Read({ children }: { children: ReactNode }) {
  return <mark className="rounded bg-model-soft px-1 text-model">{children}</mark>;
}

/**
 * The clean sample, start to finish: violet marks what a model read, blue what code
 * checked, the same colors the run graph uses.
 */
function WorkedExample() {
  const facts: { kind: SpanKind; label: string; value: string }[] = [
    { kind: "llm", label: "Pet", value: "Biscuit, a Beagle on file" },
    { kind: "llm", label: "Stay", value: "Boarding, March 24 to 27" },
    { kind: "code", label: "Vaccines", value: "Rabies, DHPP, and Bordetella cover all three nights" },
    { kind: "code", label: "Kennel", value: "One free for his size" },
  ];
  return (
    <figure aria-label="One request from start to finish" className="rounded-2xl bg-surface p-5 ring-1 ring-rule sm:p-7">
      <p className="text-sm text-faint">Avery Lindqvist wrote, with a photo attached:</p>
      <blockquote className="mt-2 font-display text-xl leading-snug font-medium sm:text-2xl">
        Hi! Could <Read>Biscuit</Read> <Read>board</Read> with you from <Read>March 24 to March 27</Read>?
        He eats grain-free food twice a day. His <Read>vaccine card</Read> is attached.
      </blockquote>

      <dl className="mt-6 space-y-2.5 border-t border-rule pt-5 text-sm">
        {facts.map((f) => (
          <div key={f.label} className="grid grid-cols-[1rem_5rem_minmax(0,1fr)] items-baseline">
            <KindDot kind={f.kind} />
            <dt className="text-muted">{f.label}</dt>
            <dd>{f.value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-rule pt-5 text-sm">
        <StateTag status="sent" />
        <span>Every check passed, so PawDesk sent the reply with no one on staff involved.</span>
      </div>

      <figcaption className="mt-5 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <KindDot kind="llm" /> A model read it
        </span>
        <span className="inline-flex items-center gap-1.5">
          <KindDot kind="code" /> Code checked it
        </span>
      </figcaption>
    </figure>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-heading`} className="mt-28 scroll-mt-6">
      <h2 id={`${id}-heading`} className="text-3xl font-bold">
        {title}
      </h2>
      {children}
    </section>
  );
}

function HowItWorks() {
  return (
    <Section id="how" title="How a request moves">
      <p className="mt-3 max-w-2xl leading-relaxed text-muted">
        Code sets the order of the steps and makes each decision. The models read messy input and
        write text for people.
      </p>

      <ol className="mt-10 max-w-3xl">
        {STEPS.map((step, i) => (
          <li key={step.title} className="relative grid grid-cols-[2.5rem_minmax(0,1fr)] pb-9 last:pb-0">
            {i < STEPS.length - 1 && <span aria-hidden className="absolute top-8 bottom-1 left-[0.9rem] w-px bg-rule" />}
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-surface font-display text-sm font-semibold ring-1 ring-rule">
              {i + 1}
            </span>
            <div>
              <h3 className="flex flex-wrap items-baseline gap-x-3 text-xl font-semibold">
                {step.title}
                <span className="inline-flex items-center gap-2 font-sans text-sm font-normal text-muted">
                  {step.who.map((k) => (
                    <span key={k} className="inline-flex items-center gap-1.5">
                      <KindDot kind={k} />
                      {WHO[k]}
                    </span>
                  ))}
                </span>
              </h3>
              <p className="mt-1.5 leading-relaxed text-muted">{step.text}</p>
            </div>
          </li>
        ))}
      </ol>

      <h3 className="mt-16 text-xl font-semibold">What the tests hold it to</h3>
      <ul className="mt-5 grid max-w-4xl gap-x-10 gap-y-5 leading-relaxed text-muted md:grid-cols-2">
        {GUARANTEES.map((g, i) => (
          <li key={i} className="flex gap-3">
            <span aria-hidden className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-kennel" />
            <span>{g}</span>
          </li>
        ))}
      </ul>
      <p className="mt-8 max-w-2xl leading-relaxed text-muted">
        On 16 labeled messages, three of them prompt-injection attempts, intake got all 16 right and
        sent all three attempts to a person. The <Link href="/evals" className={link}>evals page</Link>{" "}
        has that report and the others.
      </p>
    </Section>
  );
}

function About() {
  return (
    <Section id="about" title="Why I built PawDesk">
      <div className="mt-5 max-w-2xl space-y-4 text-lg leading-relaxed">
        <p>
          I built PawDesk to show that I work across the stack and use AI tools every day
          while checking what they produce.
        </p>
        <p className="text-muted">
          I wanted one working product that shows both, small enough that I can walk you through any
          part of it. The table pairs the posting&apos;s skills with the parts of PawDesk that use them.
        </p>
      </div>

      <table className="mt-10 w-full max-w-4xl border-t border-ink text-left">
        <thead className="sr-only">
          <tr>
            <th scope="col">Skill from the posting</th>
            <th scope="col">Where PawDesk uses it</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {POSTING.map((row) => (
            <tr key={row.skill} className="flex flex-col gap-1 py-4 sm:table-row">
              <th scope="row" className="pr-8 align-top font-display font-semibold sm:w-60 sm:py-4">
                {row.skill}
              </th>
              <td className="align-top leading-relaxed text-muted sm:py-4">{row.here}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function Method() {
  const { totals } = walkthrough;
  const tests = totals.tests.backend + totals.tests.frontend + (totals.tests.e2e ?? 0);
  const changeSteps: ReactNode[] = [
    "An AI assistant drafts the change as an OpenSpec proposal: requirements with when/then scenarios, a design that weighs the options, and a task list.",
    "I read the proposal, push back where I disagree, and approve it before any code exists.",
    "The code goes in as small commits. Lint, type checks, and the tests pass before each one.",
    <>
      Each test names the requirement it proves, and the build fails when a requirement has no
      passing test. In the latest test run, {totals.verified} of {totals.requirements} requirements
      pass, across{" "}
      {tests} tests.
    </>,
  ];
  return (
    <Section id="method" title="Working with an AI assistant">
      <p className="mt-3 max-w-2xl leading-relaxed text-muted">
        I build PawDesk one change at a time, and each change goes through the same four steps.
        Choices that outlast one change get a numbered decision record; there are{" "}
        {walkthrough.decisions.length} so far.
      </p>
      <ol className="mt-8 max-w-2xl list-decimal space-y-3 pl-6 leading-relaxed marker:font-display marker:font-semibold marker:text-kennel">
        {changeSteps.map((s, i) => (
          <li key={i} className="pl-2">
            {s}
          </li>
        ))}
      </ol>
      <p className="mt-8 max-w-2xl leading-relaxed text-muted">
        <Link href="/build" className={link}>How it was built</Link> lists each of the{" "}
        {totals.changes} changes with its requirements, the tests behind them, and their latest
        results.
      </p>
    </Section>
  );
}
