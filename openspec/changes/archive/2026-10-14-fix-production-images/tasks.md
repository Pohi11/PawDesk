# Tasks

## 1. Fix

- [x] 1.1 Declare `httpx` and `pydantic` as runtime dependencies, and add `tests/test_runtime_dependencies.py`. Verify that the test fails on the old dependency list and passes on the new one.
- [x] 1.2 Add the `images` job to the pipeline and extend `tests/test_ci_workflow.py`. Verify by building both images locally, importing the app inside the backend image, and checking every dashboard route against the rebuilt container.
