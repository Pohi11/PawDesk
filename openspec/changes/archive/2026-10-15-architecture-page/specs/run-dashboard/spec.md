# Spec Delta

## ADDED Requirements

### Requirement: The architecture page shows how the system works
The dashboard SHALL have an Architecture page at `/architecture`, linked from the navigation. It SHALL draw the system's parts and their connections, a request's path through the agents and checks, the lifecycle states, the step loop, what a model's output passes before code uses it, and how tracing records each step. Each diagram SHALL have a name and a text equivalent. The page SHALL not scroll sideways at phone width.

#### Scenario: Opening the page from the navigation
- **WHEN** a visitor follows the navigation's Architecture link
- **THEN** the browser opens `/architecture`, which shows the six diagrams by name

#### Scenario: Diagrams in words
- **WHEN** a screen reader reaches a diagram
- **THEN** it announces the diagram's name and a description that names the same parts and connections

#### Scenario: Phone width
- **WHEN** a visitor opens the page 375 pixels wide
- **THEN** the page doesn't scroll sideways, and a wide diagram scrolls inside its own frame

### Requirement: The architecture page's lifecycle matches the backend
The lifecycle diagram's transitions, the actor allowed on each, and the states that can fail SHALL match the backend's lifecycle rules. The step loop's table SHALL match the orchestrator's map from state to step. Every transition in the page's data SHALL have an arrow in the diagram.

#### Scenario: Transitions match the lifecycle rules
- **WHEN** the page's transitions and failable states are compared with the backend's allowed transitions and failable states
- **THEN** they match

#### Scenario: Steps match the orchestrator
- **WHEN** the page's state-to-step table is compared with the orchestrator's step map
- **THEN** each state names the same step function

#### Scenario: Every transition is drawn
- **WHEN** the page's transitions are compared with the arrows the diagram draws
- **THEN** each transition has exactly one arrow, and each arrow is a transition
