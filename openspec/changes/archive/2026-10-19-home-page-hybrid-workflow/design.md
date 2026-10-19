# Design

## Context

- The architecture is recorded in [0008 — A hybrid workflow](../../../../docs/decisions/0008-hybrid-workflow-over-agentic.md): a plain async function fixes the order, models are used only for reading and writing, and a multi-agent supervisor was considered and rejected.
- The introduction's first paragraph said "PawDesk is a multi-agent workflow", which contradicts that record.

## Goals / Non-Goals

**Goals:** the introduction and the Space description name the architecture PawDesk actually has.

**Non-Goals:** renaming the agents section. Intake, records, resolver, and reply are still agents inside the workflow; the section describes each one's limits.

## Decisions

### D1. Say "hybrid workflow" and explain it in the same sentence
- The term alone means little to most visitors, so the sentence says who decides the order (code) and where agents are used (messy input).
- **Alternative considered:** "AI workflow". It is vaguer and hides the main design point, that code, not a model, decides what happens next.

### D2. The test checks the wording directly
- One end-to-end test reads the introduction and checks it contains "hybrid workflow" and not "multi-agent". It fails with the old text.
