# 0007 — How LLM steps are evaluated

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

Unit tests prove that the pipeline around a model is correct: validation, repair, code checks, and handoff. They use scripted answers, so they can't say how *good* the model is at reading messages or certificates. That needs an evaluation against the real model. Evaluations cost money, vary between runs, and are easy to misreport: a cherry-picked demo, a number remembered from an older prompt, or an accuracy figure that hides the errors that actually matter. This project already has two such steps (intake and records), and the architecture comparison will need a fair way to compare whole systems.

## Options considered

1. **Manual spot checks.** Fast, but not repeatable and not comparable over time.
2. **One overall accuracy number per step.** Simple, but it hides *which* errors happen and whether they change decisions.
3. **Labeled sets with layered metrics, run on demand, with every run stored as a dated report.**
4. **An LLM judge scoring free-form outputs.** Useful for open-ended text, but unnecessary when ground truth is exact, and it adds a second model's errors.

## Decision

Option 3, with these rules for every evaluated step:

- **Ground truth is exact.** Labeled cases (intake) or generated data whose truth is known by construction (records). Fields that are genuinely open to interpretation are marked unscored rather than guessed.
- **Three levels of metric:**
  1. **Field accuracy**, per field.
  2. **Dangerous errors counted separately.** For example, *invented expiries*: a missing value made up by the model.
  3. **Decision agreement:** run the deterministic decision (compliance) on the truth and on the model's output, and compare. **Silent disagreements**, where the decision is wrong *and* nothing sent the case to a person, are the headline safety number.
- **Results are broken down** by case type or variant, not only averaged.
- **Every run is a measurement:**
  - It runs against the real model only on demand.
  - It is traced like production, so its cost comes from span rows.
  - It is written to `backend/evals/results/<step>-<timestamp>.json` with the prompt version, model, and trace id.
  - It is never edited by hand. Numbers are quoted with the run they came from, never estimated or averaged across prompt versions.
- **Benchmarks are versioned.** The labeled files and generated images are committed. Changing them creates a new benchmark, not a silent edit.
- **Scoring code is unit-tested** with scripted answers, so the evaluation itself can be trusted.

## Consequences

- **Good:** A prompt or model change can be judged by its effect on decisions, not just on field accuracy.
- **Good:** The same method extends to the architecture comparison: the same sets, the same metrics, and the same cost accounting.
- **Cost:** Real-model runs cost money. Intake and records each run in cents, so they're run deliberately, not on every commit.
- **Limitation:** Synthetic benchmarks are cleaner than real-world input. Results are reported as performance on *this* benchmark, never as real-world accuracy.
