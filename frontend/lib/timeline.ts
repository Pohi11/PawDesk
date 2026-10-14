// Waterfall layout for one trace's spans (spec: run-dashboard): each bar is placed by its
// start and end relative to the trace's first span, and indented by its depth in the tree,
// so concurrent steps visibly overlap.

import type { SpanSummary } from "./types";

export interface Bar {
  span: SpanSummary;
  offsetMs: number;
  widthMs: number;
  depth: number;
}

export function layout(spans: readonly SpanSummary[], nowMs: number): { bars: Bar[]; totalMs: number } {
  if (spans.length === 0) return { bars: [], totalMs: 0 };

  const byId = new Map(spans.map((s) => [s.id, s]));
  const depth = (span: SpanSummary): number => {
    let d = 0;
    let parent = span.parent_span_id ? byId.get(span.parent_span_id) : undefined;
    while (parent) {
      d += 1;
      parent = parent.parent_span_id ? byId.get(parent.parent_span_id) : undefined;
    }
    return d;
  };

  const start = Math.min(...spans.map((s) => Date.parse(s.started_at)));
  const bars = [...spans]
    .sort((a, b) => a.started_at.localeCompare(b.started_at))
    .map((span) => {
      const from = Date.parse(span.started_at);
      // A span still running extends to now.
      const to = span.ended_at ? Date.parse(span.ended_at) : nowMs;
      return { span, offsetMs: from - start, widthMs: Math.max(to - from, 0), depth: depth(span) };
    });
  const totalMs = Math.max(...bars.map((b) => b.offsetMs + b.widthMs), 1);
  return { bars, totalMs };
}

export function overlaps(a: Bar, b: Bar): boolean {
  return a.offsetMs < b.offsetMs + b.widthMs && b.offsetMs < a.offsetMs + a.widthMs;
}
