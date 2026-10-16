import Link from "next/link";
import { type ReactNode, Suspense } from "react";

import { DemoPanel } from "@/components/demo-panel";
import { KindDot, Loading, StateTag } from "@/components/ui";
import rules from "@/content/booking-rules.json";
import data from "@/content/walkthrough.json";
import { backendJson } from "@/lib/backend";
import { certificateSrc } from "@/lib/demo";
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
    text: "The intake and records agents read the message and the vaccine card at the same time.",
  },
  {
    title: "Check",
    who: ["code"],
    text: "Code compares each required vaccine's expiry date with the stay, then looks for a free kennel that fits the pet's size.",
  },
  {
    title: "Find options",
    who: ["llm", "tool"],
    text: "If a check fails, the resolver suggests a fix and code checks it again. If every check passes, this step is skipped.",
  },
  {
    title: "Write the reply",
    who: ["llm"],
    text: "The reply agent drafts the answer to the pet parent from the facts code checked.",
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

const AGENTS: { name: string; calls: string; reads: string; returns: string; checks: string }[] = [
  {
    name: "Intake",
    calls: "One model call",
    reads: "The pet parent's message. Code scans it for instruction-like text, such as “ignore your rules”, before the model sees it.",
    returns: "The pet's name, the service, the dates, any special notes, a confidence score, and anything it found unclear.",
    checks: "Matches the pet to one on file and checks the dates. Instruction-like text, a confidence under 0.7, or anything unclear sends the request to a person.",
  },
  {
    name: "Records",
    calls: "One model call",
    reads: "The photo of the vaccine card.",
    returns: "Each vaccine with the date given and the expiry date, the pet's name as printed, whether the photo was readable, and a confidence score.",
    checks: "Rejects impossible dates and unknown vaccines, and compares the printed name with the booked pet. An unreadable card or a confidence under 0.7 sends the request to a person.",
  },
  {
    name: "Resolver",
    calls: "A loop of up to 6 model calls",
    reads: "Only values code built, such as which vaccine expired. It never sees the pet parent's message, and code starts it only for problems it can work on.",
    returns: "One offer: other dates, a larger kennel, or a request for an updated vaccine record. It finds them with 3 read-only tools, at most 12 calls.",
    checks: "Runs the checks again on every option. The resolver can't book anything, and a person reviews its offer.",
  },
  {
    name: "Reply",
    calls: "One model call",
    reads: "The checked facts and the options code verified. Like the resolver, it never sees the original message.",
    returns: "A subject line and the body of the reply.",
    checks: "Flags any date the checks didn't confirm, any money amount, and words like “booked” or “confirmed” the facts don't support. A flagged draft goes to a person.",
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

      <BookingRules />
      <Agents />
      <HowItWorks />
      <Method />
      <Skills />

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

const FEATURES: { skill: string; what: string }[] = [
  { skill: "Python and FastAPI", what: "the API and the workflow that runs each request" },
  { skill: "React and TypeScript", what: "this dashboard, which shows each run live" },
  { skill: "PostgreSQL and Docker", what: "migrations, and the full stack in Docker Compose" },
  { skill: "Testing and CI", what: "pytest, Vitest, and Playwright, run by GitHub Actions" },
  { skill: "AI-assisted development", what: "each change specified, reviewed, and tested before it ships" },
];

function Intro() {
  return (
    <section className="mb-20 grid items-start gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-12">
      <div className="max-w-2xl lg:pt-4">
        <h1 className="text-4xl leading-[1.05] font-semibold sm:text-5xl">
          PawDesk handles pet care bookings and asks a person when it isn&apos;t sure.
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-muted">
          PawDesk is a multi-agent workflow for a kennel&apos;s booking inbox. AI agents read each
          request and the photo of the vaccine card, plain code checks the vaccines and finds a free
          kennel, and another agent writes the reply.
        </p>
        <p className="mt-4 text-lg leading-relaxed text-muted">
          When every check passes, PawDesk books the stay and sends the reply. When something is
          unclear or breaks a rule, the request waits in a review queue for someone on staff.
        </p>
        <p className="mt-4 text-lg leading-relaxed">
          I built it to show full stack work and AI-driven
          development, with the skills the posting lists:
        </p>
        <ul className="mt-4 space-y-2">
          {FEATURES.map((f) => (
            <li key={f.skill} className="flex gap-3 leading-relaxed">
              <span aria-hidden className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-kennel" />
              <span>
                <span className="font-medium">{f.skill}:</span> <span className="text-muted">{f.what}</span>
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-3">
          <a href="#try" className="rounded-full bg-ink px-5 py-2.5 font-medium text-white hover:brightness-125">
            Try a request
          </a>
          <a href="#how" className={link}>
            How it works
          </a>
          <a href="#skills" className={link}>
            Skills in detail
          </a>
        </div>
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
      <blockquote className="mt-2 font-display text-xl leading-snug font-medium sm:text-2xl lg:text-xl">
        Hi! Could <Read>Biscuit</Read> <Read>board</Read> with you from <Read>March 24 to March 27</Read>?
        He eats grain-free food twice a day. His <Read>vaccine card</Read> is attached.
      </blockquote>

      <figure className="mt-5">
        {/* eslint-disable-next-line @next/next/no-img-element -- the clean sample's PNG from the API, the file the request sends */}
        <img
          src={certificateSrc({ sample: "clean" })}
          alt="Biscuit's vaccine card, listing Rabies, DHPP, Bordetella, and Canine influenza with the dates given and expiry dates"
          width={780}
          height={338}
          className="h-auto w-full rounded-lg bg-white ring-2 ring-model-soft"
        />
        <figcaption className="mt-2 inline-flex items-center gap-1.5 text-xs text-muted">
          <KindDot kind="llm" /> The attached card, read by the records agent
        </figcaption>
      </figure>

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

type VaccineId = keyof typeof rules.vaccine_names;
const vaccineList = (ids: string[]) => ids.map((id) => rules.vaccine_names[id as VaccineId]).join(", ");

function BookingRules() {
  const cell = "block align-top leading-relaxed lg:table-cell lg:py-5 lg:pr-6";
  const label = "block text-xs font-medium text-faint lg:hidden";
  return (
    <Section id="rules" title="Booking rules">
      <p className="mt-3 max-w-2xl leading-relaxed text-muted">
        Code checks each rule below; no model decides any of them. They&apos;re the demo
        facility&apos;s rules, and each facility sets its own vaccine lists per service and species.
      </p>

      <h3 className="mt-10 text-xl font-semibold">Services</h3>
      <table className="mt-4 w-full max-w-3xl border-t border-ink text-left text-sm lg:max-w-none">
        <thead className="hidden lg:table-header-group">
          <tr className="text-xs text-faint">
            <th scope="col" className="w-36 py-3 pr-6 font-medium">Service</th>
            <th scope="col" className="py-3 pr-6 font-medium">Visit</th>
            <th scope="col" className="py-3 pr-6 font-medium">Kennel</th>
            <th scope="col" className="py-3 pr-6 font-medium">Dogs need</th>
            <th scope="col" className="py-3 font-medium">Cats need</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule border-t border-rule">
          {rules.services.map((s) => (
            <tr key={s.service} className="flex flex-col gap-3 py-5 lg:table-row">
              <th scope="row" className="align-top font-display text-lg font-semibold lg:py-5 lg:pr-6">
                {s.label}
              </th>
              <td className={`${cell} text-muted`}>
                <span className={label}>Visit</span>
                {s.visit}
              </td>
              <td className={`${cell} text-muted`}>
                <span className={label}>Kennel</span>
                {s.kennel ? "A free kennel of the pet's size, reserved when the reply goes out" : "None"}
              </td>
              <td className={cell}>
                <span className={label}>Dogs need</span>
                {vaccineList(s.vaccines.dog)}
              </td>
              <td className={`${cell} lg:pr-0`}>
                <span className={label}>Cats need</span>
                {vaccineList(s.vaccines.cat)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-14 grid gap-x-14 gap-y-12 lg:grid-cols-2">
        <div>
          <h3 className="text-xl font-semibold">When a vaccine counts</h3>
          <p className="mt-3 leading-relaxed text-muted">
            The pet is on site every day from drop-off through pickup. A shot counts if the pet got
            it on or before drop-off and it expires on or after pickup day. Code looks at the records
            on file and the ones the records agent read from the card, and one covering record is
            enough.
          </p>
          <CoverageStrip />
          <p className="mt-6 leading-relaxed text-muted">
            When no record covers the stay, code names the reason: no record, expired before
            drop-off, expires during the stay, or given after drop-off. A card with no expiry date for
            a required shot goes to a person.
          </p>
        </div>

        <div className="space-y-10">
          <div>
            <h3 className="text-xl font-semibold">Kennel sizes</h3>
            <p className="mt-3 leading-relaxed text-muted">
              Code sets a pet&apos;s size from its species and weight and searches only kennels of
              that size. Cats get cat kennels at any weight. Dogs:
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-rule ring-1 ring-rule sm:grid-cols-4">
              {rules.dog_sizes.map((band, i) => (
                <div key={band.size} className="bg-surface px-4 py-3">
                  <dt className="font-display font-semibold">{band.label}</dt>
                  <dd className="mt-0.5 text-sm text-muted">{bandRange(i)}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 leading-relaxed text-muted">
              A kennel is free when none of the stay&apos;s nights is booked. The nights run from
              drop-off to the night before pickup, so a stay that ends March 27 doesn&apos;t block one
              that starts March 27.
            </p>
          </div>

          <div>
            <h3 className="text-xl font-semibold">Dates</h3>
            <p className="mt-3 leading-relaxed text-muted">
              A request can start today or up to {rules.booking_horizon_days} days ahead. Boarding
              has to end at least one day after it starts. Daycare and grooming start and end on the
              same date.
            </p>
          </div>
        </div>
      </div>

      <h3 className="mt-14 text-xl font-semibold">When a rule isn&apos;t met</h3>
      <p className="mt-3 max-w-2xl leading-relaxed text-muted">
        A failed rule, or anything the intake or records agent flags, takes the request off the
        automatic path. If the resolver can work on the problem, it suggests other dates, a larger
        kennel, or an updated vaccine record. Either way, someone on staff decides before a reply
        goes out.
      </p>
    </Section>
  );
}

/** A dog weight band in words, from the band before it: "20 to under 50 lb". */
function bandRange(i: number): string {
  const band = rules.dog_sizes[i];
  const from = i === 0 ? null : rules.dog_sizes[i - 1].under_lb;
  if (from === null) return `Under ${band.under_lb} lb`;
  if (band.under_lb === null) return `${from} lb and up`;
  return `${from} to under ${band.under_lb} lb`;
}

/** A hypothetical dog's stay, with one shot that covers it and one that doesn't. */
function CoverageStrip() {
  const days = [23, 24, 25, 26, 27, 28];
  const onSite = (d: number) => d >= 24 && d <= 27;
  const shots = [
    { name: "Bordetella, expires April 2", verdict: "Covers the stay", ok: true, until: 28 },
    { name: "DHPP, expires March 26", verdict: "Expires during the stay", ok: false, until: 26 },
  ];
  const lane = (children: ReactNode) => (
    <div className="relative grid grid-cols-6">
      {days.map((d) => (
        <span key={d} aria-hidden className={`h-7 ${onSite(d) ? "bg-kennel-soft" : ""}`} />
      ))}
      {children}
    </div>
  );
  return (
    <figure
      aria-label="Two vaccines against a hypothetical dog's stay from March 24 to 27"
      className="mt-6 rounded-2xl bg-surface p-5 ring-1 ring-rule"
    >
      <div className="grid grid-cols-6 text-center text-xs text-muted">
        {days.map((d) => (
          <span key={d} className={`py-1 ${onSite(d) ? "font-medium text-kennel" : ""}`}>
            Mar {d}
          </span>
        ))}
      </div>
      {lane(
        <span className="absolute inset-y-0 right-[16.67%] left-[16.67%] flex items-center justify-center text-xs font-medium text-kennel">
          Dog on site
        </span>,
      )}
      {shots.map((shot) => (
        <div key={shot.name} className="mt-3">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
            <span>{shot.name}</span>
            <span className={`text-xs font-medium ${shot.ok ? "text-kennel" : "text-error"}`}>{shot.verdict}</span>
          </div>
          {lane(
            <span
              aria-hidden
              className={`absolute inset-y-2.5 left-0 ${shot.ok ? "rounded-l-full bg-kennel" : "rounded-full bg-error"}`}
              style={{ width: `${((days.indexOf(shot.until) + 1) * 100) / days.length}%` }}
            />,
          )}
        </div>
      ))}
      <figcaption className="mt-4 text-xs leading-relaxed text-muted">
        A hypothetical dog: drop-off March 24, pickup March 27. The DHPP shot runs out before
        pickup, so it fails even though it was valid at drop-off.
      </figcaption>
    </figure>
  );
}

function Agents() {
  const cell = "block align-top leading-relaxed text-muted lg:table-cell lg:py-5 lg:pr-6";
  const label = "block text-xs font-medium text-faint lg:hidden";
  return (
    <Section id="agents" title="The agents">
      <p className="mt-3 max-w-2xl leading-relaxed text-muted">
        Four parts of PawDesk use a model. Each one reads something, returns a fixed set of fields,
        and hands them to code that checks them before they count. None of them can approve a
        booking.
      </p>

      <table className="mt-10 w-full max-w-3xl border-t border-ink text-left text-sm lg:max-w-none">
        <thead className="hidden lg:table-header-group">
          <tr className="text-xs text-faint">
            <th scope="col" className="w-44 py-3 pr-6 font-medium">Agent</th>
            <th scope="col" className="py-3 pr-6 font-medium">Reads</th>
            <th scope="col" className="py-3 pr-6 font-medium">Returns</th>
            <th scope="col" className="py-3 font-medium">What code checks</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule border-t border-rule">
          {AGENTS.map((a) => (
            <tr key={a.name} className="flex flex-col gap-3 py-5 lg:table-row">
              <th scope="row" className="align-top font-normal lg:py-5 lg:pr-6">
                <span className="flex items-center gap-2 font-display text-lg font-semibold">
                  <KindDot kind="llm" />
                  {a.name}
                </span>
                <span className="mt-0.5 block text-xs text-muted">{a.calls}</span>
              </th>
              <td className={cell}>
                <span className={label}>Reads</span>
                {a.reads}
              </td>
              <td className={cell}>
                <span className={label}>Returns</span>
                {a.returns}
              </td>
              <td className={`${cell} lg:pr-0`}>
                <span className={label}>What code checks</span>
                {a.checks}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
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

function Skills() {
  return (
    <Section id="skills" title="Skills from the posting">
      <p className="mt-3 max-w-2xl leading-relaxed text-muted">
        The posting asks for someone who works across the stack and uses AI tools every day while
        checking what they produce. Each row pairs one of its skills with the parts of PawDesk that
        use it.
      </p>

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
