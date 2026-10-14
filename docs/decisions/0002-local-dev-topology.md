# 0002 — Local development: Postgres in Docker, apps on the host; Compose runs built images

- **Date:** 2026-10-13
- **Status:** Accepted

## Context

PawDesk has three runtime pieces: a FastAPI backend, a Next.js frontend, and PostgreSQL. Development happens on Windows with Docker Desktop. A single `docker compose up` should start the whole system for demos and end-to-end checks.

Docker Desktop on Windows and macOS shares source files into a Linux VM. File-change events often fail to cross that boundary or arrive late. The Next.js documentation warns that Fast Refresh inside such containers can take seconds or even minutes, and it advises against working around this with polling, because polling adds latency and CPU load.

## Options considered

1. **Everything in Compose, with source bind-mounted and hot reload in the containers.** One command for everything, but slow or broken reloads on Windows, and polling for file watching.
2. **Postgres only in Compose; apps always on the host.** Fast reloads, but there's no single command for the full system, and the containers are never exercised before CI.
3. **Both modes.** Compose builds and runs the full stack from images with no bind mounts. Daily development runs only Postgres in Docker and the apps on the host.

## Decision

Option 3.

- `docker compose up --build`: Postgres, the backend (uvicorn without reload), and the frontend (a standalone Next.js production build). This is used for demos and end-to-end checks.
- Daily development: `docker compose up -d postgres`, then `uv run uvicorn app.main:app --reload` and `pnpm dev` on the host.

Configuration differs only by environment variables. The backend reads `DATABASE_URL` (the host is `localhost` on the host machine, and `postgres` inside Compose). The frontend reads a server-only `BACKEND_URL`.

## Consequences

- **Good:** Instant reloads during development, and the container images are exercised whenever the full stack runs.
- **Good:** The full-stack mode runs production-like images, so build problems show up locally instead of in CI.
- **Good:** The frontend container gets no `env_file`, so backend secrets never reach it. A check of the running containers confirmed `OPENROUTER_*` variables are present in the backend and absent from the frontend.
- **Cost:** Two ways to run the system. Code changes need `--build` before they show up in Compose mode.
- **Cost:** Tests always run on the host against the Postgres container. They never run inside the backend image, which leaves out dev dependencies.
