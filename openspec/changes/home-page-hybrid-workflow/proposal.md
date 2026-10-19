# Proposal

## Why

The home page introduction calls PawDesk a multi-agent workflow. It isn't one: plain code fixes the order of the steps, and models only read the messy input and write the reply (decision record 0008 chose a hybrid workflow over a multi-agent supervisor). The Space's short description says the same. A visitor who knows the patterns reads the wrong architecture before seeing the rest of the page.

## What Changes

- **The introduction calls PawDesk a hybrid workflow** and says what that means: code runs the steps in a fixed order and calls agents only where the input is messy.
- **The Space's short description** says "Hybrid workflow booking intake desk for pet care".

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: a new requirement that the home page describes PawDesk as a hybrid workflow.

## Impact

- **Frontend:** `app/page.tsx`.
- **Deploy:** `deploy/huggingface/README.md` front matter.
- **Tests:** a home page end-to-end test that checks the introduction's wording.
