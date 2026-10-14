// Which workflow step is waiting, running, done, failed, or skipped, derived from the
// request's state and its spans (spec: run-dashboard, design D5). Pure, so it's tested
// without a browser and the live view just re-renders it on every snapshot.

import type { Snapshot, SpanKind, SpanSummary } from "./types";

export type NodeStatus = "waiting" | "running" | "ok" | "error" | "skipped";
export type NodeId =
  | "intake"
  | "records"
  | "compliance"
  | "capacity"
  | "route"
  | "resolver"
  | "reply"
  | "review"
  | "send";

export interface WorkflowNode {
  id: NodeId;
  label: string;
  kind: SpanKind;
  span?: string; // the span name that represents this step
}

export const NODES: readonly WorkflowNode[] = [
  { id: "intake", label: "Intake", kind: "llm", span: "intake" },
  { id: "records", label: "Records", kind: "llm", span: "records" },
  { id: "compliance", label: "Compliance", kind: "code", span: "compliance" },
  { id: "capacity", label: "Capacity", kind: "tool", span: "capacity" },
  { id: "route", label: "Route", kind: "code", span: "route" },
  { id: "resolver", label: "Resolver", kind: "llm", span: "resolve" },
  { id: "reply", label: "Reply", kind: "llm", span: "reply" },
  { id: "review", label: "Staff review", kind: "human" },
  { id: "send", label: "Send", kind: "code" },
];

export const EDGES: readonly [NodeId, NodeId][] = [
  ["intake", "compliance"],
  ["records", "compliance"],
  ["compliance", "capacity"],
  ["capacity", "route"],
  ["route", "resolver"],
  ["route", "reply"],
  ["resolver", "reply"],
  ["reply", "review"],
  ["reply", "send"],
  ["review", "send"],
];

const AFTER_ROUTING = new Set([
  "drafting",
  "needs_review",
  "ready",
  "approved",
  "rejected",
  "sent",
]);
const DECIDED = new Set(["approved", "rejected", "sent"]);

function latest(spans: SpanSummary[], name: string): SpanSummary | undefined {
  return spans
    .filter((s) => s.name === name)
    .sort((a, b) => a.started_at.localeCompare(b.started_at))
    .at(-1);
}

const finished = (span?: SpanSummary) => span !== undefined && span.status !== "running";

export function nodeStatuses(snap: Snapshot): Record<NodeId, NodeStatus> {
  const { spans, status } = snap;
  const result = {} as Record<NodeId, NodeStatus>;

  for (const node of NODES) {
    if (!node.span) continue;
    const span = latest(spans, node.span);
    result[node.id] = span ? span.status : "waiting";
  }

  // A step with no span is skipped once the step that would have run it has finished.
  const extractDone = finished(latest(spans, "extract"));
  const checkDone = finished(latest(spans, "check"));
  if (result.records === "waiting" && extractDone) result.records = "skipped";
  if (result.compliance === "waiting" && checkDone) result.compliance = "skipped";
  if (result.capacity === "waiting" && checkDone) result.capacity = "skipped";
  if (result.resolver === "waiting" && (AFTER_ROUTING.has(status) || latest(spans, "reply"))) {
    result.resolver = "skipped";
  }

  // The human step and sending have no spans: they follow the state.
  if (snap.flagged === false) {
    result.review = "skipped";
  } else if (status === "needs_review") {
    result.review = "running";
  } else if (snap.flagged && DECIDED.has(status)) {
    result.review = "ok";
  } else {
    result.review = "waiting";
  }

  if (status === "sent") {
    result.send = "ok";
  } else if (status === "failed" && ["approved", "rejected"].includes(snap.failed_step ?? "")) {
    result.send = "error";
  } else if (status === "approved" || status === "rejected") {
    result.send = "running";
  } else {
    result.send = "waiting";
  }
  return result;
}
