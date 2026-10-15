# Tasks

## 1. Backend

- [x] 1.1 Translate libpq SSL options in `async_url`. Verify with unit tests for a hosted and a local URL.
- [x] 1.2 Let the seed command reset the host named in `PAWDESK_SEED_ALLOWED_HOST`. Verify with tests that a different remote host is still refused and the named host passes the check.
- [x] 1.3 Add the hourly and daily model-call limits to `POST /demo/requests`. Verify with API tests for each scenario, including that a refused request stores nothing.

## 2. Frontend

- [x] 2.1 Show the server's explanation when sending answers 429. Verify with a unit test.

## 3. Deployment

- [x] 3.1 Add the Space's Dockerfile, start script, and README in `deploy/huggingface/`. Verify by building the image locally and running it against a local database.
- [x] 3.2 Add the deploy script that builds the bundle from `HEAD` and uploads it. Verify with a test of the bundle's contents.
- [x] 3.3 Write decision record 0019 and a README section on the hosted demo.

## 4. Integration

- [x] 4.1 Run every backend and frontend suite, lint, type check, and the walkthrough coverage check.
- [x] 4.2 Create the Neon database, set the Space's secrets and variables, deploy, and check the hosted demo in a browser: pages load, a request runs to an outcome, and the limit message appears when a limit is reached.
