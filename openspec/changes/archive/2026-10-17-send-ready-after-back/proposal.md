# Proposal

## Why

Sending a request from the home page's Try panel opens its run. Coming back to the home page, with the browser's Back button or the navigation's "Try a request" link, shows the panel's buttons still disabled and labelled "Sending". The panel stays unusable until the page is reloaded, so a visitor can't try a second request.

## What Changes

- **The Try panel is ready again when the visitor comes back from a run.** The send button reads "Send and watch it run" and is enabled, and "Make another" is enabled.
- **Sending and making up a request are tracked apart,** so clearing one never interrupts the other.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: a new requirement that the Try panel is ready again after a run.

## Impact

- **Frontend:** `components/demo-panel.tsx`.
- **Tests:** end-to-end tests that send a sample, come back each way, and check the send button.
