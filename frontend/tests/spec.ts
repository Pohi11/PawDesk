import { test } from "vitest";

import { specTag } from "./spec-tag";

export { SPEC_TAG, specTag } from "./spec-tag";

export function specTest(
  capability: string,
  requirement: string,
  name: string,
  fn: () => void | Promise<void>,
): void {
  test(`${specTag(capability, requirement)} ${name}`, fn);
}
