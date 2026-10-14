// Shapes returned by the backend's observability API (spec: observability-api).

export type SpanKind = "llm" | "tool" | "code" | "human";
export type SpanStatus = "running" | "ok" | "error";

export interface SpanSummary {
  id: string;
  trace_id: string;
  parent_span_id: string | null;
  name: string;
  kind: SpanKind;
  status: SpanStatus;
  started_at: string;
  ended_at: string | null;
  model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_usd: string | null;
}

export interface SpanDetail extends SpanSummary {
  input: unknown;
  output: unknown;
  attributes: Record<string, unknown>;
  error: string | null;
}

export interface Snapshot {
  status: string;
  failed_step: string | null;
  flagged: boolean | null;
  spans: SpanSummary[];
}

export interface TraceDetail {
  id: string;
  name: string;
  started_at: string;
  ended_at: string | null;
  spans: SpanDetail[];
}

/** The matched pet. Every field is null until intake matches the request to a pet on file. */
export interface PetFields {
  pet: string | null;
  pet_id: string | null;
  pet_species: string | null;
  pet_breed: string | null;
}

export interface RequestDetail extends PetFields {
  id: string;
  status: string;
  failed_step: string | null;
  last_error: string | null;
  created_at: string;
  owner: string;
  raw_message: string;
  transitions: { from: string; to: string; actor: string; reason: string | null; at: string }[];
  steps: Record<string, Record<string, unknown>>;
  approvals: {
    action: string;
    staff_name: string;
    reason: string | null;
    edited_reply: string | null;
    at: string;
  }[];
  message: { kind: string; subject: string; body: string } | null;
  traces: TraceDetail[];
}

export interface RequestRow extends PetFields {
  id: string;
  status: string;
  created_at: string;
  owner: string;
  service: string | null;
  start_date: string | null;
  end_date: string | null;
  cost_usd: string;
  flagged: boolean;
}

export interface ReviewItem {
  id: string;
  created_at: string;
  owner: string;
  pet: string | null;
  service: string | null;
  start_date: string | null;
  end_date: string | null;
  situation: string | null;
  flags: string[];
  draft: { subject: string; body: string } | null;
}

export interface Metrics {
  requests_by_state: Record<string, number>;
  cost: { total_usd: string; average_per_request_usd: string; requests_with_cost: number };
  model_steps: { name: string; calls: number; cost_usd: string; average_seconds: number | null }[];
  run_seconds: { p50: number | null; p95: number | null; runs: number };
  flag_rate: { flagged: number; drafted: number; rate: number | null };
}

export interface EvalReport {
  file: string;
  kind: string;
  benchmark: string | null;
  prompt_version: string | null;
  model: string | null;
  run_at: string | null;
  cost_usd: string;
  headline: Record<string, unknown>;
}

export interface DemoSample {
  id: string;
  title: string;
  expect: string;
  message: string;
  certificate: string | null;
}
