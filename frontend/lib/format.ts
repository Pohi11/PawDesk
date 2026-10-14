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

const MONTH = new Intl.DateTimeFormat("en-US", { month: "short", timeZone: "UTC" });

/** "Mar 10–13, 2027", "Mar 31 – Apr 2, 2027", or "Mar 15, 2027" for a single day. */
export function formatStay(start: string | null, end: string | null): string {
  if (!start) return "Dates unclear";
  const a = new Date(`${start}T00:00:00Z`);
  const b = new Date(`${(end ?? start)}T00:00:00Z`);
  const [ma, mb] = [MONTH.format(a), MONTH.format(b)];
  const [da, db, ya, yb] = [a.getUTCDate(), b.getUTCDate(), a.getUTCFullYear(), b.getUTCFullYear()];
  if (start === (end ?? start)) return `${ma} ${da}, ${ya}`;
  if (ya !== yb) return `${ma} ${da}, ${ya} – ${mb} ${db}, ${yb}`;
  if (ma === mb) return `${ma} ${da}–${db}, ${ya}`;
  return `${ma} ${da} – ${mb} ${db}, ${ya}`;
}

export function formatService(service: string | null): string {
  return service ? service[0].toUpperCase() + service.slice(1) : "Service unclear";
}
