# Spec Delta

## Purpose

Provides a repeatable, ground-truth-labeled set of synthetic vaccine certificates and an evaluation that measures how accurately the records step reads them, and how often reading errors would change a compliance decision.

## ADDED Requirements

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
