# Proposal

## Why

The source code is public on GitHub, and PawDesk is one project in a wider portfolio. A visitor to the dashboard has no way to reach either from the page.

## What Changes

- **Two links at the right end of the navigation bar:** "Source code", to the GitHub repository, and "Portfolio", to https://pohi.me/.
- **Both open in a new tab,** so the dashboard (and any live run on it) stays open, and each says so to screen readers.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the navigation links to the source code and the portfolio.

## Impact

- **Frontend:** `app/layout.tsx`.
- **Tests:** an end-to-end test for both links' addresses and new-tab behavior.
