# Design

## Context

- **A generated request** (`GET /demo/generate`) carries everything the preview's summary needs: owner, pet, breed, weight, service, dates, and `scenario_text`.
- **A sample** (`app/demo.py`) carries a title, an expected outcome, the owner's email, the pet's name, a message, and a card file. Its service and dates exist only inside the message, and its card's records only in `scripts/draw_sample_cards.py`.
- **`GET /demo/samples`** already looks up each sample's pet among its owner's pets (change `try-page-pet-photos`).

## Goals / Non-Goals

**Goals:** the preview reads the same for a sample and a generated request; the page opens on "Make one up".

**Non-Goals:** changing the samples' messages, cards, or expected outcomes.

## Decisions

### D1. The summary's facts come from where they already live
- **Owner name, breed, and weight** come from the database, through the lookup that already finds each sample's pet, so they can't drift from the seed data.
- **Service, dates, and the card summary** are new fields on `Sample`. They describe what the message asks for and what the card shows, which only the sample's author knows.
- **The card summary is written by hand,** in the generator's wording ("Every vaccine on the card is current for the whole stay."; "Bordetella expired on Nov 14, 2026, before the stay."). Deriving it from the card's records would mean moving those records out of the drawing script for one sentence per sample.
- **The unknown-pet sample** now names its pet (Rex) instead of `None`, so its heading has a name. The lookup still finds no Rex on file, so it has no breed, weight, or card, and its summary says so.

### D2. One summary block for both kinds of request
- **The panel builds a summary** (pet fields, heading, detail line) from either a generated request or a sample, and renders one block. The two can't drift apart in layout.

### D3. Open on "Make one up" and generate at once
- **Selecting it without a request** would show an empty preview, so the panel generates one on mount.
- **React's development mode mounts effects twice,** which would generate two requests and use up two names. A ref guards the first call.
- **Trade-off:** each visit to the page costs one generation call. It uses no model, only seeded randomness and a database read.

## Risks / Trade-offs

- [A hand-written card summary can disagree with its card] → The cards change only through the drawing script, which says to check the samples when a card changes; the summary sits next to the card file name in `Sample`.
