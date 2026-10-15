# Spec Delta

## ADDED Requirements

### Requirement: The home page introduces PawDesk and holds the Try panel
The home page (`/`) SHALL open with a plain-language description of what PawDesk does, followed by the Try panel. Below the panel it SHALL describe how a request moves through the steps, the dashboard's other pages, why the project was built, and the technologies it uses. `/demo` SHALL redirect to the home page, and the requests list SHALL be at `/requests`.

#### Scenario: Opening the home page
- **WHEN** a visitor opens `/`
- **THEN** the page says what PawDesk does and shows the Try panel's samples and its "Make one up" choice

#### Scenario: The old Try page address
- **WHEN** a visitor opens `/demo`
- **THEN** the browser lands on `/`

#### Scenario: The requests list
- **WHEN** a visitor follows the navigation's Requests link
- **THEN** the browser opens `/requests`, which lists the requests

## MODIFIED Requirements

### Requirement: Operators can review, measure, and demo from the dashboard
The dashboard SHALL provide:
- a requests list page linking each request to its run view;
- a review queue page showing each waiting request's flag reasons and draft, with approve, edit and approve, and reject (with a reason);
- a metrics page charting cost per step, flag rate, and run duration;
- an evals page listing every report;
- a Try panel on the home page that submits a sample and opens its live run view.

#### Scenario: Span inspector formatting
- **WHEN** a model span with tokens, cost, and latency is selected
- **THEN** the inspector shows its tokens, its cost in dollars, and its duration in seconds

#### Scenario: Demo opens the live view
- **WHEN** a sample is submitted from the Try panel
- **THEN** the browser navigates to that request's live run view
