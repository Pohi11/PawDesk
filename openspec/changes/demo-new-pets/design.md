# Design

## Context

- **The generator** (`app/demo_generator.py`, change `demo-generated-requests`) picks one of the eight seeded pets from the seed. Its card's scenario is checked together with that pet's records on file.
- **Intake** matches the named pet among the owner's pets, ignoring case. Two pets with the same name for one owner are ambiguous and go to a person.
- **Pet photos** (`pet-photos`) show the breed's photo when the set has one, and otherwise a stable photo of the species chosen from the pet's id.
- **The size class** is computed by Postgres from species and weight, so a new pet gets one on insert.

## Goals / Non-Goals

**Goals:** a different pet nearly every time, never one already on file or just generated, without losing reproducibility by seed.

**Non-Goals:**
- new owners (the five seeded owners stay; the request is about the pet);
- removing generated pets later (they are synthetic demo data, like the requests);
- photos for breeds outside the photo set (they get a general photo of their species).

## Decisions

### D1. The pet is invented from the seed
- **Species:** dog three times out of four, cat otherwise.
- **Name:** from a pool of 120 dog names and 60 cat names, in code. A test keeps it clear of seeded pet names and of every name in the fixed samples' messages (for example "Rex" in the unknown-pet sample, which must stay unknown).
- **Breed and weight:** a breed from a short list per species, each with a weight range, drawn to one decimal place. Breeds in the photo set are on the list, so their photos show.
- **Owner:** one of the seeded owners, ordered by name, as before.
- **Why not more seeded pets:** seeding more pets would change data that hundreds of tests and the evals rely on, and the names would still run out against existing requests.

### D2. Fresh names come from choosing the seed, not from the generator
- **`generate(session, seed)` reads only seeded data** (owners, rules, the facility), so a seed gives the same request before and after it is sent.
- **Choosing the seed:** with no seed given, `GET /demo/generate` draws random seeds and keeps the first whose name is fresh: not equal, ignoring case, to any pet on file or to a recent name. The name is computed with the same random sequence as `generate`, so checking a draw doesn't touch the database.
- **Pets on file** cover the seeded pets and every pet a sent request has added, so a name already in the request list is skipped.
- **Recent names** come from the client as `avoid` (at most 20, each at most 100 characters). The server keeps no state between requests (`demo-generated-requests` D1).
- **Running out:** after 200 draws the last draw is used. With 180 names this only happens after most of the pool is on file.
- **A seed given by the client is used as is,** so a preview link or a resend is reproducible.

### D3. Sending adds the pet
- **`store_request` takes the generated pet.** In one transaction it finds the owner's pet with that name (ignoring case) or adds it with its species, breed, and weight, then stores the request with its card.
- **Sending the same seed twice** finds the pet from the first send, so intake still finds one match.
- **No records on file:** the card is the only vaccine evidence, so every scenario holds as described. The combined check stays in the tests as the guard.

### D4. Recent names on the Try page
- **The page keeps the last 10 generated names** in session storage, so they survive opening a run view and coming back. Reading and writing are wrapped so the page works without storage.
- **Each generation sends them** as repeated `avoid` query parameters. The proxy already forwards the query string of an allowed path.

### D5. The card shows the breed
- The species cell reads "Dog, Beagle", so a reader can match the card against the request in full.

## Risks / Trade-offs

- [The demo database grows by one pet per sent request] → Pets are small rows, and the demo database is reseeded at will.
- [A visitor can send `avoid` names to steer the draw] → It only changes which random pet is shown. The list is bounded and never stored.
- [The seeded pets no longer appear in generated requests] → The fixed samples still use them, including the known edge cases on file.
