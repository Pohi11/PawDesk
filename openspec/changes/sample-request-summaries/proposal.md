# Proposal

## Why

On the Try page, a generated request's preview opens with a summary: the pet, service, and dates as a heading, then the owner, breed, weight, and what the vaccine card shows. The fixed samples show only the message, so a visitor has to read it to learn what the request is, and can't see what the card is meant to show before sending. The page also opens on the first sample, while "Make one up" is the choice that shows something new on each visit.

## What Changes

- **Each sample's preview opens with the same summary** as a generated request: pet, service, and dates, then the owner, the pet's breed and weight when on file, and what the vaccine card shows.
- **The samples list from the API carries each sample's service, dates, owner name, the pet's weight, and a card summary** in plain words.
- **"Make one up" is selected when the Try page opens,** and a request is generated right away so the preview isn't empty.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `demo-generator`: samples carry a request summary.
- `run-dashboard`: the Try page shows the summary for samples too and opens on "Make one up".

## Impact

- **Backend:** `app/demo.py` (each sample's service, dates, and card summary; the owner is looked up with the pet) and `app/api.py` (`GET /demo/samples` returns them).
- **Frontend:** `components/demo-panel.tsx` (one summary block for both kinds, the default choice, a generation on open) and `lib/types.ts`.
- **Tests:** an API test for the summary fields, and end-to-end checks of the default choice and a sample's summary.
