# Spec Delta

## ADDED Requirements

### Requirement: The Try panel is ready again after a run
After the visitor sends a request from the Try panel and its run opens, coming back to the home page SHALL show the panel ready to send again: the send button SHALL read "Send and watch it run" and be enabled, whether the visitor comes back with the browser's Back button or the navigation's "Try a request" link.

#### Scenario: Back from a run
- **WHEN** the visitor sends the clean boarding sample, its run opens, and the visitor goes back with the browser's Back button
- **THEN** the send button reads "Send and watch it run" and is enabled, and no button reads "Sending"

#### Scenario: The Try link from a run
- **WHEN** the visitor sends the clean boarding sample, its run opens, and the visitor clicks the navigation's "Try a request" link
- **THEN** the send button reads "Send and watch it run" and is enabled, and no button reads "Sending"
