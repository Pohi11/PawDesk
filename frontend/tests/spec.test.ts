import { expect, test } from "vitest";

import { SPEC_TAG, specTag } from "./spec";

test("a spec tag round-trips through the pattern the coverage check uses", () => {
  const tag = specTag("run-dashboard", "The timeline shows overlapping steps");

  const match = SPEC_TAG.exec(`${tag} bars overlap`);

  expect(match?.[1]).toBe("run-dashboard");
  expect(match?.[2]).toBe("The timeline shows overlapping steps");
});

test("malformed tags are refused when the test is defined", () => {
  expect(() => specTag("Run Dashboard", "x")).toThrow("malformed");
  expect(() => specTag("run-dashboard", " ")).toThrow("malformed");
  expect(() => specTag("run-dashboard", "a ] b")).toThrow("malformed");
});
