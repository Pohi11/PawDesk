# Spec Delta

## MODIFIED Requirements

### Requirement: The Try page previews a request and its certificate
The Try page SHALL let the visitor generate a random request, and show its message (editable), its scenario in plain words, and its certificate image before sending. A new request can be generated at any time. Each generation SHALL send the pet names generated earlier in this browser session, the latest 10, so the next name is fresh. Fixed samples SHALL show their certificate too, when they have one. Every preview, of a sample or a generated request, SHALL open with the same summary: the pet, service, and dates, then the owner, the pet's breed and weight when known, and what the vaccine card shows. The page SHALL open with "Make one up" selected and a generated request in the preview.

#### Scenario: Generate and preview
- **WHEN** the visitor generates a request
- **THEN** the page shows the generated message, the scenario, and the certificate image for that request's seed

#### Scenario: Send a generated request
- **WHEN** the visitor sends a generated request
- **THEN** it is submitted by its seed, and the browser opens its live run view

#### Scenario: Recent names go with each generation
- **WHEN** the visitor generates a request after generating Juno and Pickle
- **THEN** the page asks for the new request with Juno and Pickle as names to avoid

#### Scenario: Opens on Make one up
- **WHEN** the visitor opens the Try page
- **THEN** "Make one up" is selected and the preview shows a generated request

#### Scenario: A sample's summary
- **WHEN** the visitor chooses the clean boarding sample
- **THEN** the preview opens with Biscuit, boarding, and the dates, then the owner, breed, weight, and that every vaccine on the card is current
