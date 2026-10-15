// The Architecture page's lifecycle drawing (spec: run-dashboard). The transitions come from
// content/architecture.json, which a backend test checks against app/lifecycle.py; this file
// only says where each state sits and how each arrow runs.

import data from "@/content/architecture.json";

export type Actor = "system" | "staff";
export type Transition = { from: string; to: string; actor: Actor };
export type StepRow = { state: string; step: string; does: string };

export const lifecycle = data as { transitions: Transition[]; can_fail: string[]; steps: StepRow[] };

export const TAG = { w: 124, h: 36 };

/** Top-left corner of each state's tag. */
export const STATE_AT: Record<string, { x: number; y: number }> = {
  received: { x: 10, y: 150 },
  extracting: { x: 160, y: 150 },
  checking: { x: 310, y: 150 },
  resolving: { x: 460, y: 60 },
  drafting: { x: 610, y: 150 },
  ready: { x: 770, y: 60 },
  needs_review: { x: 770, y: 240 },
  approved: { x: 960, y: 60 },
  rejected: { x: 960, y: 240 },
  sent: { x: 1110, y: 150 },
  failed: { x: 10, y: 312 },
};

export const edgeKey = (t: Pick<Transition, "from" | "to">) => `${t.from}>${t.to}`;

/** One path per transition, keyed "from>to". */
export const EDGE_PATH: Record<string, string> = {
  "received>extracting": "M134 168 H160",
  "extracting>checking": "M284 168 H310",
  "checking>resolving": "M434 160 C452 160 442 78 460 78",
  "checking>drafting": "M434 176 H610",
  "resolving>drafting": "M584 78 C602 78 592 160 610 160",
  "drafting>ready": "M734 160 C755 160 750 78 770 78",
  "drafting>needs_review": "M734 176 C755 176 750 258 770 258",
  "ready>approved": "M894 78 H960",
  "ready>rejected": "M894 90 C925 90 930 246 960 246",
  "needs_review>approved": "M894 246 C925 246 930 90 960 90",
  "needs_review>rejected": "M894 266 H960",
  "approved>sent": "M1084 78 C1100 78 1095 160 1110 160",
  "rejected>sent": "M1084 258 C1100 258 1095 176 1110 176",
};

/** The transition list in words, for the diagram's screen reader description. */
export function transitionSentences(transitions: Transition[]): string[] {
  return transitions.map((t) => `${t.actor === "staff" ? "Staff" : "The system"} moves a request from ${t.from} to ${t.to}.`);
}
