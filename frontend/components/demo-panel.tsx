"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { submitDemo } from "@/lib/demo";
import type { DemoSample } from "@/lib/types";

export function DemoPanel({ samples }: { samples: DemoSample[] }) {
  const router = useRouter();
  const [chosen, setChosen] = useState(samples[0]?.id ?? "");
  const [messages, setMessages] = useState<Record<string, string>>(() =>
    Object.fromEntries(samples.map((s) => [s.id, s.message])),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sample = samples.find((s) => s.id === chosen);

  async function submit() {
    if (!sample) return;
    setBusy(true);
    setError(null);
    try {
      const edited = messages[sample.id] !== sample.message ? messages[sample.id] : undefined;
      router.push(await submitDemo(sample.id, edited));
    } catch (e) {
      setError(e instanceof Error ? `Not sent: ${e.message}. Is the API running?` : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium">Choose a sample</legend>
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
      {sample && (
        <div className="rounded-2xl bg-surface p-6 ring-1 ring-rule">
          <label className="block">
            <span className="text-sm font-medium">Message from the pet parent</span>
            <textarea
              className="mt-2 h-48 w-full rounded-lg bg-wash p-3 leading-relaxed ring-1 ring-rule"
              value={messages[sample.id]}
              onChange={(e) => setMessages({ ...messages, [sample.id]: e.target.value })}
            />
          </label>
          <p className="mt-2 text-sm text-faint">
            {sample.certificate ? "This sample includes a photo of a vaccine certificate." : "This sample has no certificate."}{" "}
            You can edit the message before sending.
          </p>
          <button
            type="button"
            disabled={busy || !messages[sample.id]?.trim()}
            onClick={submit}
            className="mt-5 rounded-full bg-ink px-6 py-2.5 font-medium text-white disabled:opacity-40"
          >
            {busy ? "Sending" : "Send and watch it run"}
          </button>
          {error && <p className="mt-3 text-error">{error}</p>}
        </div>
      )}
    </div>
  );
}
