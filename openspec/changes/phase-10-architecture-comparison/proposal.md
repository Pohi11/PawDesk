# Proposal

## Why

PawDesk is a hybrid workflow: code fixes the order, models only read and write, code decides, and a single fenced agent may only propose (decision records 0008 and 0010). That choice was argued from principles: error compounding, injection risk, testability. It was never measured against the obvious alternative: one autonomous agent given every tool and the whole request, deciding everything itself.

The comparison is worth measuring because the alternative is simpler to build and might be good enough. The comparison has to be fair:
- the same cases;
- the same model;
- the same deterministic checking tools;
- the same expected answers;
- failures, including injection attempts, counted the same way.

## What Changes

- **An autonomous agent** (`app/autonomous.py`). One model gets:
  - the customer's message and certificate image;
  - read-only tools: the owner's pets, a vaccine check, a kennel check, alternative dates;
  - a final decision tool: confirm, offer alternatives, or hand to a person.

  It runs in a loop with the same step limits and stuck guard as the resolver. It writes nothing.
- **A comparison set** of booking cases on seeded owners and benchmark certificates. It includes clean requests, failing and borderline vaccines, a full-kennel request, an unknown pet, unclear dates, and three injection attempts. Each case's expected outcome is computed by running the deterministic checks on the case's *true* facts (certificate ground truth, the pet on file), not labeled by hand.
- **A lab runner** (`scripts/compare_architectures.py`):
  - creates and seeds a separate lab database;
  - runs every case through both architectures, stopping the hybrid workflow before anything is sent;
  - writes a dated report with accuracy, unsafe confirmations, injection handling, cost, latency, model calls, and failures per architecture.
- **The dashboard's Evals page** shows the comparison side by side.
- **A decision record** with the measured conclusion.

## Capabilities

### New Capabilities
- `architecture-comparison`: The autonomous-agent alternative, the comparison set with computed expectations, the isolated lab run of both architectures, and the scored report.

### Modified Capabilities
None.

## Impact

- **Backend:**
  - new `app/autonomous.py` and `app/prompts/autonomous.py`;
  - new `scripts/compare_architectures.py`;
  - new `evals/comparison_cases.json`.
- **Frontend:** the Evals page renders comparison reports.
- **Tests:**
  - the agent loop against scripted turns;
  - the scoring and expected-outcome logic;
  - the lab database guard.
- **One real run** of both architectures over the whole set, which costs real model calls (a few tenths of a dollar at most).
- **Out of scope:**
  - making the autonomous agent production-ready;
  - comparing other models;
  - multi-agent alternatives.
