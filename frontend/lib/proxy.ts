// Which browser requests the dashboard forwards to the backend (spec: run-dashboard).
// Everything not listed here is answered 404 without contacting the backend, so the
// browser can reach only the reads and staff actions the dashboard needs.

const ID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

const RULES: ReadonlyArray<{ method: string; pattern: RegExp }> = [
  { method: "GET", pattern: /^requests$/ },
  { method: "GET", pattern: new RegExp(`^requests/${ID}$`) },
  { method: "GET", pattern: new RegExp(`^requests/${ID}/events$`) },
  { method: "GET", pattern: /^reviews$/ },
  { method: "GET", pattern: /^metrics$/ },
  { method: "GET", pattern: /^evals$/ },
  { method: "GET", pattern: /^demo\/samples$/ },
  { method: "POST", pattern: new RegExp(`^requests/${ID}/(approve|edit-and-approve|reject)$`) },
  { method: "POST", pattern: /^demo\/requests$/ },
];

/** The backend path to call, or null when the request must not be forwarded. */
export function allowedPath(method: string, segments: readonly string[]): string | null {
  const path = segments.join("/");
  const ok = RULES.some((rule) => rule.method === method && rule.pattern.test(path));
  return ok ? path : null;
}
