# Spec Delta

## ADDED Requirements

### Requirement: The navigation's Try a request link opens the Try panel
The navigation's "Try a request" link SHALL go to the Try panel on the home page, from any page.

#### Scenario: Following the link on the home page
- **WHEN** a visitor on `/` follows the navigation's "Try a request" link
- **THEN** the page scrolls to the Try panel and its heading is in view

#### Scenario: Following the link from another page
- **WHEN** a visitor on `/requests` follows the navigation's "Try a request" link
- **THEN** the home page opens scrolled to the Try panel, with its heading in view
