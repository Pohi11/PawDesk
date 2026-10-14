// Demo requests from the browser, through the dashboard's own proxy (spec: demo-generator).

export interface GeneratedRequest {
  seed: number;
  owner: string;
  pet: string;
  species: string;
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

export async function generateRequest(fetchImpl: typeof fetch = fetch): Promise<GeneratedRequest> {
  const response = await fetchImpl("/api/demo/generate");
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
