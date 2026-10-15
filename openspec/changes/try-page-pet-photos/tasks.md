# Tasks

## 1. API

- [ ] 1.1 Derive a generated pet's id from its seed and insert the pet with it on send, and add each sample's pet fields to `GET /demo/samples`. Verify with tests: the same pet id across previews and after sending, and Biscuit's fields for the clean sample with none for the unknown-pet sample.

## 2. Dashboard

- [ ] 2.1 Show `PetAvatar` on each choice in the Try page's list and beside the preview's heading. Verify with a frontend test that a generated preview and its sent pet get the same photo, an end-to-end check of the Beagle photo on the clean sample, then lint, type check, and build.
- [ ] 2.2 Try it in a browser: check the samples' photos, generate a pet whose breed is outside the set, send it, and compare the photos. Verify with screenshots.

## 3. Integration

- [ ] 3.1 Run every suite and the coverage check, then regenerate the walkthrough.
