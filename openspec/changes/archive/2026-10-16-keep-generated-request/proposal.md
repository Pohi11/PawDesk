# Proposal

## Why

On the Try page, clicking the "Make one up" choice always makes up a new request, even when one is already in the preview. A visitor who looks at a sample and then goes back to "Make one up" loses the request they were reading, along with any edits to its message, and each click uses up another pet name. The made-up request should stay put until the visitor asks for a new one.

## What Changes

- **Choosing "Make one up" shows the request already made up.** It only makes one up when none exists yet, for example when the opening request failed.
- **"Make another" is the way to get a new request,** and reloading the page still opens on a new one.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: choosing "Make one up" again keeps the current generated request.

## Impact

- **Frontend:** `components/demo-panel.tsx`.
- **Tests:** an end-to-end test that goes to a sample and back, then asks for another.
