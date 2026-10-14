import { NextRequest } from "next/server";
import { afterEach, expect, vi } from "vitest";

import { DELETE, GET } from "../app/api/[...path]/route";
import { specTest } from "../tests/spec";
import { allowedPath } from "./proxy";

const ID = "01a13bf4-9a05-7bc6-a5b0-497142252250";
const REQ = "The backend is reached only through an allowlisted proxy";

const ctx = (path: string[]) => ({ params: Promise.resolve({ path }) });

afterEach(() => {
  vi.unstubAllGlobals();
});

specTest("run-dashboard", REQ, "reads and staff actions are allowed", () => {
  expect(allowedPath("GET", ["requests", ID, "events"])).toBe(`requests/${ID}/events`);
  expect(allowedPath("GET", ["metrics"])).toBe("metrics");
  expect(allowedPath("POST", ["requests", ID, "reject"])).toBe(`requests/${ID}/reject`);
  expect(allowedPath("POST", ["demo", "requests"])).toBe("demo/requests");
});

specTest("run-dashboard", REQ, "everything else is refused", () => {
  expect(allowedPath("GET", ["health", "db"])).toBeNull();
  expect(allowedPath("DELETE", ["requests", ID])).toBeNull();
  expect(allowedPath("POST", ["requests", ID])).toBeNull();
  expect(allowedPath("GET", ["requests", "..", "health"])).toBeNull();
  expect(allowedPath("GET", ["requests", "not-an-id"])).toBeNull();
});

specTest("run-dashboard", REQ, "an allowed path streams the backend response through", async () => {
  const chunks = ["event: snapshot\ndata: {}\n\n", "event: end\ndata: {}\n\n"];
  const fetchMock = vi.fn(async () => {
    const stream = new ReadableStream({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
        controller.close();
      },
    });
    return new Response(stream, { headers: { "content-type": "text/event-stream" } });
  });
  vi.stubGlobal("fetch", fetchMock);

  const response = await GET(
    new NextRequest(`http://dash/api/requests/${ID}/events`),
    ctx(["requests", ID, "events"]),
  );

  expect(response.headers.get("content-type")).toBe("text/event-stream");
  expect(await response.text()).toBe(chunks.join(""));
  const [url] = fetchMock.mock.calls[0] as unknown as [URL];
  expect(url.pathname).toBe(`/requests/${ID}/events`);
});

specTest("run-dashboard", REQ, "a refused path never contacts the backend", async () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);

  const refused = await GET(new NextRequest("http://dash/api/health/db"), ctx(["health", "db"]));
  const deleted = await DELETE();

  expect([refused.status, deleted.status]).toEqual([404, 404]);
  expect(fetchMock).not.toHaveBeenCalled();
});

specTest("run-dashboard", REQ, "demo previews and certificate images are allowed", () => {
  expect(allowedPath("GET", ["demo", "generate"])).toBe("demo/generate");
  expect(allowedPath("GET", ["demo", "generated", "42", "certificate.png"])).toBe(
    "demo/generated/42/certificate.png",
  );
  expect(allowedPath("GET", ["demo", "samples", "injection", "certificate.png"])).toBe(
    "demo/samples/injection/certificate.png",
  );
  expect(allowedPath("GET", ["demo", "generated", "x", "certificate.png"])).toBeNull();
  expect(allowedPath("GET", ["demo", "generated", "42", "..", "certificate.png"])).toBeNull();
  expect(allowedPath("POST", ["demo", "generate"])).toBeNull();
});

specTest("run-dashboard", REQ, "certificate images pass through unchanged", async () => {
  const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 255, 7]);
  const fetchMock = vi.fn(async () => new Response(png, { headers: { "content-type": "image/png" } }));
  vi.stubGlobal("fetch", fetchMock);

  const response = await GET(
    new NextRequest("http://dash/api/demo/generated/42/certificate.png"),
    ctx(["demo", "generated", "42", "certificate.png"]),
  );

  expect(response.headers.get("content-type")).toBe("image/png");
  expect(new Uint8Array(await response.arrayBuffer())).toEqual(png);
  const [url] = fetchMock.mock.calls[0] as unknown as [URL];
  expect(url.pathname).toBe("/demo/generated/42/certificate.png");
});
