# Design

## Context

- **Demo samples** (`app/demo.py`) are fixed requests on seeded owners, processed as of `DEMO_TODAY` (2027-03-03), with benchmark certificates attached from `evals/certificates/v2/images/`.
- **Vaccine rules** per service and species are seeded in the database (`vaccine_rules`).
- **The benchmark certificates** are rendered with Playwright and Chromium (dev only, offline). The API can't depend on a browser.
- **The records step** reads any PNG, JPEG, or WebP of at most 5 MB.

## Goals / Non-Goals

**Goals:** a believable, varied request with a card that a person can check against it; reproducible by seed; no new infrastructure.

**Non-Goals:**
- handwriting, blur, or rotation (the benchmark covers reading hard images);
- storing generated requests before they're sent;
- predicting the whole outcome (capacity, intake, and the records model still decide the run).

## Decisions

### D1. Reproducible from a seed, stateless
- `generate(session, seed)` uses `random.Random(seed)` and the seeded database. It reads owners with their pets in name order, and each (service, species) rule set.
- **The API never stores a draft.** The preview, the image, and the send each regenerate from the seed, so nothing is kept between viewing and sending.
- The seed comes from the client (`GET /demo/generate?seed=` takes an optional seed, and the server picks one if it's missing) and is echoed back.

### D2. Request
- **Pet:** a uniformly random seeded pet.
- **Service:** chosen among services with rules for its species. Boarding is weighted most likely.
- **Stay:** the start is the demo day plus 5 to 40 days. Boarding lasts 2 to 6 nights; daycare and grooming take one day.
- **Message:** chosen from a small set of templates per service, filled with the pet's name and the dates as people write them ("March 12 to March 15"), plus an optional care note. No model writes it, so it stays reproducible and free.

### D3. Scenario and card
- **Scenarios** are chosen with weights: `current` 40%, `expired` 20%, `expires_during_stay` 20% (boarding of 2 nights or more only, otherwise `expired`), and `missing` 20%.
- **Records** cover every required vaccine:
  - given 60 to 330 days before the start;
  - valid for 1 year, or 3 years for some rabies records;
  - always expiring at least 30 days after checkout;
  - dogs sometimes also get one vaccine that isn't required, as real cards do.
- **The scenario changes one required vaccine,** chosen only among vaccines where the real check (`vaccine_status`) over the pet's records on file plus the changed record gives the scenario's status. A current record on file would otherwise cover an expired one on the card, and the scenario would say one thing while the desk concluded another (found in the first real try-out). When no required vaccine qualifies, the pet, service, and stay are drawn again, up to 30 times, and then the scenario becomes `current`, which always holds because the card covers every vaccine.
- **The changes:**
  - `expired`: expires 5 to 60 days before the start;
  - `expires_during_stay`: expires on a day from the start up to the day before checkout;
  - `missing`: removed from the card, and only for a vaccine with no record on file.
- **The plain description** names the changed vaccine and its date, e.g. "Bordetella expired on Mar 1, 2027, before the stay."
- **Clinic and vet** are drawn from fictional lists.

### D4. Drawing the card (`app/certificate_card.py`)
- **Pillow, 1000×680 PNG,** drawn by code:
  - the clinic header;
  - "Certificate of Vaccination";
  - patient, species, and owner;
  - a table of vaccine, date given, and expires;
  - the vet's signature in the bundled handwriting font (`Caveat.ttf`), with values in the bundled typewriter face.
- **The footer** reads "PawDesk demo certificate. Not a real record.", marking it as synthetic as the benchmark's images are.
- **Deterministic:** the same request always gives the same bytes (no timestamps or randomness at draw time). Pillow becomes a runtime dependency.

### D5. API
| Route | What it does |
|---|---|
| `GET /demo/generate?seed=` | `{seed, owner, pet, species, service, start_date, end_date, message, scenario, scenario_text, records}` |
| `GET /demo/generated/{seed}/certificate.png` | the PNG |
| `GET /demo/samples/{id}/certificate.png` | a fixed sample's card, or 404 |
| `POST /demo/requests` | takes `{sample}` or `{seed}`, plus an optional `message` |

A generated request is stored like a sample (owner, message, the card attached) and processed in the background as of the demo day.

### D6. Dashboard
- **The Try page lists** "Generate a request" first, then the fixed samples.
- **Generating** fetches `/api/demo/generate` and shows the message (editable), the scenario sentence, the card image, and a "Generate another" button.
- **Fixed samples** show their card image when they have one.
- **The proxy allowlist** adds `GET demo/generate`, `GET demo/generated/<digits>/certificate.png`, and `GET demo/samples/<id>/certificate.png`.

## Risks / Trade-offs

- [The records model may note the "not a real record" footer as doubt, which sends the request to review] → It's honest behavior, and it has been measured before (benchmark watermark). It's acceptable for a demo, and visible in the run's reasons.
- [Records on file decide which pets can show a failing scenario] → With the seeded records, failing scenarios fall on the dogs whose records on file leave a gap, and cats always get `current`. Variety across pets is lower for failing scenarios, but the scenario never contradicts the check.
