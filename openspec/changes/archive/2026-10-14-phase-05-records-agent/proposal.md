# Proposal

## Why

Vaccine compliance is only as good as its inputs. Pet parents send photos of vaccine certificates, not structured records, and those photos are blurry, rotated, handwritten, or missing fields. Reading an image is a job for a vision model. But a wrong date silently turns into a wrong compliance decision, and an *invented* expiry date is the most dangerous error of all, because it can make an expired pet look covered. So extraction needs strict validation, explicit handoff to a person when in doubt, and above all **measurement**: an accuracy number from a repeatable evaluation, not an impression from a few demos.

## What Changes

- Add a records step that sends a certificate image to the vision model and returns validated vaccine records in the same `VaccineEvidence` shape the compliance check already uses:
  - each vaccine as it maps to the facility's vocabulary, plus the label as written;
  - the date given;
  - the expiry date, or empty when the certificate doesn't print one.
- Never infer an expiry date. A missing expiry stays empty, so compliance reports it as `unknown_expiry` and a person looks.
- Check the extraction in code:
  - image type and size limits before any model call;
  - dates that are impossible or in the future;
  - vaccine labels that don't map to a known vaccine;
  - a pet name on the certificate that doesn't match the pet;
  - low confidence, or the model reporting the image as hard to read.

  Any issue sends the result to human review.
- Factor the "validate, then repair once" logic out of intake into a shared structured-extraction helper used by both steps.
- Add a synthetic certificate generator. It renders HTML templates to PNG in three layouts, with blur, rotation, handwriting-style fonts, and missing fields. Each image is saved with its ground truth and visibly marked as a synthetic test document.
- Add an evaluation that runs the records step over 36 generated certificates and reports:
  - per-field accuracy;
  - **invented expiries**;
  - **decision agreement**: whether compliance computed from the extracted records matches compliance computed from the ground truth.

  Results are broken down by variant.

## Capabilities

### New Capabilities
- `vaccine-records-extraction`: Reading a vaccine certificate image into validated vaccine records, with the code checks and handoff rules that decide when a person must look.
- `certificate-evaluation`: The synthetic, ground-truth-labeled certificate set and the evaluation that measures extraction accuracy and its effect on compliance decisions.

### Modified Capabilities
- None. Intake's behavior is unchanged by the shared helper. Its existing tests must keep passing as they are.

## Impact

- **Backend:** new `app/records.py`, `app/prompts/records.py`, and `app/structured.py` (shared extraction helper); `app/intake.py` switches to the helper.
- **Evaluation assets:** `backend/evals/certificates/` holds templates, vendored open-license fonts, the generated PNGs, and their ground truth. Plus `scripts/generate_certificates.py` and `scripts/eval_records.py`.
- **New development dependencies:** `playwright` (Python) plus a one-time headless Chromium download, used only to render certificates, and `pillow` for blur and rotation. Neither is used at runtime.
- **Tests:** extraction logic and scoring are tested with scripted model answers. The real-model evaluation is opt-in and costs a few cents per run. The measured result is recorded.
- **Out of scope:**
  - multi-page certificates and PDFs;
  - storing extracted records in `vaccine_records` (that happens in the orchestrator, Phase 6);
  - comparing certificates against vet databases.
