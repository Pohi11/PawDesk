# Proposal

## Why

The end-to-end test for the injection sample passes on Windows and fails on Linux CI. Pepper's vaccine card is drawn by code each time it is requested. Pillow's PNG encoder compresses with zlib-ng on Windows and with the system zlib on Linux, so the same drawing gives different bytes (45,058 vs 45,284). The recorded model responses are keyed by a hash of the request body, which carries the image, so the Linux run asks for a recording that does not exist.

## What Changes

- **Pepper's card becomes a committed PNG,** read from disk like the other samples' cards. Its bytes are the ones the existing recordings were made with, so no re-recording is needed.
- **A script draws the card** from Pepper's record, for the rare case it must change. Its output is committed, not computed at run time.
- **A test checks the committed card against a fresh drawing,** pixel for pixel, so the file can't drift from the record it shows.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `observability-api`: the injection sample's card is a committed file, served byte for byte on every platform.

## Impact

- **Backend:** `app/demo.py` (reads the file), new `app/sample_cards/pepper.png`, new `scripts/draw_pepper_card.py`.
- **Tests:** backend tests for the served bytes and the pixel match. The end-to-end injection test passes on Linux unchanged.
- **Recordings:** unchanged.
