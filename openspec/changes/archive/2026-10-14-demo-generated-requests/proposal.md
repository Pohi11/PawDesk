# Proposal

## Why

The Try page offers four fixed samples, and its vaccine certificates can't be seen: the page says a card "is attached" without showing it. That falls short in two ways:
- **Showing the system.** A reader can't check what the records step was supposed to read, so they can't judge whether it read it right.
- **Exploring the system.** Four fixed cases show four fixed paths. A request made up on the spot shows the desk handling something it was never tuned on.

## What Changes

- **Generate a random request:**
  - a seeded owner and one of their pets;
  - a service that pet can have;
  - dates soon after the demo day;
  - a message in a pet parent's words;
  - a vaccine certificate that matches all of it.
- **The card follows one scenario,** stated in plain words:
  - every vaccine current;
  - one expired before the stay;
  - one expiring during the stay;
  - one missing from the card.
- **Reproducible:** a seed fully determines the request and its card, so the same seed always gives the same request and image.
- **See the card before sending,** for generated requests and for the fixed samples.
- **Send a generated request.** It runs exactly like a sample, with its card attached.

## Capabilities

### New Capabilities
- `demo-generator`: Generating reproducible random demo requests with a matching vaccine certificate image, serving the image for preview, and sending a generated request.

### Modified Capabilities
- `run-dashboard`: the proxy also forwards the demo preview paths, and the Try page previews a request together with its certificate.

## Impact

- **Backend:**
  - new `app/demo_generator.py` (request and scenario) and `app/certificate_card.py` (the card, drawn with Pillow);
  - demo routes in `app/api.py`;
  - Pillow becomes a runtime dependency.
- **Frontend:** the Try page gets a "Generate a request" choice and a certificate preview, and the proxy allowlist grows.
- **Tests:**
  - generation and its scenarios against a seeded database;
  - the image endpoints;
  - sending a generated request with a scripted model;
  - frontend tests for the proxy paths and preview helpers;
  - the end-to-end demo still passes.
