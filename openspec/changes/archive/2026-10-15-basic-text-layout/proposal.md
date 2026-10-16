# Proposal

## Why

The backend test job on GitHub Actions hangs in the test that compares each committed sample card with a fresh drawing. The runner has the Raqm text-shaping library installed, and Pillow uses it for any TrueType font when it is present. Raqm shapes the Caveat signature differently from Pillow's basic layout, so the drawn signature moves by a few pixels. Development machines and the test container have no Raqm, which is why the cards matched there. The failing assertion compares two 2 MB byte strings, and pytest's diff of them runs for longer than the job is worth watching.

## What Changes

- **Cards always use Pillow's basic text layout,** so a card draws the same pixels with or without Raqm. The committed cards were drawn with basic layout, so they and the recorded responses stay valid.
- **The pixel comparison fails fast,** reporting the region that differs instead of diffing the raw pixel bytes.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `demo-generator`: card drawing does not depend on which text-shaping libraries the machine has.

## Impact

- **Backend:** `app/certificate_card.py`.
- **Tests:** a test that the card's fonts use basic layout; the committed-card comparison reports the differing region.
- **Committed cards and recordings:** unchanged.
