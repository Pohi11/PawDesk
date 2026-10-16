# Design

## Context

- **Pepper's card is drawn by `app/certificate_card.py`** (the demo card template, also used for generated requests) and committed as `app/sample_cards/pepper.png`. It is committed because PNG bytes differ by platform and the recorded model responses are keyed by them (change fixed-injection-card).
- **Biscuit's and Moose's cards are `cert-28.png` and `cert-25.png`** from the certificate benchmark (`evals/certificates/v2`). The records eval and the architecture comparison (`evals/comparison_cases.json`) also read these files.

## Goals / Non-Goals

**Goals:** all three sample cards look like one clinic system made them, each prints its own pet and owner, and every sample ends the way it did before.

**Non-Goals:** changing the benchmark, the card template, or the samples' messages.

## Decisions

### D1. New files, benchmark untouched
- **Biscuit's and Moose's cards become `app/sample_cards/biscuit.png` and `moose.png`.** Redrawing `cert-28.png` and `cert-25.png` would change the records eval's inputs and invalidate its measured results.

### D2. Same facts, correct owner
- **Each card keeps the benchmark card's clinic, vet, and vaccine records** (labels, dates given, expiry dates). So Biscuit's four shots still cover March 24 to 27, Moose's Bordetella still expired on November 14, 2026, and the home page's description of Biscuit's card stays true.
- **The owner is the pet's real owner on file,** printed like Pepper's ("A. Lindqvist", "J. Whitfield"). Biscuit's benchmark card printed J. Whitfield, Moose's owner.
- **Breed comes from the seed** (Beagle, Labrador Retriever).

### D3. One script for all three cards
- **`scripts/draw_sample_cards.py` replaces `draw_pepper_card.py`** and holds each card's record. Tests import the records from it, so the pixel check covers all three.
- **Pepper's committed bytes stay as they are,** so its recording stays valid. The script redraws all three, and the check after a run is that `pepper.png` shows no diff.

### D4. Record the two changed samples again
- **The clean and expired samples now send different images,** so their recorded records responses no longer match. They are recorded again with `PAWDESK_E2E_RECORD=1` (real model calls, a fraction of a cent), and the end-to-end tests confirm each sample still ends where it did: the clean one sent, the expired one held for staff with the resolver's offer.

## Risks / Trade-offs

- [The records model reads the new cards differently, for example flags something as unclear] → The end-to-end tests assert each sample's outcome; a changed outcome fails them, and the recording is not kept.
