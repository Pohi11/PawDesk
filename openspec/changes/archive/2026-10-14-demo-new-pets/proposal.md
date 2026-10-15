# Proposal

## Why

The Try page's generated requests draw their pet from the eight seeded pets, so the same names keep coming back: generate a few requests and Biscuit or Moose shows up again, often a name that already has a request in the list. A demo that is meant to show the desk handling requests it was never tuned on keeps showing it the same few pets.

## What Changes

- **A generated request brings a new pet:**
  - a seeded owner, as before;
  - a pet invented for that owner: a name from a pool of over 100 dog names and 50 cat names, a breed, and a weight that fits the breed.
- **Sending adds the pet to its owner** before the request is stored, so intake matches it like any pet on file. Sending the same seed again reuses that pet.
- **Fresh names.** When the server picks the seed, it skips any draw whose pet name is already on file (which covers every earlier request's pet) or was generated recently in this browser.
- **The Try page remembers recent names.** It sends the last 10 names it generated in this browser session with each new generation.
- **Still reproducible:** a seed alone still fixes the request, so the preview, the card, and the send stay the same.
- **Simpler scenarios.** A new pet has no vaccine records on file, so the card is the only evidence and every scenario holds as described.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `demo-generator`: generated requests invent a new pet with a fresh name, and sending adds it to its owner.
- `run-dashboard`: the Try page sends its recently generated names when it asks for a new request.

## Impact

- **Backend:**
  - `app/demo_generator.py` (name pool, breeds, choosing a fresh seed);
  - `app/demo.py` (adding the pet on send);
  - `app/api.py` (`avoid` names on `GET /demo/generate`);
  - the card shows the breed.
- **Frontend:** the Try page keeps recent names in session storage and sends them.
- **Data:** each sent generated request adds one pet to the demo database. Seeded data is unchanged.
- **Tests:** the pool, fresh names, reproducibility, adding the pet on send, and the Try page's request.
