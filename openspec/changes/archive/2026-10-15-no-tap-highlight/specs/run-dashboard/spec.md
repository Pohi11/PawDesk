# Spec Delta

## ADDED Requirements

### Requirement: Tapping on a touch screen draws no highlight
The dashboard SHALL NOT draw the browser's tap highlight on any element. On a device whose main pointer is a finger, a tapped text field, menu, or radio SHALL NOT draw a focus outline. A visitor who moves focus with the keyboard SHALL still see the focus outline on every control.

#### Scenario: Tapping a button on a phone
- **WHEN** a visitor taps a button on a phone
- **THEN** no tap highlight is drawn over it

#### Scenario: Tapping a text field on a phone
- **WHEN** a visitor taps the request text box on a phone
- **THEN** the text box has focus and no focus outline

#### Scenario: Moving with the keyboard
- **WHEN** a visitor on a desktop presses Tab to reach a control
- **THEN** the control shows the focus outline
