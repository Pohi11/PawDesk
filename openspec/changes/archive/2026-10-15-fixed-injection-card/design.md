# Design

## Context

- **Recordings are keyed by the exact request body** (decision record 0016). The records step sends the certificate as base64 inside that body, unchanged, so any byte difference in the image is a replay miss.
- **The other samples' cards are committed files** from the certificate benchmark. Pepper's was drawn at run time by `app/certificate_card.py` because no benchmark image names her with current records.
- **Drawing is deterministic on one machine, not across machines.** Same Pillow 12.3.0 and FreeType 2.14.3 on Windows and Linux, but the Windows wheel bundles zlib-ng and the Linux one uses zlib 1.2.13. The pixels agree; the compressed bytes do not.

## Goals / Non-Goals

**Goals:** every input the end-to-end samples send to the model is the same bytes on every platform, without re-recording.

**Non-Goals:** making `certificate_card.render` itself byte-stable across platforms. Generated ("Make one up") cards are never replayed from recordings: their seed is random, and no end-to-end test sends one through the model.

## Decisions

### D1. Commit the card instead of drawing it at run time
- **The served bytes are whatever is on disk,** so they can't depend on the platform's compressor.
- **The committed file is the Windows drawing** (sha256 `77450e23…`), the bytes the current recordings were made with, so the recordings stay valid.
- **Alternatives considered:** saving the PNG uncompressed (level 0) would be byte-stable, but changes the bytes and so needs a re-record, and makes a ~2 MB image; normalizing through a fixed compressor adds a dependency for one file.

### D2. Kept under `app/sample_cards/`, not the benchmark folder
- **The benchmark's images are listed in its `truth.json`** and counted by its tests. Pepper's card is demo data, so it lives with the app code that serves it.

### D3. A script draws it; a test ties the file to the record
- **`scripts/draw_pepper_card.py`** holds Pepper's record and writes the PNG. It is run by hand only when the card must change, and then the recordings are re-made.
- **A test compares decoded pixels,** not bytes, between the committed file and a fresh drawing. Pixels are the same on both platforms, so the test passes in CI and still fails if someone edits the record without redrawing the card.

## Risks / Trade-offs

- [A Pillow or FreeType upgrade changes how text is drawn] → The pixel test fails and names the card. Redraw it and re-record, or pin the version. The served card and the end-to-end test are unaffected until then.
