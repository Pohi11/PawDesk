# Proposal

## Why

The coverage diagram in the booking rules section is labeled as Biscuit's stay, but its expiry dates are made up to show one passing and one failing shot. The worked example at the top of the page now shows Biscuit's real vaccine card, whose dates differ, so a reader comparing the two sees a contradiction.

## What Changes

- **The diagram describes a hypothetical dog** instead of Biscuit: its accessible name, the on-site lane, and the caption.
- **The dates and verdicts stay the same,** since they illustrate the rule, not a pet on file.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the booking rules' coverage diagram is a hypothetical example.

## Impact

- **Frontend:** `app/page.tsx`.
- **Tests:** the booking rules end-to-end test looks the diagram up by its new name.
