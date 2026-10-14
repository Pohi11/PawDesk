# certificate-evaluation Specification

## Purpose

Provides a repeatable, ground-truth-labeled set of synthetic vaccine certificates and an evaluation that measures how accurately the records step reads them, and how often reading errors would change a compliance decision.

## Requirements

### Requirement: Certificates are generated with ground truth
A generator SHALL produce at least 30 certificate images, each saved with a ground-truth file holding the pet name, every printed record (label, vaccine, date given, expiry or empty), and the variant applied. Running the generator twice with the same seed SHALL produce identical ground truth.

#### Scenario: Ground truth is deterministic
- **WHEN** the ground truth is generated twice with the same seed
- **THEN** both results are identical

#### Scenario: Every image has ground truth
- **WHEN** the certificate set is loaded
- **THEN** there are at least 30 certificates, and each has an image file and a matching ground-truth entry

### Requirement: The set covers hard cases
The set SHALL include certificates in at least three layouts, plus blurred, rotated, handwriting-style, and missing-expiry variants, with at least four certificates of each variant.

#### Scenario: Variant coverage
- **WHEN** the certificate set's ground truth is loaded
- **THEN** each of the layouts and variants appears at least four times

### Requirement: Certificates are visibly synthetic
Every generated certificate SHALL use fictional clinic, veterinarian, and pet names, and SHALL visibly state that it is a synthetic test document.

#### Scenario: Synthetic marking
- **WHEN** a certificate's HTML is rendered
- **THEN** it contains the text "SYNTHETIC TEST DOCUMENT"

### Requirement: Evaluation reports field accuracy and invented expiries
The evaluation SHALL match extracted records to ground truth by vaccine and report:
- vaccine recall and precision;
- accuracy of the date given;
- accuracy of the expiry (an empty expiry counts as correct only when the ground truth is empty);
- accuracy of the pet name;
- the count of **invented expiries**, where the ground truth has no expiry but the extraction has one.

It SHALL also break the results down by variant.

#### Scenario: Scoring a partly wrong extraction
- **WHEN** the ground truth has rabies and DHPP, and the extraction has rabies with the wrong expiry, misses DHPP, and adds bordetella
- **THEN** vaccine recall is 1/2, precision is 1/2, and expiry accuracy is 0/1 over matched records

#### Scenario: Invented expiry
- **WHEN** the ground truth has no expiry for FVRCP and the extraction gives one
- **THEN** the report counts one invented expiry

### Requirement: Evaluation reports decision agreement
For each certificate, the evaluation SHALL compute the compliance outcome for a fixed reference stay twice, once from the ground truth and once from the extracted records, and report how often they agree.

#### Scenario: Error that changes the decision
- **WHEN** the ground truth makes a certificate `not_compliant` for the reference stay, but the extracted expiry makes it `compliant`
- **THEN** that certificate counts as a decision disagreement

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
