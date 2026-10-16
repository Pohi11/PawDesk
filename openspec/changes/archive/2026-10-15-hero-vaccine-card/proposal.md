# Proposal

## Why

The worked request at the top of the home page says the pet parent sent "a photo attached", and the records agent reads that photo, but the example never shows it. A visitor sees the message the intake agent read and has to imagine the other half of the input.

## What Changes

- **The worked example shows the vaccine card** that the clean sample sends: Biscuit's certificate, between the message and the facts code checked.
- **The card is marked the same way as the message,** as something a model read, so the legend still explains every mark in the example.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: the home page's worked example includes the attached vaccine card.

## Impact

- **Frontend:** `app/page.tsx`.
- **Tests:** the home page end-to-end test checks that the card image is shown and loads.
