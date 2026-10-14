# Tasks

## 1. Recorded responses

- [x] 1.1 Add `app/cassettes.py` and the cassette settings, and wire them into the default client. Verify with `tests/test_cassettes.py`: record then replay returns the same response with no network call, and a missing recording fails without retry, naming the key.

## 2. Secrets

- [x] 2.1 Add `tests/test_secrets.py`. Verify that it fails on a planted key-shaped value in a temporary repository and passes on the real one.

## 3. End-to-end

- [x] 3.1 Extract `scripts/lab_database.py` from the comparison lab, and add `scripts/e2e_server.py`. Verify that the comparison tests still pass.
- [x] 3.2 Add Playwright with two spec-tagged tests and JUnit output. Record the responses once against the real model, then verify the tests pass in replay mode.
- [x] 3.3 Teach the walkthrough generator the `e2e` suite. Verify with a generator test where only an end-to-end test verifies a requirement.

## 4. Pipeline and README

- [x] 4.1 Add `.github/workflows/ci.yml` and `tests/test_ci_workflow.py`. Verify the structural test, and run each job's commands locally.
- [x] 4.2 Write [decision record 0016](../../../docs/decisions/0016-recorded-model-responses-for-ci.md), add `scripts/make_demo_gif.py`, generate `docs/demo.gif`, and rewrite the README with an architecture diagram and the measured results. Verify that the GIF exists and that the README links resolve.

## 5. Integration

- [ ] 5.1 Run every check, including the end-to-end tests and the walkthrough check over three reports. Regenerate the walkthrough.
