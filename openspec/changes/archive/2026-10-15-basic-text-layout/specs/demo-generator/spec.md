# Spec Delta

## ADDED Requirements

### Requirement: Cards draw the same on every machine
Card drawing SHALL lay out all text with Pillow's basic layout engine, so a card's pixels do not depend on whether the machine has an optional text-shaping library such as Raqm.

#### Scenario: Fonts use basic layout
- **WHEN** the card's fonts are loaded
- **THEN** each one uses the basic layout engine

#### Scenario: Raqm installed
- **WHEN** a sample's card is drawn on a machine where Raqm is available
- **THEN** its pixels match the committed card
