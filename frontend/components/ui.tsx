// Small presentational pieces shared by server and client components (no hooks).

import type { ReactNode } from "react";

import type { NodeStatus } from "@/lib/graph";
import type { SpanKind } from "@/lib/types";

export const KIND_STYLE: Record<SpanKind, { label: string; dot: string; border: string }> = {
  llm: { label: "model", dot: "bg-violet-500", border: "#8b5cf6" },
  code: { label: "code", dot: "bg-sky-500", border: "#0ea5e9" },
  tool: { label: "tool", dot: "bg-amber-500", border: "#f59e0b" },
  human: { label: "human", dot: "bg-emerald-500", border: "#10b981" },
};

export const NODE_STATUS_STYLE: Record<NodeStatus, { fill: string; text: string }> = {
  waiting: { fill: "#f4f4f5", text: "#71717a" },
  running: { fill: "#dbeafe", text: "#1d4ed8" },
  ok: { fill: "#dcfce7", text: "#15803d" },
  error: { fill: "#fee2e2", text: "#b91c1c" },
  skipped: { fill: "#fafafa", text: "#a1a1aa" },
};

const STATUS_COLORS: Record<string, string> = {
  received: "bg-zinc-100 text-zinc-700",
  extracting: "bg-blue-100 text-blue-800",
  checking: "bg-blue-100 text-blue-800",
  resolving: "bg-blue-100 text-blue-800",
  drafting: "bg-blue-100 text-blue-800",
  ready: "bg-sky-100 text-sky-800",
  approved: "bg-sky-100 text-sky-800",
  needs_review: "bg-amber-100 text-amber-800",
  rejected: "bg-zinc-200 text-zinc-800",
  sent: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status] ?? "bg-zinc-100 text-zinc-700"}`}
    >
      {status.replace("_", " ")}
    </span>
  );
}

export function KindDot({ kind }: { kind: SpanKind }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${KIND_STYLE[kind].dot}`} />;
}

export function Card({
  title,
  children,
  className = "",
}: {
  title?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-zinc-200 bg-white p-4 shadow-sm ${className}`}>
      {title && <h2 className="mb-3 text-sm font-semibold text-zinc-700">{title}</h2>}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </div>
  );
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {children && <p className="mt-1 max-w-3xl text-sm text-zinc-600">{children}</p>}
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <p className="animate-pulse text-sm text-zinc-500">{label}</p>;
}

export function Json({ value }: { value: unknown }) {
  return (
    <pre className="max-h-80 overflow-auto rounded-lg bg-zinc-950 p-3 font-mono text-xs leading-relaxed text-zinc-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
