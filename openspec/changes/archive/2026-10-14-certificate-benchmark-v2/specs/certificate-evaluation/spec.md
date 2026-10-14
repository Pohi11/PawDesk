# Spec Delta

## ADDED Requirements

### Requirement: Reference decisions are balanced
From benchmark v2 on, the correct compliance outcome for the reference stay SHALL be mixed:
- neither `compliant` nor `not_compliant` covers more than 60% of the certificates;
- at least 4 certificates are `needs_review`;
- at least 4 are `compliant` because a required vaccine expires exactly on checkout day;
- at least 4 are `not_compliant` because a required vaccine expires the day before checkout.

#### Scenario: Decision mix
- **WHEN** the v2 ground truth is evaluated with the compliance check for the reference stay
- **THEN** no single outcome exceeds 60% of the certificates and at least 4 are `needs_review`

#### Scenario: Boundary coverage
- **WHEN** the v2 ground truth is inspected
- **THEN** at least 4 compliant certificates have a required vaccine expiring on checkout day, and at least 4 not-compliant certificates have one expiring the day before checkout

#### Scenario: Generator verifies its targets
- **WHEN** the v2 generator produces a certificate meant to be `compliant`
- **THEN** the compliance check on its ground truth returns `compliant`, or generation fails

### Requirement: Benchmark versions are kept side by side
Each benchmark version SHALL live in its own folder with its own images and truth file, and the truth file SHALL name its version. Generating a new version SHALL NOT change an earlier one. Evaluation reports SHALL name the benchmark version they ran on, and evaluation SHALL default to the newest version.

#### Scenario: v1 is unchanged
- **WHEN** v2 is added
- **THEN** the committed v1 truth still equals what the v1 generator produces, and every v1 image is still present

#### Scenario: Report names its benchmark
- **WHEN** an evaluation report is built for v2
- **THEN** it records benchmark version `v2`
