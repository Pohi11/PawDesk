"use client";

import { useEffect, useMemo, useState } from "react";

import { formatCost, formatSeconds, formatTokens, spanDurationMs } from "@/lib/format";
import { NODES, type NodeId, nodeStatuses } from "@/lib/graph";
import { layout } from "@/lib/timeline";
import type { RequestDetail, Snapshot, SpanDetail } from "@/lib/types";

import { RunGraph } from "./run-graph";
import { Card, Json, KIND_STYLE, KindDot, StatusBadge } from "./ui";

const SPAN_STATUS: Record<SpanDetail["status"], string> = {
  running: "bg-blue-100 text-blue-800",
  ok: "bg-emerald-100 text-emerald-800",
  error: "bg-red-100 text-red-800",
};

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

  // Live updates: one snapshot per change, then refetch the full detail for the inspector.
  // Opened in an effect and closed in its cleanup: hidden pages keep their state but not
  // their effects, so a background tab holds no stream.
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

  const snap = useMemo(() => snapshotOf(detail), [detail]);
  const statuses = useMemo(() => nodeStatuses(snap), [snap]);
  const trace = detail.traces.find((t) => t.id === traceId) ?? detail.traces.at(-1);
  const allSpans = detail.traces.flatMap((t) => t.spans);
  const selected = allSpans.find((s) => s.id === selectedId) ?? null;

  const selectNode = (node: NodeId) => {
    const name = NODES.find((n) => n.id === node)?.span;
    const span = allSpans.filter((s) => s.name === name).at(-1);
    if (span) {
      setSelectedId(span.id);
      setTraceId(span.trace_id);
    }
  };

  const cost = allSpans.reduce((sum, s) => sum + Number(s.cost_usd ?? 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {detail.pet ?? "Unknown pet"} <span className="text-zinc-400">·</span> {detail.owner}
        </h1>
        <StatusBadge status={detail.status} />
        {live && (
          <span className="inline-flex items-center gap-1.5 text-xs text-blue-700">
            <span className="h-2 w-2 animate-ping rounded-full bg-blue-500" /> live
          </span>
        )}
        <span className="ml-auto text-sm text-zinc-500">
          {allSpans.filter((s) => s.kind === "llm").length} model calls · {formatCost(cost)}
        </span>
      </div>

      <Card
        title={
          <span className="flex items-center gap-4">
            Workflow
            <span className="flex gap-3 text-xs font-normal text-zinc-500">
              {(["llm", "code", "tool", "human"] as const).map((k) => (
                <span key={k} className="inline-flex items-center gap-1">
                  <KindDot kind={k} /> {KIND_STYLE[k].label}
                </span>
              ))}
            </span>
          </span>
        }
      >
        <RunGraph statuses={statuses} onSelect={selectNode} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card
          className="lg:col-span-3"
          title={
            <span className="flex items-center gap-3">
              Timeline
              {detail.traces.length > 1 && (
                <select
                  className="rounded border border-zinc-300 px-1 py-0.5 text-xs font-normal"
                  value={trace?.id}
                  onChange={(e) => setTraceId(e.target.value)}
                >
                  {detail.traces.map((t, i) => (
                    <option key={t.id} value={t.id}>
                      run {i + 1}
                    </option>
                  ))}
                </select>
              )}
            </span>
          }
        >
          {trace ? (
            <Timeline
              spans={trace.spans}
              now={now}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          ) : (
            <p className="text-sm text-zinc-500">Not processed yet.</p>
          )}
        </Card>
        <Card className="lg:col-span-2" title="Span inspector">
          {selected ? (
            <Inspector span={selected} now={now} />
          ) : (
            <p className="text-sm text-zinc-500">Select a step in the graph or a bar in the timeline.</p>
          )}
        </Card>
      </div>

      <RunFacts detail={detail} />
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
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-zinc-400">
        <span>0 s</span>
        <span>{formatSeconds(totalMs)}</span>
      </div>
      {bars.map(({ span, offsetMs, widthMs, depth }) => (
        <button
          key={span.id}
          type="button"
          onClick={() => onSelect(span.id)}
          className={`group flex w-full items-center gap-2 rounded px-1 text-left text-xs hover:bg-zinc-50 ${selectedId === span.id ? "bg-zinc-100" : ""}`}
        >
          <span className="w-40 shrink-0 truncate" style={{ paddingLeft: depth * 12 }}>
            {span.name}
          </span>
          <span className="relative h-4 flex-1 rounded bg-zinc-50">
            <span
              className={`absolute top-0.5 h-3 rounded ${span.status === "running" ? "animate-pulse" : ""}`}
              style={{
                left: `${(offsetMs / totalMs) * 100}%`,
                width: `max(${(widthMs / totalMs) * 100}%, 2px)`,
                background: span.status === "error" ? "#ef4444" : KIND_STYLE[span.kind].border,
              }}
            />
          </span>
          <span className="w-14 shrink-0 text-right tabular-nums text-zinc-500">
            {formatSeconds(widthMs)}
          </span>
        </button>
      ))}
    </div>
  );
}

function Inspector({ span, now }: { span: SpanDetail; now: number }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        <KindDot kind={span.kind} />
        <span className="font-mono font-semibold">{span.name}</span>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${SPAN_STATUS[span.status]}`}
        >
          {span.status}
        </span>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <dt className="text-zinc-500">Duration</dt>
        <dd className="tabular-nums">{formatSeconds(spanDurationMs(span, now))}</dd>
        {span.model && (
          <>
            <dt className="text-zinc-500">Model</dt>
            <dd className="font-mono">{span.model}</dd>
            <dt className="text-zinc-500">Tokens</dt>
            <dd className="tabular-nums">{formatTokens(span)}</dd>
            <dt className="text-zinc-500">Cost</dt>
            <dd className="tabular-nums">{formatCost(span.cost_usd)}</dd>
          </>
        )}
      </dl>
      {span.error && (
        <p className="rounded-lg bg-red-50 p-2 font-mono text-xs text-red-800">{span.error}</p>
      )}
      <Section title="Input" value={span.input} />
      <Section title="Output" value={span.output} />
      {Object.keys(span.attributes ?? {}).length > 0 && (
        <Section title="Attributes" value={span.attributes} />
      )}
    </div>
  );
}

function Section({ title, value }: { title: string; value: unknown }) {
  if (value === null || value === undefined) return null;
  return (
    <details open={title !== "Attributes"}>
      <summary className="cursor-pointer text-xs font-medium text-zinc-600">{title}</summary>
      <div className="mt-1">
        <Json value={value} />
      </div>
    </details>
  );
}

function RunFacts({ detail }: { detail: RequestDetail }) {
  const route = detail.steps.route as { target?: string; reasons?: string[] } | undefined;
  const resolution = detail.steps.resolution as
    | { outcome?: string; reason?: string; proposal?: { summary: string; options: Record<string, unknown>[] } | null }
    | undefined;
  const reply = detail.steps.reply as
    | { situation?: string; flags?: string[]; draft?: { subject: string; body: string } }
    | undefined;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="Message received">
        <p className="whitespace-pre-wrap text-sm text-zinc-700">{detail.raw_message}</p>
      </Card>
      <Card title="Decision trail">
        <ol className="space-y-1 text-xs">
          {detail.transitions.map((t, i) => (
            <li key={i} className="flex gap-2">
              <span className="w-20 shrink-0 tabular-nums text-zinc-400">
                {new Date(t.at).toLocaleTimeString()}
              </span>
              <span className="font-medium">{t.to.replace("_", " ")}</span>
              <span className="text-zinc-400">{t.actor}</span>
              {t.reason && <span className="truncate text-zinc-600" title={t.reason}>{t.reason}</span>}
            </li>
          ))}
        </ol>
        {detail.last_error && (
          <p className="mt-2 rounded bg-red-50 p-2 font-mono text-xs text-red-800">{detail.last_error}</p>
        )}
      </Card>
      {route && (
        <Card title={`Routing → ${route.target}`}>
          {route.reasons && route.reasons.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {route.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-zinc-600">Every check passed.</p>
          )}
        </Card>
      )}
      {resolution && (
        <Card title={`Resolver: ${resolution.outcome}`}>
          <p className="text-sm text-zinc-600">{resolution.reason}</p>
          {resolution.proposal && (
            <>
              <p className="mt-2 text-sm">{resolution.proposal.summary}</p>
              <ul className="mt-2 space-y-1 text-xs">
                {resolution.proposal.options.map((o, i) => (
                  <li key={i} className="flex gap-2">
                    <span className={o.verified ? "text-emerald-700" : "text-red-700"}>
                      {o.verified ? "verified" : "not verified"}
                    </span>
                    <span className="font-mono">{JSON.stringify(o)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}
      {reply?.draft && (
        <Card title={`Reply draft (${reply.situation})`}>
          {reply.flags && reply.flags.length > 0 && (
            <ul className="mb-2 space-y-1 text-xs text-amber-800">
              {reply.flags.map((f) => (
                <li key={f}>⚑ {f}</li>
              ))}
            </ul>
          )}
          <p className="text-sm font-medium">{reply.draft.subject}</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-700">{reply.draft.body}</p>
        </Card>
      )}
      {detail.message && (
        <Card title={`Sent: ${detail.message.kind}`}>
          <p className="text-sm font-medium">{detail.message.subject}</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-700">{detail.message.body}</p>
          {detail.approvals.map((a, i) => (
            <p key={i} className="mt-2 text-xs text-zinc-500">
              {a.action.replaceAll("_", " ")} by {a.staff_name}
              {a.reason ? `: ${a.reason}` : ""}
            </p>
          ))}
        </Card>
      )}
    </div>
  );
}
