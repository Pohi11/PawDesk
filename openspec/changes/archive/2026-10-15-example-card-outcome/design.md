# Design

## Context

- **The worked example** (`WorkedExample` in `app/page.tsx`) is a server-rendered figure: a "wrote, with a photo attached" line, the message with model-read parts marked, the card at full width (1000x680), four facts, a Sent tag with one sentence, and a color legend. It sits beside the intro on wide screens.
- **The clean sample's reply** exists only in its recorded model response (`tests/cassettes/e2e/`). The run page shows it after a run.
- **Biscuit's card** is drawn by `scripts/draw_sample_cards.py`, committed, and served as stored. The recorded responses are keyed by the request bytes, so a redrawn card needs its calls recorded again.

## Goals / Non-Goals

**Goals:** a visitor sees the whole story, request to result, in one card about as tall as today's; the card can't be mistaken for a live request; no date given that's still in the future for a visitor.

**Non-Goals:** checking dates given on real cards (a separate rule if wanted), changing the benchmark cards, changing the run page.

## Decisions

### D1. The outcome shows the action and the reply, not a description of them
- **Action line:** "PawDesk booked that kennel and sent this reply:", right after the Kennel fact, which now says "A medium one is free all three nights" so the two don't repeat each other. Biscuit weighs 24 lb, so the size follows from the weight bands. The kennel's name isn't shown: it depends on which kennels are free in the database at the time.
- **Reply:** subject in bold, then the first paragraph. The rest opens with "Show the full reply". The first paragraph carries the confirmation; the rest is pleasantries.
- **"No one on staff involved"** moves next to the Sent tag as a short note, since the reply itself now shows what was sent.

### D2. The reply text lives in one JSON file that a test checks against a real run
- **`content/worked-example.json`** holds the subject and body, the same pattern as `booking-rules.json`.
- **The clean-sample end-to-end run** reads the same file and checks that the run page shows that subject and first paragraph. If the recorded responses are recorded again and the reply changes, that test fails instead of the home page quietly quoting an old reply.
- **Alternative rejected:** fetching a live run's reply on page load. It would cost a model call per visit or need a stored run, for text that changes only when the recordings do.

### D3. The card collapses to a preview, not a link
- **Collapsed, the card shows its top 7rem** (the clinic header and the start of the table) with a fade, and a "Show the full card" button below. Expanded, it shows in full and the button says "Hide the full card".
- **The image stays in the page either way,** so it loads once and the existing check that it loads still holds.
- **Hiding it completely was rejected:** the photo is the visible proof that a model read an image, and the Vaccines fact already gives the conclusion, so a preview is enough.
- **A small client component** handles both expanders (card and reply) with a button that sets `aria-expanded` and `aria-controls`. A `<details>` element was rejected for the card: its summary would need a second copy of the image for the preview.

### D4. The label is a short line, not a banner
- **"Example request"** in medium weight starts the first line, before "Avery Lindqvist wrote, with a photo attached:". Sentence case, no badge, in keeping with the page's earlier move away from all-caps eyebrows.

### D5. Fix the date on the demo card only
- **Biscuit's DHPP date becomes Nov 24, 2025.** It stays before the stay and the expiry stays Mar 9, 2028, so the clean sample's outcome doesn't change.
- **The benchmark's cert-28 keeps Nov 24, 2026.** Its truth file and measured eval results were recorded against that image; changing it would make past numbers unreproducible.
- **The demo's checks run on `DEMO_TODAY` (Mar 3, 2027),** so for them the old date was already in the past. The rule is about what a visitor reads, so the test compares against the real date (`date.today()`), not `DEMO_TODAY`.
- **A test reads every sample's records** from the drawing script, the source of the committed cards. A date that passes once keeps passing as the calendar moves on.

## Risks / Trade-offs

- [Re-recording can change the clean sample's reply] → D2's test catches it; update the JSON to the new reply.
- [The preview's crop depends on the card's layout] → The card is a fixed committed image; the crop is a CSS height, checked in the browser at desktop and phone width.
