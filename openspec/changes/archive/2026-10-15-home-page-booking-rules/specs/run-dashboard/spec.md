# Spec Delta

## ADDED Requirements

### Requirement: The home page explains the booking rules
The home page SHALL explain the rules code checks: for each service, how long a visit lasts, whether it needs a kennel, and the vaccines dogs and cats need; when a vaccine covers a stay; how a dog's weight sets its kennel size; which dates a request can ask for; and what happens when a rule isn't met. The vaccine lists, weight bands, and booking horizon SHALL match the ones the backend uses.

#### Scenario: Services side by side
- **WHEN** a visitor reads the booking rules
- **THEN** boarding shows at least one night and a kennel, daycare and grooming show a single day and no kennel, and each shows its vaccines for dogs and cats

#### Scenario: The rules match the backend
- **WHEN** the rule data the page reads is compared with the seeded facility's vaccine rules, the size class thresholds, and the booking horizon
- **THEN** they match
