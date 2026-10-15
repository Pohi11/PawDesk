# Design

## Context

- **The home page** describes the agents, the rules, and the steps in prose and tables (changes `home-page-agents`, `home-page-booking-rules`).
- **The dashboard's tokens** give each color a meaning: violet for model steps, blue for code, amber for tools, orange where a person acts, green for done. The run graph already uses them.
- **The architecture** is recorded across decision records: the hybrid workflow ([0008](../../../../docs/decisions/0008-hybrid-workflow-over-agentic.md)), durable steps ([0009](../../../../docs/decisions/0009-durable-execution-with-step-checkpoints.md)), the human gate ([0011](../../../../docs/decisions/0011-human-gate-before-sending.md)), live updates ([0013](../../../../docs/decisions/0013-live-updates-sse-from-database.md)), and hosting ([0019](../../../../docs/decisions/0019-host-demo-on-hugging-face-and-neon.md)).
- **The home page's booking rules** live in `frontend/content/booking-rules.json`, checked by a backend test. That pattern keeps hand-written page content true to the code.

## Goals / Non-Goals

**Goals:** a visitor can follow how a request moves through the system, and who may change its state, from the diagrams alone.

**Non-Goals:**
- a diagramming library or generated diagrams from code (the page draws a handful of fixed figures);
- live data on the page (the run view already shows one request's real trace);
- new colors.

## Decisions

### D1. Hand-drawn inline SVG through a small helper
- **Options:** Mermaid (a runtime dependency that renders client-side and styles poorly with the dashboard's tokens); React Flow, already used for the run graph (built for interactive graphs, heavy for static figures); inline SVG drawn in server components.
- **Decision:** inline SVG. `components/diagram.tsx` provides a frame, boxes, a database shape, and arrows, colored with the dashboard's tokens through Tailwind's `fill-*` and `stroke-*` classes.
- **Why:** no new dependency, no client JavaScript, and the figures use the same colors as the run graph, so a violet box means a model call on every page.

### D2. Color and line style carry meaning
- **Boxes** take the color of who does the work: violet for a model, blue for code, amber for a tool, orange for a person. Dashed outlines mark parts outside the codebase (the browser, OpenRouter, the pet parent's input).
- **Lifecycle arrows** take the color of the actor: blue for the system, orange for staff. The two arrows into `approved` are drawn heavier, and `approved` has a ring.
- **States that can fail** carry a small red notch instead of six arrows into `failed`, which would cross most of the figure.

### D3. The lifecycle and step map come from data the backend checks
- **`frontend/content/architecture.json`** holds the transitions (from, to, actor), the failable states, and the state-to-step map.
- **A backend test** compares it with `ALLOWED`, `CAN_FAIL`, and `STEPS` (by function name). A changed rule fails the test until the page changes too.
- **A frontend unit test** checks that every transition in the data has one drawn arrow and every arrow is a transition, so the figure can't drop or invent an edge.
- **The other diagrams** describe structure that changes rarely and is hand-written. They name real modules and spans, and review keeps them true.

### D4. Text equivalents
- **Each SVG** has `role="img"`, a name through `aria-labelledby` (its visible heading), and a description through `aria-describedby`.
- **The lifecycle's description** is generated from the same transitions the figure draws. The others are written next to the figure as the explanation a sighted reader gets too.

### D5. Layout
- **Wide figures** (system, lifecycle, model output) sit in a frame that scrolls sideways on its own below their drawn width, so the page itself never scrolls sideways.
- **The request path** is drawn top to bottom, so it fits a phone without scrolling. On wide screens it sits beside its step list.

## Risks / Trade-offs

- [The hand-written diagrams can drift from the code] → Each names the module or span it shows, and the lifecycle and step map, the parts most likely to change, are tested.
- [A wide figure is small on a phone] → The frame scrolls, and each figure's description carries the same content in text.
