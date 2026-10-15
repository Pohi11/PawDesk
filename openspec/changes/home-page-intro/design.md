# Design

## Context

- **`/` is the requests list** today, and `/demo` is the Try page (`DemoPanel` over the samples from `GET /demo/samples`).
- **The explanation of the project** lives in the README: what the desk does, the hybrid workflow, the measured results, and the method. A visitor to the hosted demo sees only the dashboard.
- **The How it was built page** (`/build`) already shows generated totals (requirements proven, tests, changes, decision records) from `content/walkthrough.json`.
- **Interface copy** follows `docs/style/interface-copy.md` (decision record [0018](../../../docs/decisions/0018-plain-voice-for-interface-copy.md)). The build checks the banned words and em dashes in every page.

## Goals / Non-Goals

**Goals:**
- A visitor who knows nothing about PawDesk can say what it does after the first screen, and can send a request without leaving the page.
- The page explains the workflow, the safety rules, the other pages, the reason for the project, and the stack, in plain words.

**Non-Goals:**
- changes to the Try panel itself;
- new backend data.

## Decisions

### D1. One page: a short introduction, the Try panel, then the explanation
- **Options considered:**
  - a landing page at `/` that links to `/demo` (one more click before trying anything);
  - the Try page at `/` and the explanation at `/about` (most visitors would never open it);
  - one page: a short introduction above the panel and the longer explanation below it.
- **Decision:** one page. The introduction is a heading, two sentences, and links, so the panel starts high on the first screen. Everything a visitor reads after trying a request sits below the panel.
- **Trade-off:** a long page. Each section has a plain heading, so it scans.

### D2. Counts come from the walkthrough, measured results from the eval reports
- **Counts that change with every change** (requirements proven, tests, changes, decision records) are read from `content/walkthrough.json`, as on `/build`, so the page can't fall out of date.
- **Measured results** are the ones the README already reports from dated eval reports. They change only when an eval is run again, and the page links to the evals page for the reports.
- **Everything else is hand-written** and has to match the code, as the copy guide requires.

### D3. The job posting section lists only what the code shows
- **Each line pairs a skill from the posting with where PawDesk uses it** (a page, a test suite, a file).
- **Skills the project doesn't show are left out** (AWS, Agile ceremonies) rather than stretched to fit.
- **This section is in the first person:** it is the author's introduction, the one part of the dashboard that speaks for a person.

### D4. Addresses
- **`/requests`** gets the list; the request pages are already at `/requests/<id>`, so the list and its rows share a prefix.
- **`/demo` redirects to `/`** with a temporary redirect from `next.config.ts`, so browsers don't cache it if the address is reused later.

## Risks / Trade-offs

- [Hand-written claims can drift from the code] → Volatile counts are generated (D2), and the copy check covers the page's text.
- [The panel sits lower on a phone] → The introduction stays short, and its first link jumps to the panel.
