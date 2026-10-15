import { expect, vi } from "vitest";

import { specTest } from "../tests/spec";
import { petPhoto } from "./pet-photo";
import {
  RECENT_NAMES,
  type GeneratedRequest,
  certificateSrc,
  generateRequest,
  generatedPet,
  rememberName,
  submitDemo,
} from "./demo";

const TRY = "The Try page previews a request and its certificate";

specTest("run-dashboard", TRY, "generating fetches a request and points at its seed's certificate", async () => {
  const generated = { seed: 42, pet: "Biscuit", message: "Hi", certificate_url: "/demo/generated/42/certificate.png" };
  const fetchMock = vi.fn(async () => Response.json(generated));

  const request = await generateRequest([], fetchMock as unknown as typeof fetch);

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

  await expect(generateRequest([], fetchMock as unknown as typeof fetch)).rejects.toThrow("(502)");
});

specTest("run-dashboard", TRY, "recent names go with each generation", async () => {
  const fetchMock = vi.fn(async () => Response.json({ seed: 7, pet: "Nacho" }));

  await generateRequest(["Juno", "Pickle"], fetchMock as unknown as typeof fetch);

  const [url] = fetchMock.mock.calls[0] as unknown as [string];
  expect(url).toBe("/api/demo/generate?avoid=Juno&avoid=Pickle");
});

specTest("run-dashboard", TRY, "the page remembers the latest names, newest first, without repeats", () => {
  let recent: string[] = [];
  for (const name of ["Juno", "Pickle", "juno"]) recent = rememberName(recent, name);
  expect(recent).toEqual(["juno", "Pickle"]);

  for (let i = 0; i < 20; i++) recent = rememberName(recent, `Pet ${i}`);
  expect(recent).toHaveLength(RECENT_NAMES);
  expect(recent[0]).toBe("Pet 19");
});

specTest(
  "pet-photos",
  "The Try page shows each request's pet photo",
  "a generated pet keeps its photo once sent",
  () => {
    const preview = {
      pet: "Xena",
      pet_id: "0b7f6e1c-3a52-5d0e-9c41-2f6a7b8c9d10",
      species: "dog",
      breed: "Standard Poodle", // not in the photo set: a general photo picked from the id
    } as GeneratedRequest;
    // What the run page has once intake matches the pet added with the seed's id.
    const sent = { pet: "Xena", pet_id: preview.pet_id, pet_species: "dog", pet_breed: "Standard Poodle" };

    const shown = petPhoto(generatedPet(preview));

    expect(shown).not.toBeNull();
    expect(shown?.breed).toBeNull();
    expect(shown).toEqual(petPhoto(sent));
    expect(petPhoto(generatedPet({ ...preview, breed: "Beagle" }))?.breed).toBe("Beagle");
  },
);
