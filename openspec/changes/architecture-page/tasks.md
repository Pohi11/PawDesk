# Tasks

## 1. Data and checks

- [ ] 1.1 Add `frontend/content/architecture.json` with the transitions, failable states, and state-to-step map, and a backend test that checks it against `ALLOWED`, `CAN_FAIL`, and `STEPS`. Verify with the test.

## 2. Page

- [ ] 2.1 Add `components/diagram.tsx` and `app/architecture/page.tsx` with the six diagrams and the tables list, and a unit test that every transition has one drawn arrow. Verify with the unit test, the copy check, lint, and type check.
- [ ] 2.2 Add Architecture to the navigation, and an end-to-end test that opens the page from the link, finds the six diagrams by name, and checks phone width. Verify with the end-to-end test.
- [ ] 2.3 Check the page in a browser at desktop and phone widths. Verify with screenshots.

## 3. Integration

- [ ] 3.1 Run every suite and the coverage check, then regenerate the walkthrough.
