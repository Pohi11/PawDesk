# Spec Delta

## ADDED Requirements

### Requirement: Every Try preview opens with a summary
Every preview on the Try page, of a sample or a generated request, SHALL open with the same summary: the pet, service, and dates, then the owner, the pet's breed and weight when known, and what the vaccine card shows. The page SHALL open with "Make one up" selected and a generated request in the preview.

#### Scenario: Opens on Make one up
- **WHEN** the visitor opens the Try page
- **THEN** "Make one up" is selected and the preview shows a generated request

#### Scenario: A sample's summary
- **WHEN** the visitor chooses the clean boarding sample
- **THEN** the preview opens with Biscuit, boarding, and the dates, then the owner, breed, weight, and that every vaccine on the card is current
