# Design

## Context

- **The hero has three links:** "Try a request" (`#try`), "How it works" (`#how`), and "Skills in detail" (`#skills`).
- **The sections below the Try panel run in reading order:** booking rules (`#rules`), the agents, how a request moves (`#how`), the tests, the skills, and the method.

## Goals / Non-Goals

**Goals:** "How it works" starts the visitor at the top of the explanation.

**Non-Goals:** reordering the sections, or adding a table of contents.

## Decisions

### D1. Point the link at `#rules`
- **The explanation starts with the rules:** every later section refers back to them, so they are the natural entry point.
- **Alternative considered:** moving "How a request moves" above the rules. It would keep the link, but the steps make more sense once the rules they check are known.

## Risks / Trade-offs

- [The link text no longer matches a heading] → "How it works" names the whole explanation, and the rules are its first part.
