# 0001 — Adopt OpenSpec for spec-driven development

- **Date:** 2026-10-13
- **Status:** Accepted

## Context

Transparency is a core goal of PawDesk, and it has two separate audiences:

1. **Runtime:** how the agents processed a specific booking (spans, prompts, costs, approvals). The observability dashboard covers this.
2. **Build time:** how each feature was specified, decided, and verified.

Build-time transparency needs structured source data that is tied to the code and tests. Hand-written prose goes out of date as the code changes.

## Options considered

1. **No spec tool.** A build-history page written by hand. This is simple, but it isn't tied to the code and goes out of date.
2. **A home-grown spec format.** Full control, but it rebuilds what an existing tool already provides, and an unfamiliar format makes the project harder to follow.
3. **OpenSpec.** Each change gets a proposal, spec deltas (requirements with WHEN/THEN scenarios), a design, and tasks. Finished changes are archived with a date, and their spec changes merge into the current specs.

## Decision

Option 3. Every feature starts as an OpenSpec change. Each change is reviewed and approved before implementation begins, and archived when it's done.

Runtime transparency and build-time transparency are shown on **separate pages**: the observability dashboard and the build walkthrough.

Each kind of information lives in one place:

| Information | Lives in |
|---|---|
| Current system behavior, and the plan for each change | `openspec/` |
| Decisions that span more than one change | `docs/decisions/` (a change's `design.md` links here) |

## Consequences

- **Good:** The build walkthrough page is generated from repo data (archived changes, specs, test results), so it can't drift from reality.
- **Good:** Requirements are traceable: spec → test → latest result.
- **Cost:** Every test must name the requirement it verifies. The convention is set with the first spec, because adding it to existing tests later is painful.
- **Cost:** An extra tool to install (a global npm package that needs Node ≥ 20.19). Its anonymous telemetry is turned off.
