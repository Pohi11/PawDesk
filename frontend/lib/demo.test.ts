import { expect, vi } from "vitest";

import { specTest } from "../tests/spec";
import { certificateSrc, generateRequest, submitDemo } from "./demo";

const TRY = "The Try page previews a request and its certificate";

specTest("run-dashboard", TRY, "generating fetches a request and points at its seed's certificate", async () => {
  const generated = { seed: 42, pet: "Biscuit", message: "Hi", certificate_url: "/demo/generated/42/certificate.png" };
  const fetchMock = vi.fn(async () => Response.json(generated));

  const request = await generateRequest(fetchMock as unknown as typeof fetch);

  expect(fetchMock.mock.calls[0]).toEqual(["/api/demo/generate"]);
  expect(request).toEqual(generated);
  expect(certificateSrc({ seed: request.seed })).toBe("/api" + request.certificate_url);
  expect(certificateSrc({ sample: "injection" })).toBe("/api/demo/samples/injection/certificate.png");
});

specTest("run-dashboard", TRY, "a generated request is sent by its seed and opens its run", async () => {
  const fetchMock = vi.fn(async () => Response.json({ id: "abc" }, { status: 202 }));

  const plain = await submitDemo({ seed: 42 }, undefined, fetchMock as unknown as typeof fetch);
  await submitDemo({ seed: 42 }, "Edited message", fetchMock as unknown as typeof fetch);

  expect(plain).toBe("/requests/abc");
  const bodies = (fetchMock.mock.calls as unknown as [string, RequestInit][]).map(([url, init]) => {
    expect(url).toBe("/api/demo/requests");
    return JSON.parse(init.body as string);
  });
  expect(bodies).toEqual([{ seed: 42 }, { seed: 42, message: "Edited message" }]);
});

specTest("run-dashboard", TRY, "a failed generation says so", async () => {
  const fetchMock = vi.fn(async () => new Response("", { status: 502 }));

  await expect(generateRequest(fetchMock as unknown as typeof fetch)).rejects.toThrow("(502)");
});
