## ADDED Requirements

### Requirement: Demo cards are marked synthetic in metadata
A demo card, generated or a fixed sample's, SHALL NOT draw any text saying it is a demo or not a real record, because the records step reads every line of the card. Each demo card SHALL carry a PNG text chunk `Comment` saying it is a synthetic PawDesk demo certificate with a fictional pet, owner, clinic, and veterinarian.

#### Scenario: Nothing below the signature
- **WHEN** the card for seed 42 is drawn
- **THEN** the area below the "Attending veterinarian" label is blank paper

#### Scenario: Marked in metadata
- **WHEN** the card for seed 42, or any fixed sample's card, is read as a PNG
- **THEN** its `Comment` text says it is a synthetic PawDesk demo certificate
