# Proposal

## Why

The Try panel sometimes ignores a sample the visitor just chose. The page opens on "Make one up" and makes up a request as soon as it is interactive. That first request also selects "Make one up", so a sample chosen in the moment before it starts is switched back. Sending then submits the made-up request instead of the sample. The end-to-end tests choose a sample right after the page loads, and on GitHub Actions they failed this way on most recent runs: the clean sample's checks never passed, because a made-up request with no recorded responses was sent instead. A trace of a local failure shows the click finishing as the first made-up request starts.

## What Changes

- **Making up the opening request leaves the choice alone.** The page already starts with "Make one up" selected, so the automatic first request only fills the preview. Choosing "Make one up" or "Make another" still selects it.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: a sample chosen while the opening request is being made up stays chosen.

## Impact

- **Frontend:** `components/demo-panel.tsx`.
- **Tests:** an end-to-end test that chooses a sample while the opening request is still being made up.
