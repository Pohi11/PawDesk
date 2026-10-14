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

## Develop (fast reload)

```bash
docker compose up -d postgres
cd backend && uv run uvicorn app.main:app --reload
cd frontend && pnpm dev
```

## Test

```bash
cd backend && uv run pytest
```

Tests run against the real Postgres container, not mocks.
