# Proposal

## Why

The hero's "How it works" link jumps to "How a request moves", which sits below the booking rules and the agents. A visitor who follows it skips the rules that decide every outcome and lands halfway down the explanation.

## What Changes

- **"How it works" opens the booking rules,** the first section below the Try panel, so the explanation reads from the top: rules, then agents, then how a request moves.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the hero's "How it works" link goes to the booking rules section.

## Impact

- **Frontend:** `app/page.tsx`.
- **Tests:** the home page end-to-end test follows the link and checks the booking rules heading is in view.
