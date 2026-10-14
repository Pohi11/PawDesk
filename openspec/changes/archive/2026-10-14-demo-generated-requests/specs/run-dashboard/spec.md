# Spec Delta

## ADDED Requirements

### Requirement: The Try page previews a request and its certificate
The Try page SHALL let the visitor generate a random request, and show its message (editable), its scenario in plain words, and its certificate image before sending. A new request can be generated at any time. Fixed samples SHALL show their certificate too, when they have one.

#### Scenario: Generate and preview
- **WHEN** the visitor generates a request
- **THEN** the page shows the generated message, the scenario, and the certificate image for that request's seed

#### Scenario: Send a generated request
- **WHEN** the visitor sends a generated request
- **THEN** it is submitted by its seed, and the browser opens its live run view

## MODIFIED Requirements

### Requirement: The backend is reached only through an allowlisted proxy
The browser SHALL reach the backend only through the dashboard's own route. The route SHALL forward only these paths:
- `GET` for requests, reviews, metrics, evals, demo samples, generated demo requests, and demo certificate images;
- `POST` for staff actions and demo submissions.

Everything else SHALL be refused with 404. The backend address SHALL NOT appear in browser code.

#### Scenario: Allowed path
- **WHEN** the browser asks for `GET /api/requests/<id>/events`
- **THEN** the route forwards it and streams the response through

#### Scenario: Refused path
- **WHEN** the browser asks for `GET /api/health/db` or `DELETE /api/requests/<id>`
- **THEN** the route answers 404 without contacting the backend

#### Scenario: Certificate images pass through
- **WHEN** the browser asks for `GET /api/demo/generated/42/certificate.png`
- **THEN** the route forwards it and returns the image unchanged

#### Scenario: No backend address in client code
- **WHEN** the client components are checked
- **THEN** none of them reads the backend address
