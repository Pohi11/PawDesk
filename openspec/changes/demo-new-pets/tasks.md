# Tasks

## 1. Generator

- [x] 1.1 Invent the pet from the seed (species, pool name, breed, weight), show the breed on the card, and add choosing a fresh seed. Verify with tests: pool sizes and clearance, same request before and after sending, names vary, fresh seeds skip names on file and recent names, a given seed is kept, and the scenario checks still pass.

## 2. API

- [x] 2.1 Accept `avoid` on `GET /demo/generate` and add the pet on send. Verify with API tests: a name on file and recent names are skipped, sending adds one pet with the generated details, and sending twice reuses it.

## 3. Dashboard

- [ ] 3.1 Keep the last 10 generated names in session storage and send them with each generation. Verify with a frontend test of the request URL, then lint, type check, build, and the end-to-end demo.
- [ ] 3.2 Try it in a browser: generate several requests, check the names don't repeat and the cards match, and send one. Verify with a screenshot and the run's outcome.

## 4. Integration

- [ ] 4.1 Run every suite and the coverage check, then regenerate the walkthrough.
