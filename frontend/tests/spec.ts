import { test } from "vitest";

// "[spec <capability>: <requirement>] <name>": the frontend counterpart of the backend's
// @pytest.mark.spec marker (decision records 0004 and 0012).
export const SPEC_TAG = /^\[spec ([a-z0-9-]+): ([^\]]+)\] /;

export function specTag(capability: string, requirement: string): string {
  if (!/^[a-z0-9-]+$/.test(capability) || !requirement.trim() || requirement.includes("]")) {
    throw new Error(`malformed spec tag: ${capability} / ${requirement}`);
  }
  return `[spec ${capability}: ${requirement}]`;
}

export function specTest(
  capability: string,
  requirement: string,
  name: string,
  fn: () => void | Promise<void>,
): void {
  test(`${specTag(capability, requirement)} ${name}`, fn);
}
