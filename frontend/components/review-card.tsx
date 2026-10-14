"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { formatService, formatStay } from "@/lib/format";
import { flagText } from "@/lib/story";
import type { ReviewItem } from "@/lib/types";

type Action = "approve" | "edit-and-approve" | "reject";

export function ReviewQueue({ items }: { items: ReviewItem[] }) {
  const [staff, setStaff] = useState("");
  // Kept here, not on the card: a decided request leaves the queue, and its card with it.
  const [done, setDone] = useState<string | null>(null);
  return (
    <div className="space-y-6">
      {done && (
        <p role="status" className="rounded-xl bg-kennel-soft px-4 py-3 font-medium text-kennel">
          {done}
        </p>
      )}
      <label className="flex max-w-sm flex-col gap-1.5">
        <span className="text-sm font-medium">Reviewing as</span>
        <input
          className="rounded-lg bg-surface px-3 py-2 ring-1 ring-rule"
          value={staff}
          onChange={(e) => setStaff(e.target.value)}
          placeholder="Your name"
          autoComplete="name"
        />
        <span className="text-sm text-faint">Saved with each decision you make.</span>
      </label>
      {items.map((item) => (
        <ReviewCard key={item.id} item={item} staff={staff.trim()} onDone={setDone} />
      ))}
    </div>
  );
}

function ReviewCard({
  item,
  staff,
  onDone,
}: {
  item: ReviewItem;
  staff: string;
  onDone: (message: string) => void;
}) {
  const router = useRouter();
  const [reply, setReply] = useState(item.draft?.body ?? "");
  const [declining, setDeclining] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const edited = item.draft !== null && reply.trim() !== item.draft.body.trim();

  async function act(action: Action) {
    setBusy(true);
    setError(null);
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
      const declined = item.pet ? `Declined ${item.pet}'s request.` : "Declined the request.";
      const sent = `Sent the reply for ${item.pet ?? "this request"}.`;
      onDone(action === "reject" ? `${declined} The pet parent gets a polite no.` : sent);
      router.refresh();
    } else {
      const detail = typeof data.detail === "string" ? data.detail : "check the fields and try again";
      setError(`Not sent: ${detail}.`);
    }
  }

  return (
    <article className="overflow-hidden rounded-2xl bg-surface ring-1 ring-rule">
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-l-4 border-signal px-6 pt-5">
        <div>
          <h2 className="text-2xl font-bold">{item.pet ?? "Pet not on file"}</h2>
          <p className="text-muted">
            {item.owner}, {formatService(item.service).toLowerCase()}, {formatStay(item.start_date, item.end_date).replace(/^Dates/, "dates")}
          </p>
        </div>
        <Link href={`/requests/${item.id}`} className="text-sm text-code hover:underline">
          See the full run
        </Link>
      </div>

      <div className="border-l-4 border-signal px-6 pt-4 pb-5">
        <p className="text-sm font-medium">Reasons for review</p>
        <ul className="mt-1.5 space-y-1">
          {item.flags.length > 0 ? (
            item.flags.map((flag) => (
              <li key={flag} className="flex gap-2">
                <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" />
                <span>
                  {flagText(flag)[0].toUpperCase() + flagText(flag).slice(1)}
                  <span className="sr-only"> ({flag})</span>
                </span>
              </li>
            ))
          ) : (
            <li className="text-muted">The desk recorded no reason.</li>
          )}
        </ul>
      </div>

      {item.draft ? (
        <div className="border-t border-rule bg-wash px-6 py-5">
          <label className="block">
            <span className="text-sm font-medium">
              Reply{edited && <span className="ml-2 text-code">edited</span>}
            </span>
            <textarea
              className="mt-1.5 h-44 w-full rounded-lg bg-surface p-3 leading-relaxed ring-1 ring-rule"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
            />
          </label>

          {declining && (
            <label className="mt-3 block max-w-lg">
              <span className="text-sm font-medium">Reason for declining</span>
              <input
                className="mt-1.5 w-full rounded-lg bg-surface px-3 py-2 ring-1 ring-rule"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Only staff see this. The pet parent gets a polite no."
              />
            </label>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-3">
            {!declining ? (
              <>
                <button
                  type="button"
                  disabled={busy || !staff}
                  onClick={() => act(edited ? "edit-and-approve" : "approve")}
                  className="rounded-full bg-kennel px-5 py-2 font-medium text-white disabled:opacity-40"
                >
                  {edited ? "Send edited reply" : "Send reply"}
                </button>
                <button
                  type="button"
                  onClick={() => setDeclining(true)}
                  className="rounded-full px-4 py-2 text-muted ring-1 ring-rule hover:bg-surface"
                >
                  Decline
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  disabled={busy || !staff || !reason.trim()}
                  onClick={() => act("reject")}
                  className="rounded-full bg-ink px-5 py-2 font-medium text-white disabled:opacity-40"
                >
                  Decline request
                </button>
                <button type="button" onClick={() => setDeclining(false)} className="px-2 py-2 text-muted hover:text-ink">
                  Keep it
                </button>
              </>
            )}
            {!staff && <span className="text-sm text-faint">Add your name above to decide.</span>}
            {error && (
              <span role="alert" className="text-error">
                {error}
              </span>
            )}
          </div>
        </div>
      ) : (
        <p className="border-t border-rule bg-wash px-6 py-5 text-muted">
          This request has no draft, so you can&apos;t send it from here.
        </p>
      )}
    </article>
  );
}
