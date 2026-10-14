import manifest from "./pet-photos.json";
import type { PetFields } from "./types";

/** One committed photo, as written by backend/scripts/fetch_pet_photos.py. */
export interface PetPhoto {
  file: string;
  species: string;
  /** null for a general photo of the species. */
  breed: string | null;
  source: string;
  author: string;
  license: string;
}

export const PET_PHOTOS: readonly PetPhoto[] = manifest;

const sameBreed = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

/** 32-bit FNV-1a: a small, stable hash, so the same id gives the same answer everywhere. */
export function fnv1a(text: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash;
}

/**
 * The photo for a request's pet: its breed's photo if the set has one, else a general photo
 * of its species picked from the pet id. null when no pet is matched (show the placeholder).
 * Never random: the server render, the browser, and every live refresh must agree.
 */
export function petPhoto(
  pet: Pick<PetFields, "pet_id" | "pet_species" | "pet_breed">,
  photos: readonly PetPhoto[] = PET_PHOTOS,
): PetPhoto | null {
  const { pet_id: id, pet_species: species, pet_breed: breed } = pet;
  if (id === null || species === null) return null;
  const own = photos.filter((p) => p.species === species);
  const byBreed = breed && own.find((p) => p.breed !== null && sameBreed(p.breed, breed));
  if (byBreed) return byBreed;
  const general = own.filter((p) => p.breed === null);
  return general.length > 0 ? general[fnv1a(id) % general.length] : null;
}
