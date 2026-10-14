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
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3">
        {samples.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setChosen(s.id)}
            className={`block w-full rounded-xl border p-4 text-left shadow-sm transition ${chosen === s.id ? "border-blue-500 bg-blue-50" : "border-zinc-200 bg-white hover:border-zinc-300"}`}
          >
            <div className="font-semibold">{s.title}</div>
            <div className="mt-1 text-sm text-zinc-600">{s.expect}</div>
            {s.certificate && (
              <div className="mt-1 text-xs text-zinc-400">with certificate {s.certificate}</div>
            )}
          </button>
        ))}
      </div>
      {sample && (
        <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
          <label className="block text-sm">
            <span className="text-xs font-medium text-zinc-600">Message from the pet parent</span>
            <textarea
              className="mt-1 h-48 w-full rounded-lg border border-zinc-300 p-2 text-sm"
              value={messages[sample.id]}
              onChange={(e) => setMessages({ ...messages, [sample.id]: e.target.value })}
            />
          </label>
          <button
            type="button"
            disabled={busy || !messages[sample.id]?.trim()}
            onClick={submit}
            className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {busy ? "Submitting…" : "Submit and watch the run"}
          </button>
          {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
        </div>
      )}
    </div>
  );
}
