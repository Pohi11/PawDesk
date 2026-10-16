# Design

## Context

- **Pillow picks a layout engine per font.** `ImageFont.truetype` uses Raqm when the library is installed and basic layout otherwise. `load_default` always uses basic layout.
- **The card uses two TrueType fonts:** Courier Prime for values and Caveat for the signature. Caveat has contextual glyph features that Raqm applies and basic layout does not.
- **Measured on Linux with and without `libraqm0`:** with Raqm, each sample card differs from its committed file only in the signature (for Pepper's card, the box from (67, 563) to (254, 595), the same box the CI runner reported). With basic layout forced, all three cards match their committed files with and without Raqm.

## Goals / Non-Goals

**Goals:** a card's pixels depend only on its request, the fonts, and the Pillow and FreeType versions, not on optional system libraries.

**Non-Goals:** better typography from Raqm. The card's text is English and needs no complex shaping.

## Decisions

### D1. Request basic layout for every TrueType font on the card
- **One argument at one place:** `_font` passes `layout_engine=ImageFont.Layout.BASIC`, so every font the card draws with is pinned.
- **The committed cards keep their bytes,** because they were drawn on machines without Raqm, which is basic layout.
- **Alternative considered:** removing Raqm from the CI runner. It would fix CI only, and any other machine with Raqm (a contributor's Linux desktop, a future image) would draw different cards.

### D2. Compare pixels by the differing region
- **`ImageChops.difference(...).getbbox()`** is None when the images match, and otherwise names the region that differs, which is the useful part of a failure.
- **Comparing `tobytes()` with `==` made a failure expensive:** pytest's assertion rewriting diffs the two byte strings, and for 2 MB of pixels that diff runs for many minutes.

## Risks / Trade-offs

- [A future Pillow changes basic layout] → The comparison test fails with the differing region. Redraw the cards and re-record, as for any card change.
