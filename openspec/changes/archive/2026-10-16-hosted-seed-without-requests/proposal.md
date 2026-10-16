# Proposal

## Why

Every start of the hosted demo runs the seed, and the seed adds five example booking requests (Juniper, Pepper, Tofu, Moose, Biscuit) with their history. On the public demo these look like real activity: the review queue opens with Pepper waiting, and the request list shows runs no visitor made. The demo should open with an empty desk, so the only requests on it are the ones visitors send.

The rest of the seed is still needed there. The facility, its vaccine rules and kennels are what the checks run against, and the owners and pets are the clients that incoming messages are matched to; the Try page's samples are written about them.

## What Changes

- **The seed command can leave out booking requests.** `python -m scripts.seed --no-requests` loads the same facility, rules, kennels, owners, pets, vaccine records, and reservations, and no booking requests, transitions, or approvals.
- **The hosted demo seeds without requests.** The Space's start script passes `--no-requests`, so each start leaves the review queue and request list empty.
- Local development and the tests keep the full seed, example requests included.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `seed-data`: the seed command can load the dataset without booking requests.
- `demo-hosting`: the hosted demo starts with no booking requests.

## Impact

- **Backend:** `backend/scripts/seed.py`.
- **Deploy:** `deploy/huggingface/start.sh`, the Space README, and the main README's hosting notes.
- **Tests:** seed tests for the option and a test that the start script uses it.
- **Hosted demo:** redeployed; it starts with no requests.
