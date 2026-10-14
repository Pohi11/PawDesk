// Shared presentational pieces (no hooks), usable from server and client components.

import type { ReactNode } from "react";

import type { NodeStatus } from "@/lib/graph";
import type { SpanKind } from "@/lib/types";

export const KIND_STYLE: Record<SpanKind, { label: string; dot: string; color: string; soft: string }> = {
  llm: { label: "Model", dot: "bg-model", color: "#5847c2", soft: "#e8e5fa" },
  code: { label: "Code", dot: "bg-code", color: "#2d5da8", soft: "#e1eaf7" },
  tool: { label: "Tool", dot: "bg-tool", color: "#b7791f", soft: "#f6ead6" },
  human: { label: "Person", dot: "bg-signal", color: "#e4621b", soft: "#fde7da" },
};

export const NODE_STATUS_LABEL: Record<NodeStatus, string> = {
  waiting: "Not yet",
  running: "Working",
  ok: "Done",
  error: "Failed",
  skipped: "Not needed",
};

// What each request state means to the person at the desk.
const STATE: Record<string, { label: string; tone: "work" | "act" | "done" | "fail" | "quiet" }> = {
  received: { label: "Received", tone: "quiet" },
  extracting: { label: "Reading", tone: "work" },
  checking: { label: "Checking", tone: "work" },
  resolving: { label: "Finding options", tone: "work" },
  drafting: { label: "Writing reply", tone: "work" },
  ready: { label: "Approved by checks", tone: "work" },
  approved: { label: "Approved", tone: "work" },
  needs_review: { label: "Waiting for you", tone: "act" },
  rejected: { label: "Declined", tone: "quiet" },
  sent: { label: "Sent", tone: "done" },
  failed: { label: "Failed", tone: "fail" },
};

const TONE = {
  work: "bg-code-soft text-code",
  act: "bg-signal text-white",
  done: "bg-kennel-soft text-kennel",
  fail: "bg-error-soft text-error",
  quiet: "bg-wash text-muted ring-1 ring-rule",
} as const;

export function stateLabel(status: string): string {
  return STATE[status]?.label ?? status.replace("_", " ");
}

/** A request's state as a kennel ID tag: a small tag with a punched hole. */
export function StateTag({ status }: { status: string }) {
  const { label, tone } = STATE[status] ?? { label: status, tone: "quiet" as const };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-r-full rounded-l-md py-0.5 pr-2.5 pl-1.5 text-xs font-medium whitespace-nowrap ${TONE[tone]}`}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-paper ring-1 ring-black/10" />
      {label}
    </span>
  );
}

export function KindDot({ kind }: { kind: SpanKind }) {
  return <span aria-hidden className={`inline-block h-2 w-2 rounded-full ${KIND_STYLE[kind].dot}`} />;
}

export function Panel({
  title,
  aside,
  children,
  className = "",
}: {
  title?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl bg-surface p-5 ring-1 ring-rule ${className}`}>
      {(title || aside) && (
        <div className="mb-4 flex items-baseline justify-between gap-4">
          {title && <h2 className="text-lg font-semibold">{title}</h2>}
          {aside && <div className="text-sm text-muted">{aside}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Figure({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return (
    <div>
      <div className="text-sm text-muted">{label}</div>
      <div className="font-display text-3xl font-semibold">{value}</div>
      {note && <div className="mt-0.5 text-sm text-faint">{note}</div>}
    </div>
  );
}

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="mb-8 max-w-2xl">
      <h1 className="text-4xl font-bold">{title}</h1>
      {children && <p className="mt-2 text-base leading-relaxed text-muted">{children}</p>}
    </header>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return <p className="text-sm text-muted motion-safe:animate-pulse">{label}</p>;
}

export function Json({ value }: { value: unknown }) {
  return (
    <pre className="max-h-80 overflow-auto rounded-lg bg-ink p-3 font-mono text-xs leading-relaxed text-white/90">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
