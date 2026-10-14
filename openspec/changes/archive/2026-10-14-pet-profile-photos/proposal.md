# Proposal

## Why

The requests list and the run page identify a request by the pet's name in text. A photo makes each row recognizable at a glance and makes the demo read as a pet care desk rather than a log viewer. The photo belongs to the pet, so the same pet looks the same on every request, and it has to match what the pet is: a Beagle shows a Beagle, a cat never shows a dog.

## What Changes

- The request list and request detail report the matched pet's id, species, and breed alongside its name.
- The dashboard picks a photo for each matched pet: a photo of its breed when the set has one, otherwise a stable photo of its species chosen from the pet's id.
- A request with no matched pet (before intake, or a pet not on file) shows a neutral placeholder, never a photo.
- The photo appears as an avatar on each row of the requests list and beside the pet's name on the run page. On a live run, it appears as soon as intake matches the pet.
- A small set of dog and cat photos is committed with the dashboard. Every photo comes from Wikimedia Commons under CC0 or a public-domain dedication, is recorded in a manifest with its source, author, and license, and is re-encoded without embedded metadata.

## Capabilities

### New Capabilities

- `pet-photos`: how the dashboard chooses and shows a photo for a pet, and the licensing and metadata rules for the committed photo set.

### Modified Capabilities

- `observability-api`: requests identify the matched pet by id, species, and breed in the list and the detail.

## Impact

- **Backend:** `app/observability.py` (`list_requests`, `request_detail`) adds three fields. No schema change, no migration.
- **Frontend:** a photo manifest and selection function in `lib/`, an avatar component, the requests list (`app/page.tsx`), the run view header (`components/run-view.tsx`), and `lib/types.ts`. Photos live under `public/pets/` and are served as static files, so the proxy allowlist does not change.
- **Assets:** about 13 small JPEGs (under 0.5 MB in total) downloaded once from upload.wikimedia.org.
- **Tests:** backend API tests for the new fields; frontend unit tests for selection and the manifest; the end-to-end demo checks the photo on both pages.
