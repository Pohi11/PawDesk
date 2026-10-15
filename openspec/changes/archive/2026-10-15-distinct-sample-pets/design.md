# Design

## Context

- Samples are fixed requests from seeded owners about seeded pets. The clean and injection samples both use Biscuit and the benchmark image `cert-28.png`.
- The records check compares the pet name printed on the card with the pet being booked, so a sample about a new pet needs a card that prints that pet's name.
- `app/certificate_card.py` already draws a generated request's card with Pillow, with no browser.

## Goals / Non-Goals

**Goals:** each sample shows a different pet photo; the injection sample still fails for one reason only, the planted instruction.

**Non-Goals:** new seeded pets, new photos, or changes to the benchmark images.

## Decisions

### D1. Pepper, from the seed data
- **Pepper** is already on file (Priya Venkataraman, Chihuahua, 6 lb). Her breed has its own photo, which differs from the Beagle, the Labrador, and the placeholder the other samples show.
- **Options considered:** Juniper (Bernese Mountain Dog) also has a photo, but a 98 lb dog adds a kennel-size question to a sample about something else. Waffles has a benchmark card, but it is not compliant.
- **Decision:** Pepper.

### D2. The card is drawn when requested, not committed
- **No committed benchmark card** names Pepper with current records, and adding one would change the pinned benchmark.
- **Decision:** the sample holds a small spec (clinic, vet, dates) and `sample_certificate` draws it with `certificate_card.render`. The same sample always gives the same bytes.
- **Import:** `certificate_card` imports `demo_generator`, which imports `demo`, so `demo` imports the renderer inside the function.
- **Dates:** every vaccine boarding needs for a dog is current through the stay (March 24 to 27, 2027) with today as March 3, 2027.
