"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  type DemoSource,
  type GeneratedRequest,
  certificateSrc,
  generateRequest,
  rememberName,
  submitDemo,
} from "@/lib/demo";
import { formatService, formatStay } from "@/lib/format";
import type { DemoSample } from "@/lib/types";

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

function saveRecent(names: string[]) {
  try {
    sessionStorage.setItem(RECENT_KEY, JSON.stringify(names));
  } catch {
    // Not kept; the server still skips every name on file.
  }
}

export function DemoPanel({ samples }: { samples: DemoSample[] }) {
  const router = useRouter();
  const [chosen, setChosen] = useState<string>(samples[0]?.id ?? GENERATED);
  const [generated, setGenerated] = useState<GeneratedRequest | null>(null);
  const [messages, setMessages] = useState<Record<string, string>>(() =>
    Object.fromEntries(samples.map((s) => [s.id, s.message])),
  );
  const [busy, setBusy] = useState(false);
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

  async function makeOne() {
    setChosen(GENERATED);
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

  async function send() {
    if (!source) return;
    setBusy(true);
    setError(null);
    try {
      router.push(await submitDemo(source, message !== original ? message : undefined));
    } catch (e) {
      setError(e instanceof Error ? `Not sent: ${e.message}. Is the API running?` : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">Choose a request</legend>
        <button
          type="button"
          onClick={makeOne}
          className={`block w-full rounded-2xl p-4 text-left ring-1 ${chosen === GENERATED ? "bg-surface ring-2 ring-ink" : "ring-rule hover:bg-surface"}`}
        >
          <span className="block font-display text-lg font-semibold">Make one up</span>
          <span className="mt-1 block text-sm text-muted">
            A new pet for one of the pet parents, a stay, and a vaccine card to match. No name repeats one already on file.
          </span>
        </button>
        {samples.map((s) => (
          <label
            key={s.id}
            className={`block cursor-pointer rounded-2xl p-4 ring-1 ${chosen === s.id ? "bg-surface ring-2 ring-ink" : "ring-rule hover:bg-surface"}`}
          >
            <input type="radio" name="sample" value={s.id} checked={chosen === s.id} onChange={() => setChosen(s.id)} className="sr-only" />
            <span className="block font-display text-lg font-semibold">{s.title}</span>
            <span className="mt-1 block text-sm text-muted">{s.expect}</span>
          </label>
        ))}
      </fieldset>

      <div className="rounded-2xl bg-surface p-6 ring-1 ring-rule">
        {chosen === GENERATED && !generated ? (
          <p className="text-muted">{busy ? "Making up a request" : "Choose “Make one up” to create a request."}</p>
        ) : (
          <>
            {chosen === GENERATED && generated && (
              <div className="mb-5">
                <p className="font-display text-xl font-semibold">
                  {generated.pet}, {formatService(generated.service).toLowerCase()}, {formatStay(generated.start_date, generated.end_date)}
                </p>
                <p className="text-muted">
                  From {generated.owner}. {generated.breed}, {generated.weight_lb} lb. {generated.scenario_text}
                </p>
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
                disabled={busy || !message.trim() || !source}
                onClick={send}
                className="rounded-full bg-ink px-6 py-2.5 font-medium text-white disabled:opacity-40"
              >
                {busy ? "Sending" : "Send and watch it run"}
              </button>
              {chosen === GENERATED && (
                <button type="button" disabled={busy} onClick={makeOne} className="rounded-full px-5 py-2.5 ring-1 ring-rule hover:bg-wash disabled:opacity-40">
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
