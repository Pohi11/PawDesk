// What each step on the path does, and what it found in this run (spec: run-dashboard,
// "Path steps explain themselves"). Pure, like nodeStatuses: the live view calls it again on
// every snapshot. Saved step outputs are untyped JSON, so every field is checked before use,
// and only structured facts are shown, never the pet parent's words or model free text.

import { formatStay } from "./format";
import type { NodeId, NodeStatus } from "./graph";
import type { RequestDetail } from "./types";

export interface StepSummary {
  does: string;
  result: string;
}

const DOES: Record<NodeId, string> = {
  intake: "A model reads the message for the pet, the service, and the dates.",
  records: "A model reads the attached vaccine card, if there is one.",
  compliance: "Code checks every required vaccine against the stay.",
  capacity: "A query looks for a free kennel of the pet's size for the stay.",
  route: "Code decides: straight to a reply, or look for options first.",
  resolver: "An agent looks for options that work, and code checks each one.",
  reply: "A model drafts the reply, and code checks it promises nothing the checks don't support.",
  review: "A person approves, edits, or declines anything flagged.",
  send: "Code sends the reply and, on a confirmation, reserves the kennel.",
};

const VACCINE: Record<string, string> = {
  rabies: "Rabies",
  dhpp: "DHPP",
  bordetella: "Bordetella",
  canine_influenza: "Canine influenza",
  leptospirosis: "Leptospirosis",
  fvrcp: "FVRCP",
  felv: "FeLV",
};

const PROBLEM: Record<string, string> = {
  expired: "expired before the stay",
  expires_during_stay: "expires during the stay",
  missing: "is missing",
  not_yet_given: "is given only after the stay starts",
  unknown_expiry: "has no expiry date",
};

// The first word of each routing reason says which check raised it.
const REASON_SOURCE: [string, string][] = [
  ["intake:", "the message"],
  ["records:", "the vaccine card"],
  ["vaccine ", "vaccines"],
  ["capacity:", "kennel space"],
  ["pet unknown", "an unmatched pet"],
  ["service or dates", "unusable dates"],
];

type Json = Record<string, unknown>;

const obj = (value: unknown): Json | undefined =>
  value !== null && typeof value === "object" && !Array.isArray(value) ? (value as Json) : undefined;
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const text = (value: unknown): string | undefined => (typeof value === "string" ? value : undefined);
const vaccine = (value: unknown) => VACCINE[String(value)] ?? String(value);
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

function joinAnd(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

export function stepSummary(id: NodeId, status: NodeStatus, detail: RequestDetail): StepSummary {
  return { does: DOES[id], result: result(id, status, detail) };
}

function result(id: NodeId, status: NodeStatus, detail: RequestDetail): string {
  if (status === "waiting") return "Not run yet.";
  if (status === "running") return id === "review" ? "Waiting for a person." : "Working on it now.";
  if (status === "error") return "Failed here. Processing the request again resumes from this step.";
  const steps = detail.steps;
  switch (id) {
    case "intake":
      return intake(obj(steps.intake), detail.pet);
    case "records":
      return records(obj(steps.records));
    case "compliance":
      return compliance(obj(steps.checks));
    case "capacity":
      return capacity(obj(steps.checks), obj(obj(steps.intake)?.intent));
    case "route":
      return route(obj(steps.route));
    case "resolver":
      return resolver(status, obj(steps.resolution));
    case "reply":
      return reply(obj(steps.reply));
    case "review":
      return review(status, detail);
    case "send":
      return send(detail);
  }
}

function intake(step: Json | undefined, pet: string | null): string {
  const intent = obj(step?.intent);
  if (!intent) return step ? "Couldn't read a booking from the message." : "Done.";
  const service = text(intent.service)?.toLowerCase() ?? "a booking";
  const start = text(intent.start_date) ?? null;
  const stay = start ? formatStay(start, text(intent.end_date) ?? null) : "with no clear dates";
  const read = pet ? `Read ${service} for ${pet}, ${stay}.` : `Read ${service}, ${stay}, but no pet on file matched.`;
  const issues = list(step?.issues).length;
  return issues ? `${read} Flagged ${plural(issues, "thing")} for a person.` : read;
}

function records(step: Json | undefined): string {
  if (!step) return "Done.";
  if (text(step.skipped) || step.outcome === "skipped") return "Skipped: no vaccine card was attached.";
  const extraction = obj(step.extraction);
  if (extraction?.readable === false) return "Couldn't read the card. A person will look.";
  const names = list(extraction?.records).map((r) => vaccine(obj(r)?.vaccine));
  const read = names.length
    ? `Read ${plural(names.length, "vaccine")} from the card: ${joinAnd(names)}.`
    : "Found no vaccines on the card.";
  const issues = list(step.issues).length;
  return issues ? `${read} Flagged ${plural(issues, "thing")} for a person.` : read;
}

function compliance(checks: Json | undefined): string {
  const result = obj(checks?.compliance);
  if (!result) {
    const reason = text(checks?.not_checked);
    if (reason?.startsWith("pet unknown")) return "Not checked: no pet on file matched.";
    if (reason) return "Not checked: the service or dates couldn't be used.";
    return "Not checked.";
  }
  const failing = list(result.checks)
    .map(obj)
    .filter((c) => c && c.status !== "ok")
    .map((c) => `${vaccine(c?.vaccine)} ${PROBLEM[String(c?.status)] ?? String(c?.status)}`);
  if (failing.length) return `${failing.join("; ")}.`;
  const checked = list(result.checks).length;
  return `Every required vaccine covers the stay (${plural(checked, "vaccine")} checked).`;
}

function capacity(checks: Json | undefined, intent: Json | undefined): string {
  const result = obj(checks?.capacity);
  switch (result?.status) {
    case "found":
      return `Kennel ${String(result.kennel)} is free for the stay.`;
    case "none_free":
      return `No ${String(result.size_class)} kennel is free for the stay.`;
    case "already_booked":
      return `${text(obj(checks?.pet)?.name) ?? "The pet"} already has a kennel for these nights.`;
    case "not_needed":
      return `Not needed: ${text(intent?.service) ?? "this service"} doesn't use a kennel.`;
    default:
      return "Not checked.";
  }
}

function route(step: Json | undefined): string {
  const reasons = list(step?.reasons).map(String);
  if (!step) return "Done.";
  if (!reasons.length) return "Every check passed, so straight to the reply.";
  const sources = [
    ...new Set(reasons.map((r) => REASON_SOURCE.find(([prefix]) => r.startsWith(prefix))?.[1] ?? "other checks")),
  ];
  return `${plural(reasons.length, "thing")} to look at (${joinAnd(sources)}), so on to the resolver.`;
}

function resolver(status: NodeStatus, step: Json | undefined): string {
  if (status === "skipped") return "Not needed: there was nothing to work around.";
  switch (step?.outcome) {
    case "proposed": {
      const options = list(obj(step.proposal)?.options).map(obj);
      const checked = options.filter((o) => o?.verified === true).length;
      const all = checked === options.length ? (options.length === 1 ? ", checked" : ", all checked") : `, ${checked} checked`;
      return `Found ${plural(options.length, "option")}${all}.`;
    }
    case "escalated":
      return "Stopped without an option that checks out, so a person takes over.";
    case "not_attempted":
      return "Didn't try: this needs a person, not other options.";
    default:
      return "Done.";
  }
}

const SITUATION: Record<string, string> = {
  confirmed: "Drafted a confirmation",
  alternatives: "Drafted a reply offering the options",
  under_review: "Drafted a holding reply while a person looks",
};

function reply(step: Json | undefined): string {
  if (!step) return "Done.";
  const drafted = SITUATION[String(step.situation)] ?? "Drafted a reply";
  if (list(step.promise_issues).length) return `${drafted}. It promised more than the checks support, so a person reviews it.`;
  if (step.target === "ready") return `${drafted}. It passed the promise check and goes out without review.`;
  return `${drafted}. A person reviews it before it goes out.`;
}

// The staff member leads the sentence, as in the outcome sentence (spec: interface-copy).
const DECIDED: Record<string, string> = {
  approve: "approved the reply",
  edit_and_approve: "edited the reply and approved it",
  reject: "declined the request",
};

function review(status: NodeStatus, detail: RequestDetail): string {
  if (status === "skipped") return "Not needed: nothing was flagged.";
  const approval = detail.approvals.at(-1);
  if (!approval) return "Done.";
  return `${approval.staff_name} ${DECIDED[approval.action] ?? "decided"}.`;
}

function send(detail: RequestDetail): string {
  if (!detail.message) return "Done.";
  return detail.message.kind === "decline" ? "Sent a polite decline." : `Sent the reply to ${detail.owner}.`;
}
