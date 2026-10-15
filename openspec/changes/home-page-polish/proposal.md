# Proposal

## Why

The first version of the home page leaned on stock landing-page parts: an all-caps label over the headline, numbered markers on a list that isn't a sequence, a grid of identical page cards, a row of big numbers, and a cloud of technology tags. Its copy used slogan endings, three-part lists, and passive sentences. Seven sections, two of which repeated the navigation and the skills table, made the page longer than what a visitor needs.

## What Changes

- **The introduction shows one real request:** the clean sample's message, with the parts a model reads marked, and the results code checked listed under it. The marks use the run graph's colors for model and code.
- **The page has four parts after the Try panel instead of six:**
  - how a request moves, as one ordered timeline, with the guarantees the tests check under it;
  - why the project was built, with a table that pairs the job posting's skills with the technologies PawDesk uses;
  - how the code is written with an AI assistant, as the sequence each change follows, with the live requirement and test counts in the text.
- **Removed:** the page cards (the text links to each page where it mentions it), the big-number row, the technology tags (the table names each technology), and the all-caps label.
- **The copy is rewritten** in active voice, naming who acts, following `docs/style/interface-copy.md`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the home page's sections after the Try panel, and the worked example in its introduction.

## Impact

- **Frontend:** `app/page.tsx`.
- **Tests:** the home page end-to-end test checks the new sections and the example.
