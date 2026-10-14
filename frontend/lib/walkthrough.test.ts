import { expect } from "vitest";

import data from "../content/walkthrough.json";
import { specTest } from "../tests/spec";
import {
  type Walkthrough,
  currentRequirement,
  decisionHref,
  requirementAnchor,
  requirementHref,
} from "./walkthrough";

const REQ = "Readers can follow every link in the pages";
const walkthrough = data as unknown as Walkthrough;

specTest("build-walkthrough", REQ, "anchors are stable and distinct", () => {
  const all = walkthrough.specs.flatMap((c) =>
    c.requirements.map((r) => requirementAnchor(c.capability, r.name)),
  );

  expect(requirementAnchor("booking-lifecycle", "Guards reject illegal moves")).toBe(
    requirementAnchor("booking-lifecycle", "Guards reject illegal moves"),
  );
  expect(new Set(all).size).toBe(all.length);
  expect(all.every((a) => /^req-[a-z0-9-]+$/.test(a))).toBe(true);
});

specTest("build-walkthrough", REQ, "a change's requirements lead to their tests and results", () => {
  const dashboard = walkthrough.changes.find((c) => c.slug === "phase-09-dashboard");
  const added = dashboard?.requirements.filter((r) => r.kind === "added") ?? [];

  expect(added.length).toBeGreaterThan(0);
  for (const ref of added) {
    const req = currentRequirement(walkthrough, ref.capability, ref.name);
    expect(req, ref.name).toBeDefined();
    expect(req?.tests.length, ref.name).toBeGreaterThan(0);
    expect(requirementHref(ref.capability, ref.name)).toBe(
      `/build/specs#${requirementAnchor(ref.capability, ref.name)}`,
    );
  }
});

specTest("build-walkthrough", REQ, "a change's decisions lead to the decision records", () => {
  const numbers = new Set(walkthrough.decisions.map((d) => d.number));
  const linked = walkthrough.changes.flatMap((c) => c.decisions);

  expect(linked.length).toBeGreaterThan(0);
  for (const number of linked) {
    expect(numbers.has(number), number).toBe(true);
    expect(decisionHref(number)).toBe(`/build/decisions#adr-${number}`);
  }
});
