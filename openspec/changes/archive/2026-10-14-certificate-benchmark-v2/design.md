# Design

## Context

Benchmark v1 lives in `backend/evals/certificates/` (`images/`, `truth.json`), generated from a seed by drawing random dates. Its first evaluation report (`records-20261014T154345Z.json`) refers to it. [Decision record 0007](../../../../docs/decisions/0007-evaluating-llm-steps.md) requires benchmarks to be versioned, never edited in place.

## Goals / Non-Goals

**Goals:**
- Correct decisions that make agreement informative, plus boundary cases where one-day misreads matter.
- v1 stays reproducible.

**Non-Goals:**
- New layouts or variants.
- Changing scoring.
- Changing the records step.

## Decisions

### D1. Choose the decision first, then build records that produce it
Each v2 certificate gets a target before any dates are drawn. Variants are assigned as in v1 (6 per variant, 12 per layout).

| Group | Count | Target and construction |
|---|---|---|
| `missing_expiry` | 4 | `needs_review`: a *required* vaccine has no expiry; all others cover the stay |
| `missing_expiry` | 2 | `compliant`: the missing expiry is on an *optional* vaccine, which is always included |
| other variants | 15 | `compliant`, 4 of them with a required vaccine expiring exactly on checkout day |
| other variants | 15 | `not_compliant`, 4 of them with a required vaccine expiring the day before checkout, the rest with one already expired |

A record that covers the stay is given on or before today and expires 20–700 days after checkout.

The overall mix is about 47% compliant, 42% not compliant, and 11% needs review.

### D2. The generator verifies itself
After building a certificate, the generator runs `app.compliance.check` with the facility's boarding rules on its truth. It raises if the result doesn't match the target. A wrong benchmark should never be written.

### D3. Versions side by side
- **Folders:** v1 stays exactly where it is (`evals/certificates/`). v2 goes in `evals/certificates/v2/`.
- **Version field:** v2's truth file carries `"version": "v2"`. v1's truth file has no version field, and is read as `v1` rather than edited.
- **Command line:** both scripts take an optional version argument. Generation and evaluation default to `v2`.
- **Reports:** reports record `benchmark.version`, built by a pure `build_report()` function so it can be tested.

## Risks / Trade-offs

- [Constructed dates look less "natural" than random ones] → Field-reading difficulty comes from the layouts and variants, which are unchanged. The construction only controls *which* dates matter.
- [Different seeds mean v1 and v2 numbers aren't directly comparable] → Every report names its benchmark version, and comparisons are made within one version.
