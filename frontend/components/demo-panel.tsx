"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  type DemoSource,
  type GeneratedRequest,
  certificateSrc,
  generateRequest,
  generatedPet,
  rememberName,
  DemoRefused,
  submitDemo,
} from "@/lib/demo";
import { formatService, formatStay } from "@/lib/format";
import type { DemoSample, PetFields } from "@/lib/types";

import { PetAvatar } from "./pet-avatar";

const GENERATED = "generated";
const RECENT_KEY = "pawdesk.recent-demo-names";

// Recent names live in session storage, so they survive opening a run and coming back. The
// page works the same without storage (private windows, blocked site data).
function loadRecent(): string[] {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((n): n is string => typeof n === "string") : [];
  } catch {
    return [];
  }
}

interface Summary {
  pet: PetFields;
  heading: string;
  detail: string;
}

// The same summary opens every preview, whether the request is made up or a fixed sample.
function generatedSummary(r: GeneratedRequest): Summary {
  return {
    pet: generatedPet(r),
    heading: `${r.pet}, ${formatService(r.service).toLowerCase()}, ${formatStay(r.start_date, r.end_date)}`,
    detail: `From ${r.owner}. ${r.breed}, ${r.weight_lb} lb. ${r.scenario_text}`,
  };
}

function sampleSummary(s: DemoSample): Summary {
  const parts = [
    s.owner && `From ${s.owner}.`,
    s.pet_breed && s.weight_lb !== null && `${s.pet_breed}, ${s.weight_lb} lb.`,
    s.card_text,
  ];
  return {
    pet: s,
    heading: `${s.pet}, ${formatService(s.service).toLowerCase()}, ${formatStay(s.start_date, s.end_date)}`,
    detail: parts.filter(Boolean).join(" "),
  };
}

function saveRecent(names: string[]) {
  try {
    sessionStorage.setItem(RECENT_KEY, JSON.stringify(names));
  } catch {
    // Not kept; the server still skips every name on file.
  }
}

export function DemoPanel({ samples }: { samples: DemoSample[] }) {
  const router = useRouter();
  const [chosen, setChosen] = useState<string>(GENERATED);
  const [generated, setGenerated] = useState<GeneratedRequest | null>(null);
  const [messages, setMessages] = useState<Record<string, string>>(() =>
    Object.fromEntries(samples.map((s) => [s.id, s.message])),
  );
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Not rendered, so reading storage while rendering can't cause a hydration mismatch.
  const [recent, setRecent] = useState<string[]>(loadRecent);

  const sample = samples.find((s) => s.id === chosen);
  const source: DemoSource | null =
    chosen === GENERATED ? (generated ? { seed: generated.seed } : null) : sample ? { sample: sample.id } : null;
  const original = chosen === GENERATED ? generated?.message : sample?.message;
  const messageKey = chosen === GENERATED ? `seed-${generated?.seed}` : chosen;
  const message = messages[messageKey] ?? original ?? "";
  const hasCertificate = chosen === GENERATED ? generated !== null : Boolean(sample?.certificate);
  const summary = chosen === GENERATED ? generated && generatedSummary(generated) : sample && sampleSummary(sample);

  // "Make another" always makes a new request.
  function makeOne() {
    setChosen(GENERATED);
    void generate();
  }

  // The "Make one up" choice shows the request already made up, and makes one only when there
  // is none, such as after a failed opening request (change keep-generated-request).
  function chooseGenerated() {
    setChosen(GENERATED);
    if (!generated && !busy) void generate();
  }

  // Fills the "Make one up" preview without selecting it, so a sample chosen while the opening
  // request is on its way stays chosen (change keep-chosen-sample).
  async function generate() {
    setError(null);
    setBusy(true);
    try {
      const request = await generateRequest(recent);
      const names = rememberName(recent, request.pet);
      setRecent(names);
      saveRecent(names);
      setGenerated(request);
    } catch (e) {
      setError(e instanceof Error ? `${e.message}. Is the API running?` : String(e));
    }
    setBusy(false);
  }

  // The page opens on "Make one up", so make one up at once. The ref stops React's
  // development double mount from making two and using up two names.
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void generate();
  });

  // A sent request stays "Sending" until its run opens. The page isn't unmounted then: it is
  // kept hidden with its state (cacheComponents), and React runs effect cleanups when it hides
  // it, so the panel is ready again when the visitor comes back (change send-ready-after-back).
  useEffect(() => () => setSending(false), []);

  async function send() {
    if (!source) return;
    setSending(true);
    setError(null);
    try {
      router.push(await submitDemo(source, message !== original ? message : undefined));
    } catch (e) {
      if (e instanceof DemoRefused) setError(`Not sent: ${e.message}`);
      else setError(e instanceof Error ? `Not sent: ${e.message}. Is the API running?` : String(e));
      setSending(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">Choose a request</legend>
        <button
          type="button"
          onClick={chooseGenerated}
          className={`block w-full rounded-2xl p-4 text-left ring-1 ${chosen === GENERATED ? "bg-surface ring-2 ring-ink" : "ring-rule hover:bg-surface"}`}
        >
          <span className="flex items-start gap-3">
            {generated && <PetAvatar pet={generatedPet(generated)} />}
            <span>
              <span className="block font-display text-lg font-semibold">Make one up</span>
              <span className="mt-1 block text-sm text-muted">
                A new pet for one of the pet parents, a stay, and a vaccine card to match. No name repeats one already on file.
              </span>
            </span>
          </span>
        </button>
        {samples.map((s) => (
          <label
            key={s.id}
            className={`block cursor-pointer rounded-2xl p-4 ring-1 ${chosen === s.id ? "bg-surface ring-2 ring-ink" : "ring-rule hover:bg-surface"}`}
          >
            <input type="radio" name="sample" value={s.id} checked={chosen === s.id} onChange={() => setChosen(s.id)} className="sr-only" />
            <span className="flex items-start gap-3">
              <PetAvatar pet={s} />
              <span>
                <span className="block font-display text-lg font-semibold">{s.title}</span>
                <span className="mt-1 block text-sm text-muted">{s.expect}</span>
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="rounded-2xl bg-surface p-6 ring-1 ring-rule">
        {chosen === GENERATED && !generated ? (
          <p className="text-muted">{busy ? "Making up a request" : "Choose “Make one up” to create a request."}</p>
        ) : (
          <>
            {summary && (
              <div className="mb-5 flex items-start gap-4">
                <PetAvatar pet={summary.pet} size="lg" />
                <div>
                  <p className="font-display text-xl font-semibold">{summary.heading}</p>
                  <p className="text-muted">{summary.detail}</p>
                </div>
              </div>
            )}
            <label className="block">
              <span className="text-sm font-medium">Message from the pet parent</span>
              <textarea
                className="mt-2 h-32 w-full rounded-lg bg-wash p-3 leading-relaxed ring-1 ring-rule"
                value={message}
                onChange={(e) => setMessages({ ...messages, [messageKey]: e.target.value })}
              />
            </label>
            {hasCertificate && source ? (
              <figure className="mt-4">
                {/* eslint-disable-next-line @next/next/no-img-element -- a generated PNG from the API, not a static asset */}
                <img
                  key={certificateSrc(source)}
                  src={certificateSrc(source)}
                  alt={`Vaccine certificate attached to the request${generated && chosen === GENERATED ? ` for ${generated.pet}` : ""}`}
                  className="w-full rounded-lg ring-1 ring-rule"
                />
                <figcaption className="mt-2 text-sm text-faint">The vaccine card sent with this request.</figcaption>
              </figure>
            ) : (
              <p className="mt-4 text-sm text-faint">No vaccine card is attached to this request.</p>
            )}
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={busy || sending || !message.trim() || !source}
                onClick={send}
                className="rounded-full bg-ink px-6 py-2.5 font-medium text-white disabled:opacity-40"
              >
                {sending ? "Sending" : "Send and watch it run"}
              </button>
              {chosen === GENERATED && (
                <button type="button" disabled={busy || sending} onClick={makeOne} className="rounded-full px-5 py-2.5 ring-1 ring-rule hover:bg-wash disabled:opacity-40">
                  Make another
                </button>
              )}
            </div>
          </>
        )}
        {error && <p className="mt-3 text-error">{error}</p>}
      </div>
    </div>
  );
}
