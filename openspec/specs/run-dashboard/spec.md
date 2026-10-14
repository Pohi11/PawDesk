# run-dashboard Specification

## Purpose
The operator dashboard: watch a run live as a graph and a timeline, inspect any span, decide flagged requests, follow cost, latency, and eval results, and submit demo requests. It is served without exposing the backend to the browser.

## Requirements

### Requirement: The run graph shows each step's status and kind
The run view SHALL draw the workflow as a graph:
- **Nodes:** intake, records, compliance, capacity, route, resolver, reply, review, and send.
- **Status:** each node SHALL show `waiting`, `running`, `ok`, `error`, or `skipped`, derived from the request's spans and state.
- **Kind:** each node SHALL be colored by its kind (model, code, tool, or human).

#### Scenario: Parallel steps running
- **WHEN** the intake and records spans are both running
- **THEN** both nodes show `running`

#### Scenario: Skipped resolver
- **WHEN** a request was routed straight to drafting
- **THEN** the resolver node shows `skipped`

#### Scenario: Waiting for review
- **WHEN** a request is in `needs_review`
- **THEN** the review node shows `running` and the send node shows `waiting`

### Requirement: The timeline shows overlapping steps
The timeline SHALL place every span of a trace as a bar positioned by its start and end relative to the trace's first span, indented by its depth in the span tree. A span still running SHALL extend to the current time.

#### Scenario: Concurrent spans overlap
- **WHEN** intake ran from 0.1 s to 4.6 s and records from 0.2 s to 3.0 s
- **THEN** their bars overlap on the timeline

#### Scenario: Nesting
- **WHEN** a model span is a child of the intake span
- **THEN** it is drawn one level deeper than the intake span

### Requirement: The backend is reached only through an allowlisted proxy
The browser SHALL reach the backend only through the dashboard's own route. The route SHALL forward only these paths:
- `GET` for requests, reviews, metrics, evals, and demo samples;
- `POST` for staff actions and demo submissions.

Everything else SHALL be refused with 404. The backend address SHALL NOT appear in browser code.

#### Scenario: Allowed path
- **WHEN** the browser asks for `GET /api/requests/<id>/events`
- **THEN** the route forwards it and streams the response through

#### Scenario: Refused path
- **WHEN** the browser asks for `GET /api/health/db` or `DELETE /api/requests/<id>`
- **THEN** the route answers 404 without contacting the backend

#### Scenario: No backend address in client code
- **WHEN** the client components are checked
- **THEN** none of them reads the backend address

### Requirement: Operators can review, measure, and demo from the dashboard
The dashboard SHALL provide:
- a review queue page showing each waiting request's flag reasons and draft, with approve, edit and approve, and reject (with a reason);
- a metrics page charting cost per step, flag rate, and run duration;
- an evals page listing every report;
- a demo page that submits a sample and opens its live run view.

#### Scenario: Span inspector formatting
- **WHEN** a model span with tokens, cost, and latency is selected
- **THEN** the inspector shows its tokens, its cost in dollars, and its duration in seconds

#### Scenario: Demo opens the live view
- **WHEN** a sample is submitted from the demo page
- **THEN** the browser navigates to that request's live run view
