import { expect } from "vitest";

import { specTest } from "../tests/spec";
import { EDGE_PATH, STATE_AT, edgeKey, lifecycle, transitionSentences } from "./architecture";

const MATCHES = "The architecture page's lifecycle matches the backend";

specTest("run-dashboard", MATCHES, "each transition has exactly one arrow, and each arrow is a transition", () => {
  const transitions = lifecycle.transitions.map(edgeKey);

  expect(new Set(transitions).size).toBe(transitions.length);
  expect(Object.keys(EDGE_PATH).sort()).toEqual([...transitions].sort());
});

specTest("run-dashboard", MATCHES, "each state in the data has a place on the drawing", () => {
  const states = new Set([...lifecycle.transitions.flatMap((t) => [t.from, t.to]), ...lifecycle.can_fail, "failed"]);

  expect([...states].filter((s) => !(s in STATE_AT))).toEqual([]);
});

specTest("run-dashboard", MATCHES, "the description names the actor of each transition", () => {
  expect(transitionSentences([{ from: "needs_review", to: "approved", actor: "staff" }])).toEqual([
    "Staff moves a request from needs_review to approved.",
  ]);
});
