"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { formatCost, formatSeconds, formatService, formatStay, formatTokens, spanDurationMs } from "@/lib/format";
import { NODES, type NodeId, nodeStatuses } from "@/lib/graph";
import { optionText, outcome } from "@/lib/story";
import { layout } from "@/lib/timeline";
import type { RequestDetail, Snapshot, SpanDetail } from "@/lib/types";

import { PetAvatar } from "./pet-avatar";
import { RunGraph } from "./run-graph";
import { Json, KIND_STYLE, KindDot, Panel, StateTag, stateLabel } from "./ui";

function snapshotOf(detail: RequestDetail): Snapshot {
  const reply = detail.steps.reply as { target?: string } | undefined;
  return {
    status: detail.status,
    failed_step: detail.failed_step,
    flagged: reply ? reply.target === "needs_review" : null,
    spans: detail.traces.flatMap((t) => t.spans),
  };
}

export function RunView({ initial }: { initial: RequestDetail }) {
  const [detail, setDetail] = useState(initial);
  const [live, setLive] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);

  // One snapshot per change, then the full detail for the inspector. The stream lives in an
  // effect and closes in its cleanup, so a hidden page holds no connection.
  useEffect(() => {
    const source = new EventSource(`/api/requests/${initial.id}/events`);
    source.onopen = () => setLive(true);
    source.addEventListener("snapshot", async () => {
      const response = await fetch(`/api/requests/${initial.id}`);
      if (response.ok) setDetail((await response.json()) as RequestDetail);
      setNow(Date.now());
    });
    const stop = () => {
      source.close();
      setLive(false);
    };
    source.addEventListener("end", stop);
    source.onerror = stop;
    return () => source.close();
  }, [initial.id]);

  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(timer);
  }, [live]);

  const statuses = useMemo(() => nodeStatuses(snapshotOf(detail)), [detail]);
  const spans = detail.traces.flatMap((t) => t.spans);
  // Runs that did work; a run that only sent an approved reply has no steps to show.
  const runs = detail.traces.filter((t) => t.spans.length > 0);
  const trace = runs.find((t) => t.id === traceId) ?? runs.at(-1);
  const selected = spans.find((s) => s.id === selectedId) ?? null;
  const cost = spans.reduce((sum, s) => sum + Number(s.cost_usd ?? 0), 0);
  const modelCalls = spans.filter((s) => s.kind === "llm").length;
  const intent = (detail.steps.intake as { intent?: { service?: string; start_date?: string; end_date?: string } } | undefined)?.intent;

  const selectNode = (node: NodeId) => {
    const name = NODES.find((n) => n.id === node)?.span;
    const span = spans.filter((s) => s.name === name).at(-1);
    if (span) {
      setSelectedId(span.id);
      setTraceId(span.trace_id);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <Link href="/" className="text-sm text-muted hover:text-ink">
          All requests
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <PetAvatar pet={detail} size="lg" />
          <h1 className="text-4xl font-extrabold sm:text-5xl">{detail.pet ?? "Pet not on file"}</h1>
          <StateTag status={detail.status} />
          {live && (
            <span className="inline-flex items-center gap-2 text-sm text-code">
              <span className="h-2 w-2 rounded-full bg-code motion-safe:animate-ping" /> Live
            </span>
          )}
        </div>
        <p className="mt-2 text-muted">
          {detail.owner}, {formatService(intent?.service ?? null).toLowerCase()},{" "}
          {formatStay(intent?.start_date ?? null, intent?.end_date ?? null).replace(/^Dates/, "dates")}
        </p>
        <div className="mt-5 flex flex-wrap items-baseline justify-between gap-4 border-l-4 border-ink pl-4">
          <p className="max-w-2xl font-display text-xl font-medium">{outcome(detail)}</p>
          <p className="text-sm text-muted">
            {modelCalls} model {modelCalls === 1 ? "call" : "calls"}, {formatCost(cost)}
          </p>
        </div>
      </div>

      <Panel
        title="The desk's path"
        aside={
          <span className="flex flex-wrap gap-x-4 gap-y-1">
            {(["llm", "code", "tool", "human"] as const).map((k) => (
              <span key={k} className="inline-flex items-center gap-1.5">
                <KindDot kind={k} /> {KIND_STYLE[k].label}
              </span>
            ))}
          </span>
        }
      >
        <RunGraph statuses={statuses} detail={detail} onSelect={selectNode} />
        <p className="mt-2 text-sm text-faint">Point at a step for a summary, or select it to see exactly what it was given and what it returned.</p>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel
          className="lg:col-span-3"
          title="Timeline"
          aside={
            runs.length > 1 && (
              <label className="flex items-center gap-2">
                Run
                <select
                  className="rounded-md bg-wash px-2 py-1 text-ink ring-1 ring-rule"
                  value={trace?.id}
                  onChange={(e) => setTraceId(e.target.value)}
                >
                  {runs.map((t, i) => (
                    <option key={t.id} value={t.id}>
                      {i + 1} of {runs.length}
                    </option>
                  ))}
                </select>
              </label>
            )
          }
        >
          {trace ? (
            <Timeline spans={trace.spans} now={now} selectedId={selectedId} onSelect={setSelectedId} />
          ) : (
            <p className="text-sm text-muted">Not started yet.</p>
          )}
        </Panel>
        <Panel className="lg:col-span-2" title="Step details">
          {selected ? (
            <Inspector span={selected} now={now} />
          ) : (
            <p className="text-sm text-muted">Choose a step in the path or a bar in the timeline.</p>
          )}
        </Panel>
      </div>

      <Story detail={detail} />
    </div>
  );
}

function Timeline({
  spans,
  now,
  selectedId,
  onSelect,
}: {
  spans: SpanDetail[];
  now: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const { bars, totalMs } = layout(spans, now);
  return (
    <div>
      <div className="mb-2 flex justify-end text-xs text-faint">{formatSeconds(totalMs)} in total</div>
      <div className="space-y-0.5">
        {bars.map(({ span, offsetMs, widthMs, depth }) => (
          <button
            key={span.id}
            type="button"
            onClick={() => onSelect(span.id)}
            className={`flex w-full items-center gap-3 rounded-md px-2 py-1 text-left text-sm hover:bg-wash ${selectedId === span.id ? "bg-wash ring-1 ring-rule" : ""}`}
          >
            <span className="w-40 shrink-0 truncate" style={{ paddingLeft: depth * 14 }}>
              {span.name}
            </span>
            <span className="relative h-3 flex-1">
              <span
                className={`absolute top-0 h-3 rounded-full ${span.status === "running" ? "motion-safe:animate-pulse" : ""}`}
                style={{
                  left: `${(offsetMs / totalMs) * 100}%`,
                  width: `max(${(widthMs / totalMs) * 100}%, 3px)`,
                  background: span.status === "error" ? "#c42b3e" : KIND_STYLE[span.kind].color,
                }}
              />
            </span>
            <span className="w-14 shrink-0 text-right text-xs text-muted">{formatSeconds(widthMs)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Inspector({ span, now }: { span: SpanDetail; now: number }) {
  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <KindDot kind={span.kind} />
        <span className="font-semibold">{span.name}</span>
        <span className={span.status === "error" ? "text-error" : span.status === "ok" ? "text-kennel" : "text-code"}>
          {span.status === "ok" ? "succeeded" : span.status === "error" ? "failed" : "running"}
        </span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1">
        <dt className="text-muted">Took</dt>
        <dd>{formatSeconds(spanDurationMs(span, now))}</dd>
        {span.model && (
          <>
            <dt className="text-muted">Model</dt>
            <dd className="break-all">{span.model}</dd>
            <dt className="text-muted">Tokens</dt>
            <dd>{formatTokens(span)}</dd>
            <dt className="text-muted">Cost</dt>
            <dd>{formatCost(span.cost_usd)}</dd>
          </>
        )}
      </dl>
      {span.error && <p className="rounded-lg bg-error-soft p-3 text-error">{span.error}</p>}
      <Payload title="Given" value={span.input} open />
      <Payload title="Returned" value={span.output} open />
      {Object.keys(span.attributes ?? {}).length > 0 && <Payload title="Attributes" value={span.attributes} />}
    </div>
  );
}

function Payload({ title, value, open = false }: { title: string; value: unknown; open?: boolean }) {
  if (value === null || value === undefined) return null;
  return (
    <details open={open}>
      <summary className="cursor-pointer font-medium">{title}</summary>
      <div className="mt-2">
        <Json value={value} />
      </div>
    </details>
  );
}

function Story({ detail }: { detail: RequestDetail }) {
  const route = detail.steps.route as { target?: string; reasons?: string[] } | undefined;
  const resolution = detail.steps.resolution as
    | { outcome?: string; proposal?: { summary: string; options: (Record<string, unknown> & { kind: string; verified?: boolean; remaining_problems?: string[] })[] } | null }
    | undefined;
  const reply = detail.steps.reply as { flags?: string[]; draft?: { subject: string; body: string } } | undefined;
  const letter = detail.message ?? (reply?.draft ? { ...reply.draft, kind: "draft" } : null);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        <Panel title="What they asked">
          <p className="whitespace-pre-wrap leading-relaxed">{detail.raw_message}</p>
        </Panel>
        {letter && (
          <Panel title={detail.message ? "What was sent" : "Reply waiting to be sent"}>
            <p className="font-medium">{letter.subject}</p>
            <p className="mt-2 whitespace-pre-wrap leading-relaxed text-muted">{letter.body}</p>
          </Panel>
        )}
      </div>
      <div className="space-y-6">
        {route && (
          <Panel title="Why it went this way">
            {route.reasons?.length ? (
              <ul className="space-y-1.5">
                {route.reasons.map((r) => (
                  <li key={r} className="flex gap-2">
                    <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" />
                    {r}
                  </li>
                ))}
              </ul>
            ) : (
              <p>Every check passed.</p>
            )}
            {resolution?.proposal && (
              <div className="mt-5">
                <p className="font-medium">Options found</p>
                <p className="mt-1 text-sm text-muted">{resolution.proposal.summary}</p>
                <ul className="mt-3 space-y-2">
                  {resolution.proposal.options.map((o, i) => (
                    <li key={i} className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg bg-wash px-3 py-2">
                      <span>{optionText(o)}</span>
                      <span className={`text-sm ${o.verified ? "text-kennel" : "text-error"}`}>
                        {o.verified ? "Checked and works" : `Still blocked: ${o.remaining_problems?.join(", ")}`}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>
        )}
        <Panel title="Every step it took">
          <ol className="space-y-2 text-sm">
            {detail.transitions.map((t, i) => (
              <li key={i} className="grid grid-cols-[6.5rem_1fr] gap-3">
                <span className="text-faint">{new Date(t.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
                <span>
                  <span className="font-medium">{stateLabel(t.to)}</span>
                  {t.actor === "staff" && <span className="ml-2 text-signal">by staff</span>}
                </span>
              </li>
            ))}
          </ol>
          {detail.last_error && <p className="mt-3 rounded-lg bg-error-soft p-3 text-sm text-error">{detail.last_error}</p>}
        </Panel>
      </div>
    </div>
  );
}
