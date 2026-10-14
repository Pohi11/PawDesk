// "[spec <capability>: <requirement>] <name>": the frontend and end-to-end counterpart of
// the backend's @pytest.mark.spec marker (decision records 0004 and 0012). No test-runner
// imports here, so Vitest and Playwright tests can both use it.

export const SPEC_TAG = /^\[spec ([a-z0-9-]+): ([^\]]+)\] /;

export function specTag(capability: string, requirement: string): string {
  if (!/^[a-z0-9-]+$/.test(capability) || !requirement.trim() || requirement.includes("]")) {
    throw new Error(`malformed spec tag: ${capability} / ${requirement}`);
  }
  return `[spec ${capability}: ${requirement}]`;
}
