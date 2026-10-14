import { expect, vi } from "vitest";

import { specTest } from "../tests/spec";
import { submitDemo } from "./demo";
import { formatCost, formatSeconds, formatTokens, spanDurationMs } from "./format";
import { NODES, nodeStatuses } from "./graph";
import { layout, overlaps } from "./timeline";
import type { Snapshot, SpanSummary } from "./types";

const T0 = Date.parse("2027-03-03T10:00:00.000Z");
const at = (seconds: number) => new Date(T0 + seconds * 1000).toISOString();

function span(
  name: string,
  from: number,
  to: number | null,
  extra: Partial<SpanSummary> = {},
): SpanSummary {
  return {
    id: name,
    trace_id: "t",
    parent_span_id: null,
    name,
    kind: "code",
    status: to === null ? "running" : "ok",
    started_at: at(from),
    ended_at: to === null ? null : at(to),
    model: null,
    prompt_tokens: null,
    completion_tokens: null,
    cost_usd: null,
    ...extra,
  };
}

const snap = (status: string, spans: SpanSummary[], extra: Partial<Snapshot> = {}): Snapshot => ({
  status,
  failed_step: null,
  flagged: null,
  spans,
  ...extra,
});

const GRAPH = "The run graph shows each step's status and kind";
const TIMELINE = "The timeline shows overlapping steps";
const OPERATORS = "Operators can review, measure, and demo from the dashboard";

// --- The run graph -------------------------------------------------------------------

specTest("run-dashboard", GRAPH, "parallel steps both show running", () => {
  const statuses = nodeStatuses(
    snap("extracting", [span("extract", 0, null), span("intake", 0.1, null), span("records", 0.2, null)]),
  );

  expect([statuses.intake, statuses.records]).toEqual(["running", "running"]);
  expect(statuses.compliance).toBe("waiting");
});

specTest("run-dashboard", GRAPH, "a request routed straight to drafting skips the resolver", () => {
  const statuses = nodeStatuses(
    snap(
      "sent",
      [
        span("extract", 0, 4),
        span("intake", 0, 4),
        span("records", 0, 3),
        span("check", 4, 5),
        span("compliance", 4, 4.1),
        span("capacity", 4.1, 4.2),
        span("route", 5, 5.1),
        span("reply", 5.1, 7),
      ],
      { flagged: false },
    ),
  );

  expect(statuses.resolver).toBe("skipped");
  expect(statuses.review).toBe("skipped");
  expect(statuses.send).toBe("ok");
});

specTest("run-dashboard", GRAPH, "a request waiting for review", () => {
  const statuses = nodeStatuses(
    snap("needs_review", [span("route", 0, 1), span("resolve", 1, 3), span("reply", 3, 5)], {
      flagged: true,
    }),
  );

  expect(statuses.review).toBe("running");
  expect(statuses.send).toBe("waiting");
  expect(statuses.resolver).toBe("ok");
});

specTest("run-dashboard", GRAPH, "steps without a span are skipped once their parent step ends", () => {
  const statuses = nodeStatuses(
    snap("checking", [span("extract", 0, 2), span("intake", 0, 2), span("check", 2, 3)]),
  );

  expect([statuses.records, statuses.compliance, statuses.capacity]).toEqual([
    "skipped",
    "skipped",
    "skipped",
  ]);
});

specTest("run-dashboard", GRAPH, "failures show as errors, and a failed send as a send error", () => {
  const failedModel = nodeStatuses(
    snap("failed", [span("intake", 0, 1, { status: "error" })], { failed_step: "extracting" }),
  );
  const failedSend = nodeStatuses(snap("failed", [], { failed_step: "approved", flagged: false }));

  expect(failedModel.intake).toBe("error");
  expect(failedSend.send).toBe("error");
});

specTest("run-dashboard", GRAPH, "every node has a kind for its color", () => {
  expect(Object.fromEntries(NODES.map((n) => [n.id, n.kind]))).toEqual({
    intake: "llm",
    records: "llm",
    compliance: "code",
    capacity: "tool",
    route: "code",
    resolver: "llm",
    reply: "llm",
    review: "human",
    send: "code",
  });
});

// --- The timeline ----------------------------------------------------------------------

specTest("run-dashboard", TIMELINE, "concurrent spans overlap", () => {
  const { bars } = layout([span("intake", 0.1, 4.6), span("records", 0.2, 3.0)], T0 + 10_000);

  const [intake, records] = bars;
  expect([intake.offsetMs, intake.widthMs]).toEqual([0, 4500]);
  expect([records.offsetMs, records.widthMs]).toEqual([100, 2800]);
  expect(overlaps(intake, records)).toBe(true);
});

specTest("run-dashboard", TIMELINE, "a child is drawn one level deeper", () => {
  const { bars } = layout(
    [
      span("extract", 0, 5),
      span("intake", 0.1, 4.6, { parent_span_id: "extract" }),
      span("intake.extract", 0.2, 4.5, { parent_span_id: "intake", kind: "llm" }),
    ],
    T0,
  );

  expect(bars.map((b) => [b.span.name, b.depth])).toEqual([
    ["extract", 0],
    ["intake", 1],
    ["intake.extract", 2],
  ]);
});

specTest("run-dashboard", TIMELINE, "a running span extends to now", () => {
  const { bars, totalMs } = layout([span("resolve", 1, null)], T0 + 7000);

  expect(bars[0].widthMs).toBe(6000);
  expect(totalMs).toBe(6000);
});

// --- Inspector formatting and the demo -------------------------------------------------

specTest("run-dashboard", OPERATORS, "the span inspector shows tokens, dollars, and seconds", () => {
  const model = span("intake.extract", 0.2, 4.55, {
    kind: "llm",
    prompt_tokens: 812,
    completion_tokens: 674,
    cost_usd: "0.0006843200",
  });

  expect(formatTokens(model)).toBe("812 in / 674 out");
  expect(formatCost(model.cost_usd)).toBe("$0.000684");
  expect(formatSeconds(spanDurationMs(model, T0))).toBe("4.35 s");
  expect([formatCost("0"), formatCost(null), formatCost("1.5")]).toEqual(["$0", "—", "$1.5000"]);
});

specTest("run-dashboard", OPERATORS, "submitting a demo sample opens its live run view", async () => {
  const fetchMock = vi.fn(async () => Response.json({ id: "abc" }, { status: 202 }));

  const path = await submitDemo("injection", undefined, fetchMock as unknown as typeof fetch);

  expect(path).toBe("/requests/abc");
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("/api/demo/requests");
  expect(JSON.parse(init.body as string)).toEqual({ sample: "injection" });
});
