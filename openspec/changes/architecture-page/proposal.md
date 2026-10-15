# Proposal

## Why

The home page lists the agents and the steps in words, but a visitor can't see how the parts fit: which process runs what, where the database sits between them, which states a request moves through and who may move it, and how a crashed run picks up again. These are the questions a technical reviewer asks first, and each one takes several source files to answer today.

## What Changes

- **A new Architecture page at `/architecture`,** linked from the navigation between Evals and How it was built.
- **Six diagrams, each with its explanation beside it:**
  - the parts of the system and how they connect (browser, dashboard, proxy, API, orchestrator, Postgres, OpenRouter), with how the hosted demo differs from local development;
  - the path one request takes through the agents, the checks, routing, the resolver, the reply, the promise scan, and the review queue;
  - the lifecycle states, with the actor allowed on each transition, the only two ways into `approved`, and the states that can fail;
  - the step loop that maps each state to one step function and commits after each step;
  - what a model's output passes through before code uses it;
  - how tracing records each step as a span and how the run view reads them.
- **A short list of the tables,** grouped by what they hold.
- **The lifecycle transitions and the state-to-step map live in `frontend/content/architecture.json`.** The page draws from it, and a backend test checks it against the lifecycle rules and the orchestrator's step map.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: adds the Architecture page and its check against the backend.

## Impact

- **Frontend:** a new `app/architecture/page.tsx`, a diagram helper in `components/diagram.tsx`, a new `content/architecture.json`, and the navigation in `app/layout.tsx`.
- **Backend:** one new test that reads `content/architecture.json`. No runtime change.
- **Tests:** an end-to-end test for the page and the navigation link, and a unit test that every transition in the data has a drawn arrow.
