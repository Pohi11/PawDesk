// Shapes an architecture comparison report into side-by-side rows (spec:
// architecture-comparison). Which side is better is decided per metric: fewer unsafe
// confirmations, errors, cost, and latency; more correct decisions and injections caught.

import { formatCost } from "./format";

export interface ArchitectureHeadline {
  cases: number;
  decision_accuracy: string;
  unsafe_confirmations: number;
  missed_confirmations: number;
  injections_to_person: string;
  errors: number;
  total_cost_usd: string;
  average_cost_usd: string;
  average_seconds: number | null;
  median_seconds: number | null;
  average_model_calls: number | null;
}

export type Architecture = "hybrid" | "autonomous";

export interface ComparisonRow {
  label: string;
  hybrid: string;
  autonomous: string;
  better: Architecture | null;
}

type Metric = {
  key: keyof ArchitectureHeadline;
  label: string;
  higherIsBetter: boolean;
  format?: (value: ArchitectureHeadline[keyof ArchitectureHeadline]) => string;
};

const METRICS: Metric[] = [
  { key: "decision_accuracy", label: "Decision accuracy", higherIsBetter: true },
  { key: "unsafe_confirmations", label: "Unsafe confirmations", higherIsBetter: false },
  { key: "missed_confirmations", label: "Missed confirmations", higherIsBetter: false },
  { key: "injections_to_person", label: "Injections handed to a person", higherIsBetter: true },
  { key: "errors", label: "Errors", higherIsBetter: false },
  { key: "average_cost_usd", label: "Average cost per case", higherIsBetter: false, format: (v) => formatCost(v as string) },
  { key: "average_seconds", label: "Average latency", higherIsBetter: false, format: (v) => (v === null ? "—" : `${v} s`) },
  { key: "median_seconds", label: "Median latency", higherIsBetter: false, format: (v) => (v === null ? "—" : `${v} s`) },
  { key: "average_model_calls", label: "Average model calls", higherIsBetter: false },
];

/** "33/36" → 0.9167; numbers and numeric strings as themselves. */
export function numeric(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return value;
  const text = String(value);
  const fraction = text.match(/^(\d+)\/(\d+)$/);
  if (fraction) return Number(fraction[2]) === 0 ? null : Number(fraction[1]) / Number(fraction[2]);
  const n = Number(text);
  return Number.isFinite(n) ? n : null;
}

export function comparisonRows(headline: Record<Architecture, ArchitectureHeadline>): ComparisonRow[] {
  return METRICS.map(({ key, label, higherIsBetter, format }) => {
    const [h, a] = [headline.hybrid[key], headline.autonomous[key]];
    const [hn, an] = [numeric(h), numeric(a)];
    let better: Architecture | null = null;
    if (hn !== null && an !== null && hn !== an) {
      better = (hn > an) === higherIsBetter ? "hybrid" : "autonomous";
    }
    const show = format ?? ((v: unknown) => (v === null ? "—" : String(v)));
    return { label, hybrid: show(h), autonomous: show(a), better };
  });
}
