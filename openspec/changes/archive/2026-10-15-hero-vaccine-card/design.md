# Design

## Context

- **The worked example is the clean sample,** whose message and outcome the end-to-end test already asserts. That sample attaches `cert-28.png` from the certificate benchmark, served at `/api/demo/samples/clean/certificate.png`.
- **The Try panel already shows the same image** for the selected sample, through the same proxy route.

## Goals / Non-Goals

**Goals:** a visitor sees both inputs of one request, the message and the card, before reading what code concluded from them.

**Non-Goals:** marking up individual fields on the card, or changing the coverage strip in the booking rules section.

## Decisions

### D1. Load the image from the sample route, not a copy in `public/`
- **One source of truth:** the hero shows exactly the file the clean sample sends, so the two can't drift apart.
- **The home page already needs the API** for the Try panel's samples, so the hero adds no new dependency.
- **Alternative considered:** copying the PNG into `frontend/public/`. It would load without the API, but it duplicates a binary that already lives with the benchmark.

### D2. Placed between the message and the facts
- **The order follows the run:** both inputs first, then what code checked. The card sits under the message with a short caption.
- **A violet ring and the "A model read it" dot** mark it as input the records agent read, matching the highlighted words in the message.

## Risks / Trade-offs

- [The API is down] → The image shows its alt text, and the rest of the example is static text, so the hero still reads correctly.
