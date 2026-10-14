# Design

## Context

A request is matched to a pet by the intake step, which sets `booking_requests.pet_id`. Until then, and for a pet not on file, the request has no pet. The list (`list_requests`) and detail (`request_detail`) already join the pet but return only its name. The run page re-fetches the full detail on every live snapshot, so anything added to the detail updates during a run without new streaming fields.

The seed data has six dogs (Beagle, Bernese Mountain Dog, Chihuahua, Labrador Retriever, Border Collie, Pembroke Welsh Corgi) and two cats (Domestic Shorthair, Ragdoll). `Species` has two values, `dog` and `cat`.

The dashboard and the backend ship as separate images, and the browser reaches the backend only through the allowlisted proxy (see the run-dashboard spec).

## Goals / Non-Goals

**Goals:**

- One photo per pet, the same everywhere, matching species and breed.
- A photo set that can be published in a public repository without license or privacy doubts, checked by tests rather than by trust.
- No new runtime dependency on an outside service.

**Non-Goals:**

- Uploading or storing real photos per pet. The photos are illustrations, not records of the pets.
- Photos on the review queue, metrics, or demo pages. They can reuse the same component later.
- A photo for every breed. Breeds without one use a general photo of the species.

## Decisions

### D1. The photo belongs to the pet, not the request

The picture answers "which animal is this about", so two requests for Biscuit show the same dog. Choosing per request would show different dogs for the same pet and could show a dog for a cat. The cost is that a request has no photo until intake matches its pet; the placeholder covers that window (D5).

### D2. A vendored set from Wikimedia Commons, limited to CC0 and public domain

Alternatives considered:

- **A live random-dog API (dog.ceo).** No files to commit, but the browser would contact a third party on every page, the picture would change on each load, CI and the end-to-end demo would depend on the network, and the images come from the Stanford Dogs dataset, built on ImageNet, whose terms target non-commercial research.
- **Generated images.** Fully synthetic, but each image costs an API call and breed accuracy has to be checked by eye.
- **Commons photos under CC BY or CC BY-SA.** Many more choices, but each would need visible attribution wherever it is shown.

Commons returns each file's license and author through its API, so the choice can be recorded precisely. Limiting the set to CC0 and public-domain dedications means no attribution duty, while the manifest still records the source and author. Photos showing a person, a license plate, or a home exterior are skipped when choosing.

### D3. The backend reports facts, the dashboard chooses the photo

The API adds the pet's id, species, and breed. A pure function in the dashboard maps those to a photo path from a JSON manifest, and the files are served by Next.js from `public/pets/`.

Alternatives considered:

- **The backend serves the photo** (`GET /pets/{id}/photo`). The backend image would carry dashboard assets, every photo would pass through the proxy, and the allowlist would grow.
- **The backend returns a photo path.** The backend would have to know the dashboard's file layout, and the two images would have to stay in sync.

The three new fields are facts the API already holds, and useful beyond photos. How a pet looks on screen is a presentation choice, so it lives where the screen is built.

### D4. Breed match first, then a stable pick from the pet's id

Breeds match case-insensitively after trimming, within the pet's species. Otherwise the function hashes the pet id (FNV-1a over the id string) to pick one of that species' general photos. It never uses `Math.random()`: a random pick would differ between the server render and the browser, and on every snapshot refresh during a live run.

A reseed creates new pet ids, so a pet without a breed photo may get a different general photo after reseeding. Every seeded pet has a breed photo, so the demo is unaffected.

### D5. The placeholder is an inline paw icon, not a photo file

A request with no matched pet is a different state from a pet with a photo, and the screen should show that difference. An inline SVG with accessible text ("No pet matched yet") needs no file and cannot be mistaken for an animal.

### D6. A committed fetch script produces the set

`backend/scripts/fetch_pet_photos.py` takes a short, hand-picked list of Commons file titles with their species and breed. For each, it reads the license and author from the Commons API, refuses anything that is not CC0 or public domain, downloads the 640 px thumbnail, center-crops it to 320 × 320, re-encodes it as JPEG with no EXIF or XMP, and writes the files and `frontend/lib/pet-photos.json`. The set can then be rebuilt or extended the same way, and reviewers can see where every file came from. The downloads run once at apply time; the script is not part of CI.

320 px covers the largest display (96 px on the run page) at three times pixel density. Each file is about 20–30 KB.

### D7. Tests check the set itself

A vitest suite compares the folder with the manifest, checks each license and source host, checks that each species has a general photo, and scans each JPEG for an APP1 segment carrying EXIF or XMP. The selection function gets unit tests for each pet-photos scenario. The end-to-end demo checks the photo on the run page and the list, which also covers the live swap from placeholder to photo.

Photos render with `next/image` and `unoptimized`, because the files are already sized and the optimizer would add work in the standalone image for no gain.

## Risks / Trade-offs

- [A Commons license tag is wrong or later changed] → The manifest stores the source page URL and the license read at download time, so any file can be rechecked and replaced.
- [A seeded breed has no CC0 or public-domain photo] → That pet falls back to a general photo of its species (D4), which the spec allows. The gap is recorded in the manifest.
- [Merge conflicts with in-flight branches that edit the requests list and run view copy] → This change touches layout, not wording, and adds no API routes. Conflicts are expected to be small and are resolved at merge.
- [The end-to-end demo frames change] → The README GIF is regenerated from the new frames in the integration task.
- [Real photos in a synthetic-data project] → The pets, owners, and records stay synthetic. The photos are stock illustrations of a breed and are not tied to any real animal's identity.
