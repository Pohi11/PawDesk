# Tasks

## 1. Generator

- [x] 1.1 Add `app/demo_generator.py` (request, scenario, and records from a seed) and `app/certificate_card.py` (the card drawn with Pillow), and move Pillow to the runtime dependencies. Verify with `tests/test_demo_generator.py` against a seeded database: same seed gives an identical request and image, seeds vary pets, services, and scenarios, the card names the pet and owner, and scenario dates checked alone give the expected compliance status.

## 2. API

- [x] 2.1 Add the preview routes and accept `{seed}` on demo submission. Verify with API tests: a generated certificate PNG equal to the one attached on send, 404 for a sample without a certificate, and sending a seed stores the request with its card and processes it with a scripted model.

## 3. Dashboard

- [ ] 3.1 Extend the proxy allowlist and the Try page (generate, preview message, scenario, and card, generate another, send). Verify with frontend tests for the new proxy paths and the submission body, then lint, type check, build, and the end-to-end demo.
- [ ] 3.2 Try it for real in a browser: generate requests, check each card against its request, and send one. Verify with screenshots and by recording the outcome.

## 4. Integration

- [ ] 4.1 Run every suite and the coverage check, then regenerate the walkthrough.
