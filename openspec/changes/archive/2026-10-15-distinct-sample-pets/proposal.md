# Proposal

## Why

The clean boarding sample and the prompt injection sample are both about Biscuit, so the Try page shows the same Beagle photo twice. Each sample should be about a different pet, so the choices are easy to tell apart and the photos differ.

## What Changes

- **The prompt injection sample is about Pepper**, a Chihuahua owned by Priya Venkataraman, instead of Biscuit. Its message names Pepper.
- **Its certificate names Pepper and is current**, so the planted instruction is the only reason the request goes to staff. The card is drawn by code when the sample is requested, because the benchmark images carry no card for Pepper.
- **No two samples share a pet.** A test pins this.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `observability-api`: every sample is about a different pet.

## Impact

- **Backend:** `app/demo.py` (the injection sample's owner, pet, message, and certificate).
- **Tests:** an API test that samples' pets are distinct and the injection sample's card names its pet; the end-to-end demo keeps passing.
