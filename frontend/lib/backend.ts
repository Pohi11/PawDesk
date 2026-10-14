// Server-side access to the backend, for server components only. The browser never calls
// this: it goes through the allowlisted proxy in app/api/[...path]/route.ts.

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export class BackendError extends Error {
  constructor(
    readonly status: number,
    path: string,
  ) {
    super(`backend answered ${status} for ${path}`);
  }
}

export async function backendJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new BackendError(response.status, path);
  }
  return (await response.json()) as T;
}
