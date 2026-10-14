# Spec Delta

## ADDED Requirements

### Requirement: Path steps explain themselves
Hovering or focusing a step in the run view's path SHALL show a tooltip with what the step does and, once the step has run, a one-line summary of its result for this request. A step that is skipped or has not run SHALL say so. The summary SHALL come only from the request detail already loaded, and SHALL update as the run does.

#### Scenario: A finished step
- **WHEN** the visitor hovers the Compliance step of a request whose Bordetella record expired before the stay
- **THEN** the tooltip says what the compliance check does, and that Bordetella expired

#### Scenario: A step that did not run
- **WHEN** the visitor hovers the Staff review step of a request sent without review
- **THEN** the tooltip says what staff review is for, and that this request did not need it

#### Scenario: Keyboard
- **WHEN** the visitor tabs to a step
- **THEN** the same tooltip is shown and announced as the step's description, Escape hides it, and Enter opens the step in the inspector
