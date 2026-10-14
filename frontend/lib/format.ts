// Display formatting shared by the inspector, tables, and charts.

import type { SpanSummary } from "./types";

/** Dollars, with enough decimals that sub-cent model costs stay visible. */
export function formatCost(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  if (n === 0) return "$0";
  return `$${n.toFixed(n < 0.01 ? 6 : 4)}`;
}

export function formatSeconds(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return `${(ms / 1000).toFixed(2)} s`;
}

export function spanDurationMs(span: SpanSummary, nowMs: number): number {
  const end = span.ended_at ? Date.parse(span.ended_at) : nowMs;
  return end - Date.parse(span.started_at);
}

export function formatTokens(span: Pick<SpanSummary, "prompt_tokens" | "completion_tokens">): string {
  if (span.prompt_tokens === null && span.completion_tokens === null) return "—";
  return `${span.prompt_tokens ?? 0} in / ${span.completion_tokens ?? 0} out`;
}
