# Spec Delta

## MODIFIED Requirements

### Requirement: The home page introduces PawDesk and holds the Try panel
The home page (`/`) SHALL open with a plain-language description of what PawDesk does, why it was built, and its main features, beside a worked example of one request, followed by the Try panel. Below the panel it SHALL describe how a request moves through the steps, the guarantees the tests check, how the code is written, and which technologies serve each skill in the job posting, linking to the dashboard's other pages where it mentions them. `/demo` SHALL redirect to the home page, and the requests list SHALL be at `/requests`.

#### Scenario: Opening the home page
- **WHEN** a visitor opens `/`
- **THEN** the page says what PawDesk does and why it was built, shows the worked example, and shows the Try panel's samples and its "Make one up" choice

#### Scenario: The old Try page address
- **WHEN** a visitor opens `/demo`
- **THEN** the browser lands on `/`

#### Scenario: The requests list
- **WHEN** a visitor follows the navigation's Requests link
- **THEN** the browser opens `/requests`, which lists the requests
