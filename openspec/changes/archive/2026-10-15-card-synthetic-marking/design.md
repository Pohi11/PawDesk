# Design

## Context

- **The demo card template** (`app/certificate_card.py`, change demo-generated-requests) draws a footer, "PawDesk demo certificate. Not a real record.", to mark the card as synthetic.
- **The records step** reports anything on the card that makes it unsure as an ambiguity, and routing sends any ambiguity to a person. Reading "Not a real record" as a reason for doubt is correct: on a real card, that line would be a red flag.
- **The fixed sample cards** are committed PNGs drawn by `scripts/draw_sample_cards.py`; the end-to-end model responses are keyed by the request body, which includes the image bytes.

## Goals / Non-Goals

**Goals:** the clean sample passes the records step without a person; demo cards stay identifiable as synthetic.

**Non-Goals:** telling the records prompt to ignore disclaimers; changing the certificate benchmark's watermark.

## Decisions

### D1. Fix the card, not the prompt
- **A prompt exception** ("ignore a footer saying it's a demo") would teach the records step to overlook exactly the text a forged or voided card might carry. Untrusted input stays untrusted.
- **Removing the line** removes the only cause of the ambiguity on an otherwise clean card.

### D2. The marking moves into PNG metadata
- **A `Comment` text chunk** keeps each file self-describing for anyone who inspects it, and the model never sees it: only the decoded pixels reach the records step.
- **Fictional names** (clinic, vet, pet, owner) and the demo pages' own labels still show the cards are synthetic.
- **The benchmark keeps its watermark,** because its spec requires visible marking and the eval measures reading those images unchanged.

## Risks / Trade-offs

- [A demo card copied out of the page loses obvious marking] → The metadata travels with the file, and every name on it is fictional.
- [Re-recording uses real model calls] → Only the requests whose card bytes changed are recorded again; the rest keep their committed recordings.
