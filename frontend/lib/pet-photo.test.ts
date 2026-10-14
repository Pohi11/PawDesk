import { expect } from "vitest";

import { specTest } from "../tests/spec";
import { fnv1a, petPhoto, type PetPhoto } from "./pet-photo";

const BREED = "A matched pet shows a photo of its breed";
const STABLE = "Other pets show a stable photo of their species";
const PLACEHOLDER = "A request without a matched pet shows a placeholder";

const photo = (file: string, species: string, breed: string | null): PetPhoto => ({
  file,
  species,
  breed,
  source: `https://commons.wikimedia.org/wiki/File:${file}`,
  author: "Test",
  license: "CC0",
});
const SET = [
  photo("/pets/beagle.jpg", "dog", "Beagle"),
  photo("/pets/ragdoll.jpg", "cat", "Ragdoll"),
  photo("/pets/dog-1.jpg", "dog", null),
  photo("/pets/dog-2.jpg", "dog", null),
  photo("/pets/dog-3.jpg", "dog", null),
  photo("/pets/cat-1.jpg", "cat", null),
  photo("/pets/cat-2.jpg", "cat", null),
];
const ID = "01a13bf4-9a05-7bc6-a5b0-497142252250";
const pet = (species: string, breed: string | null, id = ID) => ({
  pet_id: id,
  pet_species: species,
  pet_breed: breed,
});

specTest("pet-photos", BREED, "a Beagle gets the Beagle photo", () => {
  expect(petPhoto(pet("dog", "Beagle"), SET)?.file).toBe("/pets/beagle.jpg");
});

specTest("pet-photos", BREED, "breed matching ignores case and surrounding spaces", () => {
  expect(petPhoto(pet("dog", " beagle "), SET)?.file).toBe("/pets/beagle.jpg");
});

specTest("pet-photos", BREED, "a cat never gets a dog's breed photo", () => {
  const chosen = petPhoto(pet("cat", "Beagle"), SET);

  expect(chosen?.species).toBe("cat");
  expect(chosen?.breed).toBeNull();
});

specTest("pet-photos", STABLE, "a breed without a photo gets a general photo of the species", () => {
  const chosen = petPhoto(pet("dog", "Shiba Inu"), SET);

  expect(chosen?.species).toBe("dog");
  expect(chosen?.breed).toBeNull();
});

specTest("pet-photos", STABLE, "a pet with no breed gets a general photo", () => {
  expect(petPhoto(pet("cat", null), SET)?.file).toMatch(/^\/pets\/cat-\d\.jpg$/);
});

specTest("pet-photos", STABLE, "the same pet gets the same photo every time", () => {
  const first = petPhoto(pet("dog", "Shiba Inu"), SET);

  for (let i = 0; i < 5; i++) expect(petPhoto(pet("dog", "Shiba Inu"), SET)).toBe(first);
  expect(petPhoto(pet("dog", null), SET)).toBe(first); // the pick depends on the id alone
});

specTest("pet-photos", STABLE, "different pets spread across the general photos", () => {
  const files = new Set(
    Array.from({ length: 30 }, (_, i) => petPhoto(pet("dog", null, `pet-${i}`), SET)?.file),
  );

  expect(files.size).toBe(3);
});

specTest("pet-photos", PLACEHOLDER, "no matched pet means no photo", () => {
  expect(petPhoto({ pet_id: null, pet_species: null, pet_breed: null }, SET)).toBeNull();
});

specTest("pet-photos", STABLE, "the hash is the published FNV-1a", () => {
  // Reference values for 32-bit FNV-1a.
  expect(fnv1a("")).toBe(0x811c9dc5);
  expect(fnv1a("a")).toBe(0xe40c292c);
  expect(fnv1a("foobar")).toBe(0xbf9cf968);
});
