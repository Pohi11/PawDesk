// Submitting a demo sample from the browser, through the dashboard's own proxy.

/** Submits the sample and returns the live run view's path for the new request. */
export async function submitDemo(
  sample: string,
  message: string | undefined,
  fetchImpl: typeof fetch = fetch,
): Promise<string> {
  const response = await fetchImpl("/api/demo/requests", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(message ? { sample, message } : { sample }),
  });
  if (!response.ok) {
    throw new Error(`demo submission failed (${response.status})`);
  }
  const { id } = (await response.json()) as { id: string };
  return `/requests/${id}`;
}
