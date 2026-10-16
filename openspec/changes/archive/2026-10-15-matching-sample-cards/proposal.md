# Proposal

## Why

The three Try page samples with a vaccine card use two styles. Pepper's card (injection sample) is drawn by the demo card template; Biscuit's (clean) and Moose's (expired vaccine) are certificate benchmark images in other layouts. Biscuit's benchmark card also prints Moose's owner, J. Whitfield, as the owner.

## What Changes

- **Biscuit's and Moose's cards are drawn by the same template as Pepper's,** from each pet's own name, owner, breed, clinic, and the same vaccine records the benchmark cards printed, so each sample still ends the same way.
- **Both are committed PNGs next to Pepper's,** served as stored, like Pepper's.
- **One script draws all three cards.** Pepper's bytes do not change.
- **The end-to-end recordings for the clean and expired samples are recorded again,** since the model now reads different images.
- **The benchmark images stay as they are:** the records eval and the architecture comparison still read them.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `observability-api`: every sample's card is drawn in the demo card style from its own pet's record.

## Impact

- **Backend:** `app/demo.py`, `app/sample_cards/`, `scripts/draw_sample_cards.py` (replaces `scripts/draw_pepper_card.py`).
- **Frontend:** the home page example's image size matches the new card.
- **Tests:** the card tests cover all three samples; new end-to-end recordings.
