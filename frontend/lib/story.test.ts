import { expect, test } from "vitest";

import { specTest } from "../tests/spec";
import { flagText, optionText, outcome } from "./story";
import type { RequestDetail } from "./types";

const base = {
  steps: {},
  approvals: [],
  failed_step: null,
} as unknown as RequestDetail;

const WHO = "Outcome sentences name who decided";
const FAILED = "Failure sentences name the step in plain words";

function sentBy(action: string, staff_name: string): string {
  return outcome({
    ...base,
    status: "sent",
    approvals: [{ action, staff_name, reason: null, edited_reply: null, at: "" }],
  });
}

specTest("interface-copy", WHO, "a request sent with no approval says the checks passed it", () => {
  expect(outcome({ ...base, status: "sent" })).toBe("The checks passed it, so it went out without a person.");
});

specTest("interface-copy", WHO, "a staff decision starts with the staff member's name", () => {
  expect(sentBy("reject", "Sam")).toBe("Sam declined the request, and the pet parent got a polite no.");
  expect(sentBy("edit_and_approve", "Dana")).toBe("Dana edited the reply and sent it.");
  expect(sentBy("approve", "Dana")).toBe("Dana approved the reply, and the desk sent it.");
});

specTest("interface-copy", FAILED, "a failure names its step in words, never as a state", () => {
  const failedIn = (failed_step: string | null) => outcome({ ...base, status: "failed", failed_step });

  expect(failedIn("approved")).toBe("Stopped while sending the reply. Processing it again resumes from that step.");
  expect(failedIn("extracting")).toMatch(/^Stopped while reading the request\./);
  expect(failedIn("checking")).toMatch(/^Stopped while running the checks\./);
  expect(failedIn("resolving")).toMatch(/^Stopped while looking for other options\./);
  expect(failedIn("drafting")).toMatch(/^Stopped while writing the reply\./);
  expect(failedIn("ready")).toMatch(/^Stopped while approving the reply\./);
  expect(failedIn("rejected")).toMatch(/^Stopped while sending the reply\./);
  expect(failedIn("some_new_state")).toMatch(/^Stopped while working on it\./);
  expect(failedIn(null)).toMatch(/^Stopped while working on it\./);
});

test("flags read as plain reasons", () => {
  const injection =
    "came through resolving: not_attempted (needs a person: intake: message contains instruction-like text; intake: ambiguous: message contains instructions)";

  expect(flagText(injection)).toBe("message contains instruction-like text");
  expect(flagText("came through resolving: proposed (proposed)")).toBe("the resolver proposed other options");
  expect(flagText("reply: mentions a price: '$45'")).toBe("the reply mentions a price: '$45'");
  expect(
    outcome({ ...base, status: "needs_review", steps: { reply: { flags: [injection] } } }),
  ).toBe("Waiting for you: message contains instruction-like text.");
});

test("resolver options read as offers", () => {
  expect(optionText({ kind: "alternative_dates", start_date: "2027-03-13", end_date: "2027-03-16" })).toBe(
    "Other dates, Mar 13–16, 2027",
  );
  expect(optionText({ kind: "larger_kennel", size_class: "large" })).toBe("A large kennel for the same dates");
  expect(optionText({ kind: "vaccine_update", vaccines: ["bordetella"] })).toBe("An updated bordetella record");
});
