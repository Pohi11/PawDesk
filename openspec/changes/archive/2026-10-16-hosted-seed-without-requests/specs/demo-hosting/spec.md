# Spec Delta

## ADDED Requirements

### Requirement: The hosted demo starts with no booking requests
Each start of the hosted demo SHALL reseed the database without booking requests, so the review queue and the request list hold only requests sent since that start.

#### Scenario: Start script seeds without requests
- **WHEN** the Space's start script is read
- **THEN** it runs the seed command with `--no-requests`
