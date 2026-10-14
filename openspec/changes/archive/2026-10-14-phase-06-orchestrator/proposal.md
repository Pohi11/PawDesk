# Proposal

## Why

PawDesk now has every building block of a booking decision: intake reads the message, records reads the certificate, compliance and capacity decide. But nothing runs them together. Running them together raises the hard questions of real systems. What runs in parallel? What happens when the process dies halfway through a run that has already paid for two model calls? How do we avoid repeating, or doubling, work after a restart? The orchestrator answers these with plain code: a fixed workflow, not an LLM deciding what to do next. That keeps every booking's path predictable, testable, and safe to resume.

## What Changes

- Store a certificate image with a booking request (one per request, with the same type and size limits as the records step).
- Add an orchestrator that drives a request from `received` through extraction and checks:
  - **Extraction:** intake and records run concurrently.
  - **Checks:**
    - the certificate's pet name is compared with the pet intake matched;
    - compliance combines the pet's records on file with the extracted ones;
    - capacity looks for a kennel of the pet's size class for boarding.
  - **Routing:** the request moves to `drafting` when everything is clear, or to `resolving` with a list of reasons.
- Make execution durable:
  - each step's result is saved in the same transaction as its state change;
  - a step whose result is already saved is never run again;
  - a request interrupted mid-run resumes from its last saved step.
- Step failures move the request to `failed`, keeping the error. A retry resumes at the failed step.
- On resume, spans left `running` by a process that died are closed as abandoned.
- Add command-line entry points: submit a request with a certificate, process one request, and resume interrupted requests.
- Record two decisions: why PawDesk is a hybrid workflow rather than a fully agentic system, and how durable execution works.

## Capabilities

### New Capabilities
- `booking-orchestration`: Running a booking request's steps in order (with concurrent extraction), saving each step durably, resuming after a crash without repeating finished work, handling step failures, and routing to the next stage.

### Modified Capabilities
- `booking-domain`: adds a requirement for storing a certificate image with a booking request.
- `run-tracing`: adds a requirement for closing spans abandoned by a process that stopped.

## Impact

- **Backend:**
  - new tables `booking_documents` (certificate image bytes, hash, type) and `booking_step_results` (one saved result per request and step);
  - new `app/orchestrator.py`;
  - new `scripts/bookings.py` (command-line submit, process, resume).
- **Tests:** orchestration is tested with scripted model answers, including a simulated crash between steps and the resume that follows. One real end-to-end run and one real process kill are performed from the command line, and their outcomes recorded.
- **Out of scope:**
  - the resolver (Phase 7) and the reply and approval steps (Phase 8): requests stop at `resolving` or `drafting`;
  - running several worker processes at once (leases);
  - writing extracted records into `vaccine_records` (after human approval, Phase 8);
  - reserving kennels.
