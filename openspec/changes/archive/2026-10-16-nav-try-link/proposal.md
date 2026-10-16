# Proposal

## Why

The navigation's "Try a request" link opens the top of the home page. The Try panel sits below the introduction and the worked example, so a visitor who follows the link still has to scroll to find it.

## What Changes

- **The navigation's "Try a request" link goes to `/#try`,** so it scrolls to the Try panel from any page, the home page included.
- **The empty requests list's "Try a request" button goes there too,** for the same reason.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the navigation's Try a request link opens the Try panel.

## Impact

- **Frontend:** `app/layout.tsx`, `app/requests/page.tsx`.
- **Tests:** end-to-end tests for the link from the home page and from another page.
