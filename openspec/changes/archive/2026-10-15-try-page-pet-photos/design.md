# Design

## Context

- **`petPhoto`** (`lib/pet-photo.ts`, capability `pet-photos`) returns the breed's photo when the set has one, and otherwise a general photo of the species picked by hashing the pet's id. With no pet id it returns null, and `PetAvatar` shows the paw placeholder.
- **Samples** are fixed requests from seeded owners about seeded pets (Biscuit, Moose), except the unknown-pet sample (Rex, not on file). They don't name their pet in data; only the message does.
- **Generated pets** (change `demo-new-pets`) exist only as a seed until the request is sent. The pet row gets a Postgres `uuidv7()` id on insert.

## Goals / Non-Goals

**Goals:** the Try page shows the same photo a pet will have on the run page, for samples and generated requests.

**Non-Goals:**
- new photos or breeds in the set;
- photos on the certificate card.

## Decisions

### D1. Reuse `PetAvatar` and `petPhoto` unchanged
- **The Try page passes the same fields** (`pet`, `pet_id`, `pet_species`, `pet_breed`) that the requests list and run page pass, so the rules live in one place.
- **Sizes:** the small avatar on each choice in the list, the large one beside the preview's heading.

### D2. A generated pet's id comes from its seed
- **Without an id the preview can't pick** the general photo the run page will pick, so a breed outside the set would show one photo in the preview and another after sending.
- **Options considered:**
  - hash the pet's name instead of its id for general photos (changes `pet-photos` and moves every seeded pet's photo);
  - pick the preview's photo from the seed and accept a different one after sending;
  - derive the pet's id from the seed and insert the pet with it.
- **Decision:** `uuid5(namespace, "pawdesk-demo-pet:<seed>")`. The preview carries it as `pet_id`, and `store_request` inserts the new pet with that id. Every other pet keeps its `uuidv7()` id.
- **Trade-off:** these ids aren't time-ordered like `uuidv7()`, so inserts land anywhere in the primary key index. Demo pets are few, so it doesn't matter.
- **Edge case:** if the owner already has a pet with the generated name (only once the name pool is nearly used up), sending reuses that pet, and its photo may differ from the preview.

### D3. Samples name their pet
- **Each `Sample` gets a `pet` name** (`None` for the unknown-pet sample).
- **`GET /demo/samples` looks up** that name among the owner's pets, ignoring case as intake does, and adds `pet_id`, `pet_species`, and `pet_breed` (all null when not on file).

## Risks / Trade-offs

- [`GET /demo/samples` now reads the database] → Four small lookups, on a page that already waits for the API.
