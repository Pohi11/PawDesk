import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { expect } from "vitest";

import { PET_PHOTOS } from "../lib/pet-photo";
import { specTest } from "./spec";

const LICENSED = "Every committed photo is licensed for reuse and recorded";
const NO_METADATA = "Committed photos carry no embedded metadata";

const PUBLIC = join(__dirname, "..", "public");
const PHOTO_DIR = join(PUBLIC, "pets");
// The backend's Species enum (backend/app/enums.py).
const SPECIES = ["dog", "cat"];

/** The EXIF and XMP blocks in a JPEG; both travel in APP1 segments, named by a prefix. */
function metadataSegments(data: Buffer): string[] {
  const found: string[] = [];
  let i = 2; // skip the start-of-image marker
  while (i + 4 <= data.length && data[i] === 0xff) {
    const marker = data[i + 1];
    const length = data.readUInt16BE(i + 2);
    if (marker === 0xda) break; // start of scan: only image data follows
    const payload = data.subarray(i + 4, i + 2 + length);
    if (marker === 0xe1 && payload.subarray(0, 5).toString("latin1") === "Exif\0") found.push("exif");
    if (marker === 0xe1 && payload.toString("latin1").startsWith("http://ns.adobe.com/xap/1.0/\0")) {
      found.push("xmp");
    }
    i += 2 + length;
  }
  return found;
}

specTest("pet-photos", LICENSED, "every file has one manifest entry and every entry its file", () => {
  const files = readdirSync(PHOTO_DIR).map((name) => `/pets/${name}`).sort();
  const entries = PET_PHOTOS.map((p) => p.file).sort();

  expect(entries).toEqual(files);
  expect(new Set(entries).size).toBe(entries.length);
});

specTest("pet-photos", LICENSED, "every photo is CC0 or public domain, from Commons", () => {
  for (const photo of PET_PHOTOS) {
    expect(["CC0", "Public domain"]).toContain(photo.license);
    expect(new URL(photo.source).hostname).toBe("commons.wikimedia.org");
    expect(photo.author.trim()).not.toBe("");
    expect(SPECIES).toContain(photo.species);
  }
});

specTest("pet-photos", LICENSED, "every species has a general photo", () => {
  for (const species of SPECIES) {
    expect(PET_PHOTOS.some((p) => p.species === species && p.breed === null)).toBe(true);
  }
});

specTest("pet-photos", NO_METADATA, "no committed photo carries EXIF or XMP", () => {
  expect(PET_PHOTOS.length).toBeGreaterThan(0);
  for (const photo of PET_PHOTOS) {
    const data = readFileSync(join(PUBLIC, photo.file));

    expect(data.subarray(0, 2)).toEqual(Buffer.from([0xff, 0xd8])); // a JPEG
    expect(metadataSegments(data), photo.file).toEqual([]);
  }
});

specTest("pet-photos", NO_METADATA, "the scan does find metadata when it is there", () => {
  const xmp = Buffer.from("http://ns.adobe.com/xap/1.0/\0<x/>", "latin1");
  const exif = Buffer.from("Exif\0\0II*\0", "latin1");
  const segment = (payload: Buffer) =>
    Buffer.concat([Buffer.from([0xff, 0xe1]), Buffer.from([0, payload.length + 2]), payload]);
  const jpeg = Buffer.concat([Buffer.from([0xff, 0xd8]), segment(exif), segment(xmp), Buffer.from([0xff, 0xda, 0, 2])]);

  expect(metadataSegments(jpeg)).toEqual(["exif", "xmp"]);
});
