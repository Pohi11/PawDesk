# Proposal

## Why

The home page, the build walkthrough, and a run page with many steps are long. A visitor who has read to the bottom has to scroll the whole way back to reach the navigation or the Try panel.

## What Changes

- **A "Back to top" button** sits in the bottom right corner of every dashboard page once the visitor has scrolled past the first screen, and hides again near the top.
- **A ring around the button fills as the visitor scrolls,** so it also shows how far down the page they are.
- **Pressing it scrolls smoothly to the top,** or jumps there at once when the visitor's system asks for reduced motion.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: long pages offer a way back to the top.

## Impact

- **Frontend:** a new client component `components/back-to-top.tsx`, placed once in `app/layout.tsx`.
- **Tests:** an end-to-end test for showing, hiding, and using the button, with and without reduced motion.
