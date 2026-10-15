# Proposal

## Why

The home page calls PawDesk a multi-agent workflow, but it never says which agents there are or what each one is allowed to do. The steps section mixes the agents with the code around them, so a visitor can't see each agent's input, output, and the code check that limits it. Those limits are the main design point of the project.

## What Changes

- **A new section, "The agents", above "How a request moves".** It lists the four model-driven parts (intake, records, resolver, reply) with what each reads, what it returns, and what code checks before its output counts.
- **It says how much of each one is a model:** intake, records, and reply make one model call each; the resolver runs a short loop with read-only tools and a step limit.
- **The steps section gets shorter,** since the agents section now holds the detail. Each step names the agent or the code that runs it.
- **The introduction names the product** ("PawDesk is a multi-agent workflow…") instead of starting with "It's".

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the home page describes each agent.

## Impact

- **Frontend:** `app/page.tsx`.
- **Tests:** the home page end-to-end test checks the new section and its four agents.
