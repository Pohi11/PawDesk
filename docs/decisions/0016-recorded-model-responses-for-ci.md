# 0016 — End-to-end tests replay recorded model responses

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

The demo (submit a request, watch it run, approve a flagged one) is the most important path through PawDesk. Until now it was checked only by hand in a browser. Running it automatically on every push means running the real backend and dashboard, and the backend calls a language model at several steps (intake, records, reply). In CI a real model call:
- costs money on every push;
- needs the provider key as a CI secret;
- fails when the provider is down;
- can answer differently from run to run, which makes the test flaky.

Model quality is already measured separately, on demand, by the evals (decision record 0007).

## Options considered

1. **Call the real model in CI.** It's the most realistic option, but it has every problem above, and a test that fails because the model changed its wording tells us nothing about our code.
2. **Mock at the function level** (fake `run_intake`, `draft_reply`). Deterministic, but it skips the real client: the retries, spans, cost recording, and schema validation that the demo depends on.
3. **A fake model server** that answers by rules. Deterministic, but its answers are invented, and someone has to keep them plausible as prompts change.
4. **Record real responses once, then replay them at the HTTP layer.** A transport under the model client saves each response body under a hash of the exact request, and replays it later without the network. Everything above the transport runs for real.

## Decision

Option 4.
- **The transport:** `app/cassettes.py`, selected by the settings `llm_cassette_mode` (`off`, `record`, `replay`) and `llm_cassette_dir`.
- **What's stored:** only response bodies, keyed by the request body's SHA-256. Request bodies (with images) and headers (with the key) are never written.
- **A missing recording is a permanent error** that names the request hash, so any change to a prompt, schema, or input shows up as a failing end-to-end test until the responses are re-recorded.
- **Recording** is one command (`PAWDESK_E2E_RECORD=1 pnpm e2e`) and makes a handful of real calls. CI only replays. Its workflow holds a placeholder key, and a test checks that no model secret is referenced.

## Consequences

- **Good:** CI is free, deterministic, and offline from the model's point of view, and the full stack is still exercised (real client, real traces, real database, real browser).
- **Good:** Recording against the real model exposed a bug that scripted tests had missed. The provider's responses are gzip-compressed, and the recorder first passed decoded bodies on with their compression header. It's now covered by a regression test.
- **Cost:** The recordings have to be re-made after prompt or schema changes. The failure names exactly which request changed.
- **Cost:** Replay proves the plumbing and the flow, not the model's quality. The evals remain the measure of that, and are rerun on model or prompt changes.
