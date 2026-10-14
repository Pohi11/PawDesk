# Proposal

## Why

The production backend image crashed on startup with `No module named 'httpx'`. The app imports `httpx` directly, but it was declared only as a development dependency. It used to arrive indirectly with the model SDK, and the current SDK version no longer brings it. The image installs runtime dependencies only (`uv sync --no-dev`), so the gap appeared only there.

Every check passed regardless, because tests, the end-to-end server, and the dev server all run with development dependencies installed. Nothing built or started the production images.

## What Changes

- `httpx` and `pydantic` (also imported directly, previously present only through other packages) become declared runtime dependencies.
- A test fails when `app/` imports any third-party package that isn't a declared runtime dependency.
- The pipeline gains an `images` job. It builds the backend and frontend production images, and imports the app inside the backend image, which has runtime dependencies only.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `delivery-pipeline`: the automatic checks include building the production images and importing the app inside the backend image.

## Impact

- `backend/pyproject.toml` and `uv.lock`;
- `tests/test_runtime_dependencies.py` and `tests/test_ci_workflow.py`;
- `.github/workflows/ci.yml`.
