# Proposal

## Why

The requests list and the run page show each pet's photo, but the Try page, where a visitor picks a request to send, shows none. The visitor chooses between requests about pets without seeing the pets, and a freshly made-up pet stays a name until it is sent.

## What Changes

- **Each sample in the Try page's list shows its pet's photo,** or the paw placeholder when the sample's pet is not on file (the unknown-pet sample).
- **A generated request shows its pet's photo** on the "Make one up" choice and beside the preview's heading.
- **The preview's photo is the one the run page will show.** A breed in the photo set always gets its breed's photo. Other pets get a general photo chosen from the pet's id, so a generated pet's id now comes from its seed, and sending gives the new pet that id.
- **The samples list from the API includes each sample pet's id, species, and breed** when the pet is on file.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `pet-photos`: the Try page shows each request's pet photo.
- `demo-generator`: a generated pet's id comes from its seed, and samples carry their pet's photo fields.

## Impact

- **Backend:**
  - `app/demo_generator.py` (a pet id from the seed);
  - `app/demo.py` (each sample names its pet, and the pet is added with the seed's id);
  - `app/api.py` (`GET /demo/samples` looks up each sample's pet).
- **Frontend:** `components/demo-panel.tsx` uses the existing `PetAvatar`; types gain the pet fields.
- **Tests:** API tests for the sample pet fields and the seed's pet id, frontend tests for the photo chosen in the preview, and the end-to-end demo.
