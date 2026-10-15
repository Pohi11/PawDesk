# Proposal

## Why

The first version of the home page leaned on stock landing-page parts: an all-caps label over the headline, numbered markers on a list that isn't a sequence, a grid of identical page cards, a row of big numbers, and a cloud of technology tags. Its copy used slogan endings, three-part lists, and passive sentences. Seven sections, two of which repeated the navigation and the skills table, made the page longer than what a visitor needs.

## What Changes

- **The introduction says plainly what PawDesk is, why it was built, and what it has,** in a few sentences and a short list of features named in the job posting's terms. The all-caps label above the headline goes.
- **Beside it, one real request:** the clean sample's message, with the parts a model reads marked, and the results code checked listed under it. The marks use the run graph's colors for model and code.
- **The page has three parts after the Try panel instead of six:**
  - how a request moves, as one ordered timeline, with the guarantees the tests check under it;
  - how the code is written with an AI assistant, as the sequence each change follows, with the live requirement and test counts in the text;
  - last, a table that pairs each of the job posting's skills with the technologies and parts of PawDesk that use it.
- **Headings across the dashboard use Fraunces** instead of Bricolage Grotesque.
- **Removed:** the page cards (the text links to each page where it mentions it), the big-number row, the technology tags (the table names each technology), and the all-caps label.
- **The copy is rewritten** in active voice, naming who acts, following `docs/style/interface-copy.md`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the home page's introduction (purpose, features, worked example) and its sections after the Try panel.

## Impact

- **Frontend:** `app/page.tsx`; `app/layout.tsx` and `app/globals.css` for the heading font, which every page uses.
- **Tests:** the home page end-to-end test checks the new sections and the example.
