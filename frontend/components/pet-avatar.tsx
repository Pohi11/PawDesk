import Image from "next/image";

import { petPhoto } from "@/lib/pet-photo";
import type { PetFields } from "@/lib/types";

const SIZES = { sm: 44, lg: 88 } as const;

/**
 * The pet's photo, or a paw placeholder while no pet is matched. The photos are stock
 * illustrations of the breed (lib/pet-photos.json), not pictures of the pet itself.
 */
export function PetAvatar({ pet, size = "sm" }: { pet: PetFields; size?: keyof typeof SIZES }) {
  const px = SIZES[size];
  const photo = petPhoto(pet);
  const frame = "shrink-0 overflow-hidden rounded-full ring-1 ring-rule";

  if (photo === null || pet.pet === null) {
    return (
      <span
        role="img"
        aria-label="No pet matched yet"
        className={`${frame} inline-flex items-center justify-center bg-wash text-faint`}
        style={{ width: px, height: px }}
      >
        <PawIcon size={Math.round(px * 0.5)} />
      </span>
    );
  }
  return (
    <Image
      src={photo.file}
      alt={`Photo for ${pet.pet}`}
      width={px}
      height={px}
      // The files are already 320 px squares, so the optimizer has nothing to add.
      unoptimized
      className={`${frame} bg-wash object-cover`}
    />
  );
}

function PawIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <ellipse cx="6" cy="9" rx="2.2" ry="2.8" />
      <ellipse cx="10" cy="5.5" rx="2.2" ry="2.8" />
      <ellipse cx="14" cy="5.5" rx="2.2" ry="2.8" />
      <ellipse cx="18" cy="9" rx="2.2" ry="2.8" />
      <path d="M12 11.5c-3.2 0-6 3.3-6 6.1 0 1.8 1.3 2.9 3 2.9 1.2 0 2-.6 3-.6s1.8.6 3 .6c1.7 0 3-1.1 3-2.9 0-2.8-2.8-6.1-6-6.1z" />
    </svg>
  );
}
