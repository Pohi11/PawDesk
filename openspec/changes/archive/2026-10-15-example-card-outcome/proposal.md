# Proposal

## Why

The home page's worked example takes up most of its height with the input: the message and a full-size vaccine card. Its payoff is a "Sent" tag and a sentence *describing* that a reply went out, so a visitor never sees what PawDesk actually did. Nothing marks the card as an example either, so it can read as a live request. And the clean sample's card says Biscuit got his DHPP shot on Nov 24, 2026. The demo runs on a fixed date (Mar 3, 2027), so that's in the past for the checks, but a visitor reading the page today sees a shot given next month.

## What Changes

- **The worked example is labeled as an example** at the top.
- **The vaccine card opens as a short preview** that expands to the full card, so the example is about as tall as before once the outcome is added.
- **The example ends with what PawDesk did:** it booked a medium kennel for the stay and sent a reply. The reply's subject and first paragraph are shown, and the rest opens on demand. The text is the reply from the clean sample's recorded run.
- **No date given on a sample's card is after the real calendar date.** Biscuit's DHPP date becomes Nov 24, 2025; his card is redrawn and the clean sample's recorded model responses are recorded again.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the worked example is labeled, previews the card, and shows the outcome and reply.
- `observability-api`: no vaccine on a sample's card was given after the real calendar date.

## Impact

- **Backend:** `scripts/draw_sample_cards.py` (Biscuit's DHPP date), `app/sample_cards/biscuit.png` (redrawn), `tests/cassettes/e2e/` (the clean sample's records call and anything after it), and a test that no date given on a card is after the real calendar date.
- **Frontend:** `app/page.tsx` (the worked example), a small client component for the expanding parts, and `content/worked-example.json` (the reply and the kennel size).
- **Tests:** end-to-end checks of the label, the card preview expanding, and the outcome; the clean-sample run checks that its reply matches the one the home page quotes.
- **Not changed:** the certificate benchmark's cert-28, which prints the same future date. Its truth file and measured results stay as they are.
