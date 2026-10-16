# Spec Delta

## MODIFIED Requirements

### Requirement: The worked example shows the attached vaccine card
The home page's worked example SHALL be labeled as an example. It SHALL show the vaccine card image the clean sample sends, between the pet parent's message and the facts code checked, marked as input a model read. The card SHALL first show as a short preview that a visitor can expand to the full card and collapse again.

#### Scenario: The card in the worked example
- **WHEN** a visitor opens `/`
- **THEN** the worked example shows Biscuit's vaccine card image, and the image loads

#### Scenario: The example is labeled
- **WHEN** a visitor opens `/`
- **THEN** the worked example's first line says it is an example request

#### Scenario: Expanding the card
- **WHEN** a visitor expands the card in the worked example
- **THEN** the full card shows, and the control says it will collapse the card

## ADDED Requirements

### Requirement: The worked example shows what PawDesk did
The worked example SHALL end with the outcome of the clean sample's run: that it booked a medium kennel for the stay and sent the reply with no one on staff involved, then the reply's subject and first paragraph. The rest of the reply SHALL open on demand. The reply SHALL be the one the clean sample's recorded run sends.

#### Scenario: The outcome
- **WHEN** a visitor opens `/`
- **THEN** the worked example says a medium kennel was booked, shows the Sent tag, and shows the reply's subject and first paragraph

#### Scenario: The full reply
- **WHEN** a visitor opens the rest of the reply
- **THEN** the whole reply shows, ending with its sign-off

#### Scenario: The quoted reply is the real one
- **WHEN** the clean sample runs on its recorded responses
- **THEN** the reply it sends has the same subject and first paragraph as the worked example
