// Demo requests from the browser, through the dashboard's own proxy (spec: demo-generator).

export interface GeneratedRequest {
  seed: number;
  owner: string;
  pet: string;
  species: string;
  breed: string;
  weight_lb: number;
  service: string;
  start_date: string;
  end_date: string;
  message: string;
  scenario: string;
  scenario_text: string;
  clinic: string;
  vet: string;
  records: { vaccine: string; label: string; administered_on: string; expires_on: string }[];
  certificate_url: string;
}

export type DemoSource = { sample: string } | { seed: number };

/** Where the browser loads a certificate image: the backend path, behind the proxy. */
export function certificateSrc(source: DemoSource): string {
  return "seed" in source
    ? `/api/demo/generated/${source.seed}/certificate.png`
    : `/api/demo/samples/${source.sample}/certificate.png`;
}

/** How many generated names the Try page remembers and asks the server to avoid. */
export const RECENT_NAMES = 10;

/** The recent names with `name` first, without repeats, at most RECENT_NAMES long. */
export function rememberName(recent: string[], name: string): string[] {
  const others = recent.filter((n) => n.toLowerCase() !== name.toLowerCase());
  return [name, ...others].slice(0, RECENT_NAMES);
}

/** A new request whose pet is named none of `avoid` and no pet on file (spec: demo-generator). */
export async function generateRequest(
  avoid: string[] = [],
  fetchImpl: typeof fetch = fetch,
): Promise<GeneratedRequest> {
  const query = new URLSearchParams(avoid.map((name) => ["avoid", name])).toString();
  const response = await fetchImpl(query ? `/api/demo/generate?${query}` : "/api/demo/generate");
  if (!response.ok) throw new Error(`could not make up a request (${response.status})`);
  return (await response.json()) as GeneratedRequest;
}

/** Sends a sample or a generated request and returns the live run view's path for it. */
export async function submitDemo(
  source: DemoSource,
  message: string | undefined,
  fetchImpl: typeof fetch = fetch,
): Promise<string> {
  const response = await fetchImpl("/api/demo/requests", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(message ? { ...source, message } : source),
  });
  if (!response.ok) {
    throw new Error(`demo submission failed (${response.status})`);
  }
  const { id } = (await response.json()) as { id: string };
  return `/requests/${id}`;
}
