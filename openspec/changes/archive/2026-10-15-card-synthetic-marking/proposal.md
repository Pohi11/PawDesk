# Proposal

## Why

Every demo vaccine card, generated or fixed, prints "PawDesk demo certificate. Not a real record." along its bottom edge. The records model reads the whole card, so it reports that line as an ambiguity ("certificate footer states it is a PawDesk demo certificate, not a real record"), and any ambiguity sends the request to a person. The clean boarding sample, which should pass with no person involved, gets routed to review on some runs, and a recorded end-to-end response already carries the same ambiguity.

Flagging a card that says it isn't real is the right behavior for the records step, so the fix belongs on the card, not in the prompt.

## What Changes

- **Demo cards no longer print the footer.** Nothing drawn on a demo card says it is not a real record.
- **The synthetic marking moves into the image's metadata.** Every demo card carries a PNG text chunk saying it is a synthetic PawDesk demo certificate with fictional names.
- **The three sample cards are redrawn** and their end-to-end model responses recorded again.

The certificate benchmark's watermark ("SYNTHETIC TEST DOCUMENT") is unchanged: the records eval measures reading those images as they are.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `demo-generator`: demo cards carry their synthetic marking in metadata, not on the card.

## Impact

- **Backend:** `app/certificate_card.py` (no footer; PNG text chunk), `app/sample_cards/*.png` (redrawn).
- **Tests:** a card test for the blank footer area and the metadata; re-recorded end-to-end responses for the requests whose card changed.
