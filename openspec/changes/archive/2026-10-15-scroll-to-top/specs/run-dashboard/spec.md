# Spec Delta

## ADDED Requirements

### Requirement: Long pages offer a way back to the top
Every dashboard page SHALL show a "Back to top" button once the visitor has scrolled further than one window height, and SHALL hide it again above that point. Pressing the button SHALL scroll the page to the top, smoothly unless the visitor's system asks for reduced motion. While hidden, the button SHALL not be reachable by keyboard or by assistive technology.

#### Scenario: At the top of the page
- **WHEN** a visitor opens a page and has not scrolled
- **THEN** no "Back to top" button is visible or focusable

#### Scenario: Scrolled past the first screen
- **WHEN** a visitor scrolls further than one window height
- **THEN** the "Back to top" button appears in the bottom right corner

#### Scenario: Pressing the button
- **WHEN** a visitor presses "Back to top"
- **THEN** the page scrolls to the top and the button hides

#### Scenario: Reduced motion
- **WHEN** the visitor's system asks for reduced motion and they press "Back to top"
- **THEN** the page jumps to the top without a smooth scroll
