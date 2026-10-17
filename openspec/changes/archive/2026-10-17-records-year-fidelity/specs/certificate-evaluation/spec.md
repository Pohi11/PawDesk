# Spec Delta

## ADDED Requirements

### Requirement: Sample cards are read repeatedly to measure misreads
An evaluation SHALL read each fixed sample's card a set number of times with the live records step, as of the demo day, and compare every read with the dates printed on the card. Per card and in total, its report SHALL count reads, failed reads, reads with any date misread, decision flips (the card's records alone give a different compliance outcome for the stay than the printed dates), and silent flips (flips the records step left `clear`).

#### Scenario: A silent flip
- **WHEN** a read is a decision flip and the records step's outcome for it is `clear`
- **THEN** that read counts as a silent flip

#### Scenario: A shifted year is a misread
- **WHEN** a card prints Bordetella given 2026-10-12 and a read returns 2024-10-12
- **THEN** that read counts as a misread

#### Scenario: Exact read
- **WHEN** a read returns every printed vaccine with the printed dates
- **THEN** that read counts as neither a misread nor a decision flip

#### Scenario: A misread that changes the decision
- **WHEN** the printed dates make the clean sample compliant for its stay and a read's dates make it not compliant
- **THEN** that read counts as a decision flip

#### Scenario: Report names what it measured
- **WHEN** a sample-card report is built
- **THEN** it records the prompt version, the model, the number of reads per card, and the total cost
