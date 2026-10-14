# Spec Delta

## ADDED Requirements

### Requirement: Requests identify the matched pet
The request list and the request detail SHALL report the matched pet's id, species, and breed alongside its name. When no pet is matched, all four SHALL be null.

#### Scenario: Matched pet
- **WHEN** a request matched to Biscuit, a dog whose breed is "Beagle", is listed and inspected
- **THEN** both responses include Biscuit's pet id, species `dog`, and breed `Beagle`

#### Scenario: No matched pet
- **WHEN** a request with no matched pet is listed and inspected
- **THEN** both responses report the pet's name, id, species, and breed as null
