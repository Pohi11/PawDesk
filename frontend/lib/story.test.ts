import { expect, test } from "vitest";

import { flagText, optionText, outcome } from "./story";
import type { RequestDetail } from "./types";

const base = {
  steps: {},
  approvals: [],
  failed_step: null,
} as unknown as RequestDetail;

test("the outcome sentence says who decided", () => {
  expect(outcome({ ...base, status: "sent" })).toMatch(/^Sent automatically/);
  expect(
    outcome({
      ...base,
      status: "sent",
      approvals: [{ action: "edit_and_approve", staff_name: "Dana", reason: null, edited_reply: "x", at: "" }],
    }),
  ).toBe("Sent after Dana edited the reply.");
  expect(
    outcome({
      ...base,
      status: "sent",
      approvals: [{ action: "reject", staff_name: "Sam", reason: "x", edited_reply: null, at: "" }],
    }),
  ).toBe("Declined by Sam. A polite decline was sent.");
  expect(outcome({ ...base, status: "failed", failed_step: "approved" })).toBe(
    "Stopped while approved. It can be retried.",
  );
});

test("flags read as plain reasons", () => {
  const injection =
    "came through resolving: not_attempted (needs a person: intake: message contains instruction-like text; intake: ambiguous: message contains instructions)";

  expect(flagText(injection)).toBe("message contains instruction-like text");
  expect(flagText("came through resolving: proposed (proposed)")).toBe("the request needed other options");
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
