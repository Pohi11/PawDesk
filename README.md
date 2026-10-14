# PawDesk

A booking intake desk for pet care businesses (boarding, daycare, grooming). It reads a pet parent's request and vaccine certificate, checks them against facility rules and kennel capacity, resolves problems, drafts a reply, and routes risky cases to staff, with every step traced and visible.

> Work in progress. Specs live in [`openspec/`](openspec/) and decisions in [`docs/decisions/`](docs/decisions/).

## Requirements

Docker Desktop, [uv](https://docs.astral.sh/uv/), Node.js 20.19 or newer, and [pnpm](https://pnpm.io/).

## Setup

```bash
cp .env.example .env   # then set OPENROUTER_API_KEY
```

## Run the full stack (built images)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000/health and http://localhost:8000/docs

The backend container applies database migrations on startup.

## Develop (fast reload)

```bash
docker compose up -d postgres
cd backend
uv run alembic upgrade head      # apply migrations
uv run python -m scripts.seed    # load the synthetic dataset (local databases only; replaces existing data)
uv run uvicorn app.main:app --reload
```

```bash
cd frontend && pnpm dev
```

After changing models, generate a migration and review it by hand before committing:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic check             # passes when models and migrations agree
```

## Test

```bash
cd backend
uv run pytest                    # unit + database tests
uv run ruff check . && uv run ruff format --check .
```

Tests run against a real Postgres database (`pawdesk_test`, created and migrated automatically), not mocks. Each test runs in a transaction that is rolled back afterward.

Tests that verify a spec requirement carry `@pytest.mark.spec("<capability>", "<requirement>")`, which is exported to JUnit XML (`uv run pytest --junitxml=report.xml`), so results can be traced back to [`openspec/specs/`](openspec/specs/).
