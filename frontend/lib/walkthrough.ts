// The build walkthrough's data shape and the links between its pages (spec: build-walkthrough).

export type RequirementStatus = "verified" | "failing" | "untested";

export interface LinkedTest {
  suite: "backend" | "frontend";
  id: string;
  status: "passed" | "failed" | "skipped";
  seconds: number;
}

export interface Requirement {
  name: string;
  text: string;
  scenarios: { name: string; steps: string[] }[];
  tests: LinkedTest[];
  status: RequirementStatus;
}

export interface Capability {
  capability: string;
  purpose: string;
  requirements: Requirement[];
}

export interface Change {
  id: string;
  slug: string;
  title: string;
  date: string;
  archived_at: string | null;
  why: string;
  what_changes: string;
  tasks: { title: string; items: { id: string; done: boolean; text: string }[] }[];
  requirements: { capability: string; kind: string; name: string }[];
  decisions: string[];
}

export interface Decision {
  number: string;
  title: string;
  date: string | null;
  status: string | null;
  markdown: string;
}

export interface Walkthrough {
  generated_at: string;
  reports: Record<"backend" | "frontend", string | null>;
  totals: {
    changes: number;
    requirements: number;
    verified: number;
    tests: Record<"backend" | "frontend", number>;
    linked_tests: number;
  };
  changes: Change[];
  specs: Capability[];
  decisions: Decision[];
}

export function slug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export const requirementAnchor = (capability: string, name: string) =>
  `req-${capability}-${slug(name)}`;
export const decisionAnchor = (number: string) => `adr-${number}`;
export const requirementHref = (capability: string, name: string) =>
  `/build/specs#${requirementAnchor(capability, name)}`;
export const decisionHref = (number: string) => `/build/decisions#${decisionAnchor(number)}`;

/** The current requirement a change refers to, if it still exists under that name. */
export function currentRequirement(
  data: Pick<Walkthrough, "specs">,
  capability: string,
  name: string,
): Requirement | undefined {
  return data.specs
    .find((c) => c.capability === capability)
    ?.requirements.find((r) => r.name === name);
}
