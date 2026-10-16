# Spec Delta

## MODIFIED Requirements

### Requirement: Every Try preview opens with a summary
Every preview on the Try page, of a sample or a generated request, SHALL open with the same summary: the pet, service, and dates, then the owner, the pet's breed and weight when known, and what the vaccine card shows. The page SHALL open with "Make one up" selected and a generated request in the preview. Making up that opening request SHALL NOT change the visitor's choice. Choosing "Make one up" SHALL show the request already made up; only "Make another" or a page load SHALL make up a new one.

#### Scenario: Opens on Make one up
- **WHEN** the visitor opens the Try page
- **THEN** "Make one up" is selected and the preview shows a generated request

#### Scenario: A sample's summary
- **WHEN** the visitor chooses the clean boarding sample
- **THEN** the preview opens with Biscuit, boarding, and the dates, then the owner, breed, weight, and that every vaccine on the card is current

#### Scenario: A sample chosen while the opening request is made up
- **WHEN** the visitor chooses the clean boarding sample before the opening generated request has arrived, and then sends
- **THEN** the clean sample stays chosen after the generated request arrives, and the clean sample is the request sent

#### Scenario: Going back to Make one up keeps the request
- **WHEN** the visitor chooses a sample and then chooses "Make one up" again
- **THEN** the preview shows the same generated request as before, and no new one is made up

#### Scenario: Make another makes a new request
- **WHEN** the visitor clicks "Make another"
- **THEN** a new generated request is made up
