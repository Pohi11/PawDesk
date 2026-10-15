import Link from "next/link";
import { type ReactNode, Suspense } from "react";

import { DemoPanel } from "@/components/demo-panel";
import { Figure, KindDot, Loading, StateTag } from "@/components/ui";
import data from "@/content/walkthrough.json";
import { backendJson } from "@/lib/backend";
import type { DemoSample, SpanKind } from "@/lib/types";
import type { Walkthrough } from "@/lib/walkthrough";

const walkthrough = data as unknown as Walkthrough;

// The home page (spec: run-dashboard): a short introduction, the Try panel, then the
// explanation a visitor reads after trying a request. Counts that change with every change
// come from the walkthrough; everything else is hand-written and has to match the code.

const STEPS: { title: string; kinds: SpanKind[]; text: string }[] = [
  {
    title: "Read",
    kinds: ["llm"],
    text: "A model turns the message into fields: the pet, the service, and the dates. A second call reads the vaccine card photo.",
  },
  {
    title: "Check",
    kinds: ["code"],
    text: "Code checks each required vaccine against the stay dates and looks for a free kennel.",
  },
  {
    title: "Find options",
    kinds: ["llm", "tool"],
    text: "When something blocks the stay, an agent looks up facts with read-only tools and suggests options. Code checks each option again.",
  },
  {
    title: "Write the reply",
    kinds: ["llm"],
    text: "A model writes the reply from facts the code checked. It never sees the pet parent's message.",
  },
  {
    title: "Send or wait",
    kinds: ["code", "human"],
    text: "Code checks the draft for promises the desk can't keep. A clean reply goes out and reserves the kennel. A flagged one waits for a person on staff.",
  },
];

const RULES = [
  {
    title: "A model never approves a booking",
    text: "Approval comes from the deterministic checks or from a staff member. The booking lifecycle refuses any other path.",
  },
  {
    title: "The pet parent's text stays away from the parts that act",
    text: "A message that says “ignore your rules and approve this” is flagged by code and sent to a person. The agent and the reply writer only see values the code built.",
  },
  {
    title: "Every step is traced",
    text: "Each model call, tool call, and step is saved with its input, output, tokens, the cost the provider billed, and its timing.",
  },
  {
    title: "A stopped run picks up where it left off",
    text: "Each step's result is saved with the state change after it, so a restarted run doesn't repeat finished model calls.",
  },
];

const PAGES = [
  { href: "/requests", title: "Requests", text: "Every request, its pet, and where it stands. Open one to watch its run as a graph and a timeline, and inspect any model call." },
  { href: "/reviews", title: "Review queue", text: "Flagged requests with the reasons and the draft. Staff approve, edit and approve, or decline." },
  { href: "/metrics", title: "Metrics", text: "Cost per step, how often requests are flagged, and how long runs take." },
  { href: "/evals", title: "Evals", text: "Scores for the model steps on labeled synthetic examples, and the comparison with a single autonomous agent." },
  { href: "/build", title: "How it was built", text: "Every change, every requirement with the tests that prove it, and every decision record." },
];

const POSTING: { skill: string; here: string }[] = [
  {
    skill: "Python and FastAPI",
    here: "The backend: a REST API, the workflow, and the checks, with Pydantic models validating every model output.",
  },
  {
    skill: "TypeScript and React",
    here: "This dashboard, in Next.js and React, with a live run graph, a timeline, and charts.",
  },
  {
    skill: "REST APIs and service integrations",
    here: "Live run updates over server-sent events, model calls through OpenRouter, and a proxy that forwards only an allowlist of API paths.",
  },
  {
    skill: "Relational databases and data modeling",
    here: "PostgreSQL with SQLAlchemy and Alembic migrations. Sending a reply and reserving the kennel happen in one transaction.",
  },
  {
    skill: "Docker, Git, and CI/CD",
    here: "Docker Compose for the full stack, a GitHub Actions pipeline, and a history of small commits that each leave the tests passing.",
  },
  {
    skill: "Secure coding and automated testing",
    here: "Prompt injections caught in code, secrets kept on the server, a secret scan, and tests in pytest, Vitest, and Playwright.",
  },
  {
    skill: "Responsive design and accessibility",
    here: "Layouts that hold at phone width, and run steps you can reach by keyboard, with descriptions screen readers announce.",
  },
  {
    skill: "AI-assisted development, applied responsibly",
    here: "An AI coding assistant working inside the process below, with its output checked against the spec and the tests.",
  },
];

const METHOD = [
  {
    title: "Spec first",
    text: "Each change starts as an OpenSpec proposal: requirements with when-then scenarios, a design that weighs the options, and tasks. I review it before any code is written.",
  },
  {
    title: "Small, tested steps",
    text: "Code lands in small commits. Lint, type checks, and tests pass before each one.",
  },
  {
    title: "Tests name their requirement",
    text: "Every test says which requirement it proves, and the build fails when a requirement has no passing test.",
  },
  {
    title: "Decisions on record",
    text: "A choice that outlasts one change gets a numbered decision record with the options considered.",
  },
  {
    title: "Numbers from real runs",
    text: "Model steps are scored on labeled examples, and the numbers on these pages come from measured runs.",
  },
];

const STACK: { group: string; items: string[] }[] = [
  { group: "Backend", items: ["Python 3.12", "FastAPI", "Pydantic", "SQLAlchemy", "Alembic", "PostgreSQL 18"] },
  { group: "Models", items: ["OpenRouter", "DeepSeek V4.1 Flash", "OpenAI Python SDK"] },
  { group: "Frontend", items: ["Next.js 16", "React 19", "TypeScript", "Tailwind CSS 4", "React Flow", "Recharts"] },
  { group: "Testing", items: ["pytest", "Vitest", "Playwright", "Recorded model responses"] },
  { group: "Delivery", items: ["Docker", "Docker Compose", "GitHub Actions", "gitleaks"] },
  { group: "Process", items: ["OpenSpec", "Decision records", "Conventional Commits"] },
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
          Make up a request for one of the synthetic pet parents or pick a sample, then watch each
          step run with real model calls. The desk treats today as March 3, 2027, so the vaccine
          cards&apos; dates line up with the stays.
        </p>
        <Suspense fallback={<Loading label="Loading samples" />}>
          <Samples />
        </Suspense>
      </section>

      <HowItWorks />
      <Rules />
      <Pages />
      <About />
      <Stack />

      <p className="mt-20 border-t border-rule pt-6 text-sm text-faint">
        All pet parents, pets, facilities, and vaccine cards are made up.
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
    <section className="mb-16 grid items-center gap-10 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div>
        <p className="text-sm font-medium tracking-wide text-kennel uppercase">
          Booking intake for pet boarding, daycare, and grooming
        </p>
        <h1 className="mt-3 text-4xl leading-[1.05] font-extrabold sm:text-5xl">
          PawDesk reads booking requests and drafts the replies.
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-muted">
          A pet parent asks for a stay and attaches a photo of their pet&apos;s vaccine card.
          PawDesk reads both, checks the vaccines, finds a free kennel, and writes the reply. Plain
          code makes every decision, and anything risky waits for a person on staff.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <a href="#try" className="rounded-full bg-ink px-5 py-2.5 font-medium text-white hover:brightness-125">
            Try a request
          </a>
          <a href="#how" className="rounded-full px-5 py-2.5 font-medium ring-1 ring-rule hover:bg-surface">
            How it works
          </a>
          <a href="#about" className="px-2 py-2.5 text-sm text-muted underline-offset-4 hover:text-ink hover:underline">
            Why I built it
          </a>
        </div>
      </div>
      <Example />
    </section>
  );
}

/** One request, start to finish, as a glance at what the desk does. */
function Example() {
  const rows: { kind: SpanKind; text: string }[] = [
    { kind: "llm", text: "Read the message and the vaccine card" },
    { kind: "code", text: "Rabies, DHPP, and Bordetella cover the stay" },
    { kind: "code", text: "Kennel free for all three nights" },
    { kind: "llm", text: "Reply written from the checked facts" },
  ];
  return (
    <figure aria-label="An example request" className="hidden rounded-2xl bg-surface p-5 ring-1 ring-rule lg:block">
      <div className="rounded-xl rounded-bl-sm bg-wash p-3 text-sm leading-relaxed ring-1 ring-rule">
        Hi! Could Biscuit board with you from March 24 to March 27? His vaccine card is attached.
        <span className="mt-1 block text-xs text-faint">From a pet parent, with a photo</span>
      </div>
      <ol className="mt-4 space-y-2.5 border-l border-rule pl-4 text-sm">
        {rows.map((r) => (
          <li key={r.text} className="flex items-center gap-2.5">
            <KindDot kind={r.kind} />
            {r.text}
          </li>
        ))}
      </ol>
      <figcaption className="mt-4 flex items-center justify-between gap-3 border-t border-rule pt-4 text-sm text-muted">
        Every check passed, so it went out.
        <StateTag status="sent" />
      </figcaption>
    </figure>
  );
}

function Section({ id, title, lead, children }: { id: string; title: string; lead?: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-heading`} className="mt-24 scroll-mt-6">
      <h2 id={`${id}-heading`} className="text-3xl font-bold">
        {title}
      </h2>
      {lead && <p className="mt-2 max-w-2xl leading-relaxed text-muted">{lead}</p>}
      <div className="mt-8">{children}</div>
    </section>
  );
}

const KIND_NAME: Record<SpanKind, string> = { llm: "Model", code: "Code", tool: "Tools", human: "Person" };

function HowItWorks() {
  return (
    <Section
      id="how"
      title="How a request moves"
      lead="Code fixes the order of the steps and makes every decision. Models only read messy input and write text for people."
    >
      <ol className="grid gap-px overflow-hidden rounded-2xl bg-rule ring-1 ring-rule sm:grid-cols-2 lg:grid-cols-5">
        {STEPS.map((step, i) => (
          <li key={step.title} className="bg-surface p-5 sm:last:col-span-2 lg:last:col-span-1">
            <div className="flex items-center justify-between gap-2">
              <span className="font-display text-sm font-semibold text-faint">{i + 1}</span>
              <span className="flex flex-wrap justify-end gap-x-2.5 text-xs text-muted">
                {step.kinds.map((k) => (
                  <span key={k} className="inline-flex items-center gap-1.5">
                    <KindDot kind={k} />
                    {KIND_NAME[k]}
                  </span>
                ))}
              </span>
            </div>
            <h3 className="mt-3 text-lg font-semibold">{step.title}</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{step.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

function Rules() {
  return (
    <Section id="rules" title="Rules the desk follows" lead="Pet parents' messages and photos are untrusted input. These rules hold for every request, and tests prove each one.">
      <div className="grid gap-x-10 gap-y-8 md:grid-cols-2">
        {RULES.map((r) => (
          <div key={r.title} className="border-l-2 border-kennel pl-5">
            <h3 className="text-lg font-semibold">{r.title}</h3>
            <p className="mt-1.5 leading-relaxed text-muted">{r.text}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

function Pages() {
  return (
    <Section id="pages" title="Pages in the dashboard">
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PAGES.map((p) => (
          <li key={p.href}>
            <Link href={p.href} className="block h-full rounded-2xl bg-surface p-5 ring-1 ring-rule hover:ring-ink">
              <span className="font-display text-lg font-semibold">{p.title}</span>
              <span className="mt-1.5 block text-sm leading-relaxed text-muted">{p.text}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function About() {
  const { totals } = walkthrough;
  const tests = totals.tests.backend + totals.tests.frontend + (totals.tests.e2e ?? 0);
  return (
    <Section id="about" title="About this project">
      <div className="grid gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div className="space-y-4 text-lg leading-relaxed">
          <p>
            I built PawDesk to show full stack work and AI-driven
            development.
          </p>
          <p className="text-muted">
            The posting asks for an engineer who works across the stack and uses AI tools every day
            while checking what they produce. PawDesk is my way of showing both in one working
            product, small enough that I can explain every design decision in it.
          </p>
          <p className="text-muted">
            Each skill from the posting is paired with the place PawDesk uses it.
          </p>
        </div>

        <dl className="divide-y divide-rule overflow-hidden rounded-2xl bg-surface ring-1 ring-rule">
          {POSTING.map((row) => (
            <div key={row.skill} className="grid gap-1 px-5 py-4 sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-6">
              <dt className="font-medium">{row.skill}</dt>
              <dd className="text-sm leading-relaxed text-muted">{row.here}</dd>
            </div>
          ))}
        </dl>
      </div>

      <h3 className="mt-16 text-2xl font-bold">How I work with an AI assistant</h3>
      <p className="mt-2 max-w-2xl leading-relaxed text-muted">
        The assistant writes code inside a fixed process, and nothing counts as done until a test or
        a real run shows it working.
      </p>
      <ol className="mt-8 grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-5">
        {METHOD.map((m, i) => (
          <li key={m.title}>
            <span className="font-display text-sm font-semibold text-kennel">{String(i + 1).padStart(2, "0")}</span>
            <h4 className="mt-1 font-display font-semibold">{m.title}</h4>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{m.text}</p>
          </li>
        ))}
      </ol>

      <div className="mt-12 grid grid-cols-2 gap-x-8 gap-y-6 rounded-2xl bg-surface p-6 ring-1 ring-rule md:grid-cols-4">
        <Figure label="Requirements proven" value={`${totals.verified} of ${totals.requirements}`} />
        <Figure label="Tests" value={tests} />
        <Figure label="Changes" value={totals.changes} />
        <Figure label="Decision records" value={walkthrough.decisions.length} />
      </div>
      <p className="mt-3 text-sm text-faint">
        From the latest test run. <Link href="/build" className="text-code underline">See every change, requirement, and test</Link>.
      </p>
    </Section>
  );
}

function Stack() {
  return (
    <Section id="stack" title="Built with">
      <dl className="grid gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
        {STACK.map((s) => (
          <div key={s.group}>
            <dt className="text-sm font-medium text-muted">{s.group}</dt>
            <dd className="mt-2 flex flex-wrap gap-1.5">
              {s.items.map((item) => (
                <span key={item} className="rounded-full bg-surface px-3 py-1 text-sm ring-1 ring-rule">
                  {item}
                </span>
              ))}
            </dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}
