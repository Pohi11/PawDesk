# Spec Delta

## ADDED Requirements

### Requirement: The home page describes PawDesk as a hybrid workflow
The home page introduction SHALL describe PawDesk as a hybrid workflow, in which code runs the steps in a fixed order and agents are used only where the input is messy. It SHALL NOT call PawDesk a multi-agent workflow.

#### Scenario: Reading the introduction
- **WHEN** a visitor reads the home page introduction
- **THEN** it calls PawDesk a hybrid workflow, says code runs the steps in a fixed order, and doesn't say "multi-agent"
