# Tasks

## 1. API

- [ ] 1.1 Add `pet_id`, `pet_species`, and `pet_breed` to `list_requests` and `request_detail` (null when no pet is matched), and to `RequestRow` and `RequestDetail` in `frontend/lib/types.ts`. Verify with API tests tagged `observability-api` / "Requests identify the matched pet" for a matched and an unmatched request, plus the existing API suite and the frontend type check.

## 2. Photo set

- [ ] 2.1 Add `backend/scripts/fetch_pet_photos.py` (hand-picked Commons titles; license check; 640 px thumbnail, 320 × 320 center crop, JPEG without EXIF or XMP; writes `frontend/public/pets/` and `frontend/lib/pet-photos.json`). Unit-test its license filter and crop on a local image with fake metadata, with no network. Verify with `pytest tests/test_fetch_pet_photos.py`.
- [ ] 2.2 Choose the titles (one per seeded breed where a CC0 or public-domain photo exists, plus general photos for each species), confirm the file list, source, and total size before downloading, then run the script once. Verify with the manifest tests (2.3) and by looking at every photo.
- [ ] 2.3 Add `frontend/tests/pet-photos-manifest.test.ts` for "Every committed photo is licensed for reuse and recorded" and "Committed photos carry no embedded metadata". Verify with `pnpm test`.

## 3. Dashboard

- [ ] 3.1 Add `frontend/lib/pet-photo.ts` (breed match within species, else an FNV-1a pick from the pet id, else none) with unit tests for every scenario of "A matched pet shows a photo of its breed" and "Other pets show a stable photo of their species". Verify with `pnpm test`.
- [ ] 3.2 Add a `PetAvatar` component (photo with alternative text naming the pet, or the inline paw placeholder) and use it on the requests list rows and the run page heading. Verify with lint, type check, build, and a screenshot of both pages with a matched and an unmatched request.
- [ ] 3.3 Extend the end-to-end demo with checks tagged `pet-photos` / "Photos appear on the requests list and the run page" and "A request without a matched pet shows a placeholder": Biscuit's Beagle photo on the run page and on the list, and the placeholder for the unknown-pet sample. Verify with `pnpm e2e`.

## 4. Integration

- [ ] 4.1 Run every suite and the traceability check, regenerate the README demo GIF from the new frames, and regenerate the build walkthrough. Verify with `pytest`, `pnpm test`, `pnpm e2e`, and `uv run python -m scripts.walkthrough --check`.

## Workflow follow-up

- Archive the change once every task is done, then merge `pet-profile-photos` into `main`.
