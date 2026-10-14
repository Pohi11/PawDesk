# Design

## Context

- **The backend image** runs `uv sync --frozen --no-dev`, so it holds runtime dependencies only.
- **Everything else** (tests, the end-to-end server, the dev server) runs from the full development environment.

## Decisions

### D1. Declare what you import
- **The test:** `tests/test_runtime_dependencies.py` parses every `import` in `app/` and drops standard-library modules and `app` itself.
- **Mapping:** each remaining module is mapped to its distribution with `importlib.metadata.packages_distributions()`.
- **Failure:** the test fails if a distribution isn't listed in `[project].dependencies`. Being installed indirectly through another package doesn't count, because such a link can disappear in any upgrade, as happened here.

### D2. Build and smoke-test the images in CI
- **The `images` job:**
  - `docker build` for `backend/` and for `frontend/`;
  - then `python -c "import app.main"` inside the backend image, with its own virtual environment.
- **Why it isn't redundant with D1:** D1 catches the dependency gap in the ordinary test run, while D2 catches anything else that only breaks in the production image (Dockerfile changes, missing files).

## Risks / Trade-offs

- [Image builds add CI time] → A separate job, which runs in parallel with the others.
