# Design

## Context

- **The path** (`components/run-graph.tsx`) is a React Flow graph of nine fixed steps. Each step's status comes from `nodeStatuses` in `lib/graph.ts`, and clicking a step opens it in the inspector.
- **The run view** already holds the full request detail (`RequestDetail`): each step's saved output under `steps`, the approvals, and the sent message. Live updates replace it on every snapshot.
- **React Flow clips** anything drawn inside its viewport to the graph's box, and the graph is only 208 to 240 px tall.

## Goals / Non-Goals

**Goals:** say what each step is for and what it found, readable by someone new to the desk, by mouse or keyboard.

**Non-Goals:**
- replacing the inspector (the tooltip is a summary; the inspector keeps the exact inputs and outputs);
- tooltips on timeline bars;
- new API fields.

## Decisions

### D1. A pure summary function
- `stepSummary(id, status, detail)` in `lib/step-summary.ts` returns `{ does, result }`:
  - `does` is fixed per step;
  - `result` depends on the status and the request detail.
- **Pure,** like `nodeStatuses`, so every case is unit-tested without a browser, and the live view just calls it again on each snapshot.
- **Defensive reads:** `steps` is untyped JSON, so each field is checked before use. A missing field gives a plain fallback ("Done."), never an error.

### D2. What each step says once it has run
| Step | Result line, for example |
|---|---|
| Intake | "Read boarding for Rosie, Mar 9–12, 2027.", plus how many things it flagged for a person |
| Records | "Read 3 vaccines from the card: Rabies, DHPP, Bordetella." or "No certificate attached." |
| Compliance | "Every required vaccine covers the stay." or "Bordetella expired." |
| Capacity | "Kennel M2 is free." / "No medium kennel is free." / "No kennel needed for grooming." |
| Route | "Every check passed, so straight to the reply." or "3 things to look at (vaccines and kennel space), so on to the resolver." |
| Resolver | "Found 3 options, all checked." or why it did not try |
| Reply | the situation in words, then "passed the promise check" or the first flag |
| Staff review | "Approved by Dana." / "Waiting for a person." / "Not needed: nothing was flagged." |
| Send | "Sent a confirmation." / "Sent a decline." / "Not sent yet." |

Steps that are waiting say "Not run yet." Running steps say "Working on it now."

### D3. The tooltip lives outside React Flow
- **React Flow's viewport clips its contents,** so a tooltip drawn inside a node would be cut off at the top and bottom of the graph.
- **The tooltip renders in the graph's wrapper** (`position: relative`, not clipped). It's placed below the hovered step from the step's bounding box relative to the wrapper, and clamped so it stays inside the wrapper's width.
- **One tooltip at a time,** keyed by the step id.

### D4. Keyboard and screen readers
- **Each step's content is a `<button>`.** Enter or Space opens the step in the inspector, like a click. React Flow's own node focus is turned off, so each step is one tab stop, not two.
- **Focus shows the same tooltip as hover.** The button's `aria-describedby` points at the tooltip (`role="tooltip"`), so it's announced.
- **Escape hides the tooltip** until the pointer or focus moves to another step. The pointer can move onto the tooltip without it disappearing, so it can be read and selected (WCAG 1.4.13: dismissible, hoverable, persistent).

### D5. Only structured facts in the tooltip
- **The result line uses structured fields:** service, dates, vaccine names, kennel names, statuses, counts, and the staff member's name.
- **It never quotes** the pet parent's message, or model free text such as the resolver's summary or a drafted reply. Those stay in the story section and the inspector, where they're labeled as such. React escapes all text either way.

## Risks / Trade-offs

- [The summaries depend on the shape of each step's saved output, which the backend owns] → Defensive reads with plain fallbacks (D1), and unit tests on real shapes copied from a run.
- [Hover tooltips can hide part of the graph] → It's placed below the step, appears only while hovered or focused, and Escape hides it.
