"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import type { ReviewItem } from "@/lib/types";

type Action = "approve" | "edit-and-approve" | "reject";

export function ReviewCard({ item }: { item: ReviewItem }) {
  const router = useRouter();
  const [staff, setStaff] = useState("");
  const [reply, setReply] = useState(item.draft?.body ?? "");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const edited = item.draft !== null && reply.trim() !== item.draft.body.trim();

  async function act(action: Action) {
    setBusy(true);
    setResult(null);
    const body: Record<string, string> = { staff_name: staff };
    if (action === "edit-and-approve") body.reply = reply;
    if (action === "reject") body.reason = reason;
    const response = await fetch(`/api/requests/${item.id}/${action}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = (await response.json().catch(() => ({}))) as { status?: string; detail?: unknown };
    setBusy(false);
    if (response.ok) {
      setResult(`Done: the request is now ${data.status}.`);
      router.refresh();
    } else {
      setResult(`Refused (${response.status}): ${JSON.stringify(data.detail ?? data)}`);
    }
  }

  return (
    <article className="rounded-xl border border-amber-200 bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-lg font-semibold">
          {item.pet ?? "Unknown pet"} <span className="text-zinc-400">·</span> {item.owner}
        </h2>
        <span className="text-sm text-zinc-500">
          {item.service ?? "service unknown"}
          {item.start_date ? `, ${item.start_date} → ${item.end_date}` : ""}
        </span>
        <Link href={`/requests/${item.id}`} className="ml-auto text-sm text-blue-700 hover:underline">
          Open run →
        </Link>
      </header>

      <ul className="mt-3 space-y-1 text-sm text-amber-900">
        {item.flags.length > 0 ? (
          item.flags.map((flag) => <li key={flag}>⚑ {flag}</li>)
        ) : (
          <li>⚑ waiting for review (no reasons recorded)</li>
        )}
      </ul>

      {item.draft && (
        <label className="mt-4 block text-sm">
          <span className="text-xs font-medium text-zinc-600">
            Reply: {item.draft.subject} {edited && <span className="text-blue-700">(edited)</span>}
          </span>
          <textarea
            className="mt-1 h-40 w-full rounded-lg border border-zinc-300 p-2 text-sm"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
          />
        </label>
      )}

      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="block text-xs font-medium text-zinc-600">Your name</span>
          <input
            className="mt-1 rounded-lg border border-zinc-300 px-2 py-1"
            value={staff}
            onChange={(e) => setStaff(e.target.value)}
            placeholder="e.g. Dana"
          />
        </label>
        <button
          type="button"
          disabled={busy || !staff.trim() || !item.draft}
          onClick={() => act(edited ? "edit-and-approve" : "approve")}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {edited ? "Approve edited reply" : "Approve"}
        </button>
        <label className="text-sm">
          <span className="block text-xs font-medium text-zinc-600">Reason (internal)</span>
          <input
            className="mt-1 w-64 rounded-lg border border-zinc-300 px-2 py-1"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={busy || !staff.trim() || !reason.trim()}
          onClick={() => act("reject")}
          className="rounded-lg bg-zinc-800 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          Reject
        </button>
      </div>
      {result && <p className="mt-3 text-sm text-zinc-700">{result}</p>}
    </article>
  );
}
