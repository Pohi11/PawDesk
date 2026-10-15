# Spec Delta

## MODIFIED Requirements

### Requirement: The home page introduces PawDesk and holds the Try panel
The home page (`/`) SHALL open with what PawDesk does, why it was built, its main features, and a worked request, then the Try panel. Below the panel it SHALL name each agent with what it reads, what it returns, and what code checks, then explain the steps, the guarantees the tests check, how the code is written, and which technologies serve each skill in the job posting. `/demo` SHALL redirect to `/`, and the requests list SHALL be at `/requests`.

#### Scenario: Opening the home page
- **WHEN** a visitor opens `/`
- **THEN** the page says what PawDesk does and why it was built, shows the worked example, and shows the Try panel's samples and its "Make one up" choice

#### Scenario: The agents
- **WHEN** a visitor reads the agents section
- **THEN** it names the intake, records, resolver, and reply agents, each with what it reads, what it returns, and what code checks

#### Scenario: The old Try page address
- **WHEN** a visitor opens `/demo`
- **THEN** the browser lands on `/`

#### Scenario: The requests list
- **WHEN** a visitor follows the navigation's Requests link
- **THEN** the browser opens `/requests`, which lists the requests
