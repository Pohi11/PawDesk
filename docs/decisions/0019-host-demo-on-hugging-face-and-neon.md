# 0019 — Host the public demo on Hugging Face Spaces and Neon

- **Date:** 2026-10-15
- **Status:** Accepted

## Context

The demo runs only on a developer machine (decision record 0002). A reviewer should be able to open a link and send a request without cloning anything. The hosting has to be free, run the existing stack (a FastAPI backend, a Next.js dashboard, and PostgreSQL), keep the model key server-side, and stay cheap to operate for a demo that is idle most of the time.

## Options considered

1. **Hugging Face Docker Space + Neon Postgres.** The Space runs one container from a Dockerfile, with secrets set on the Space. The free hardware sleeps after about two idle days and its disk is wiped on restart, so the database lives at Neon (free plan, serverless Postgres that suspends when idle). The cost is folding two services into one container.
2. **Vercel (dashboard) + Render (backend) + Neon.** Each part runs on a platform built for it. Three accounts and three deploys to keep in step, and Render's free web services sleep after about 15 idle minutes, so most visits start with a long cold start.
3. **A free-tier virtual machine (for example Oracle Cloud) running Docker Compose.** The local setup runs unchanged. The machine's operating system, TLS certificates, firewall, and updates become the project's job.
4. **AWS** (container service + managed Postgres). The most production-like option, but not free beyond trial credits, and the most setup for a demo.

## Decision

Option 1.

- **One container** runs the backend on the loopback address and the dashboard on the public port, so the browser still reaches the backend only through the allowlisted proxy.
- **Neon's direct endpoint** holds the database. The Space's container is disposable.
- **Each start migrates and reseeds** the database (explicitly allowed for that one host), so the public demo always starts from the known synthetic dataset.
- **Model spend has two ceilings:** limits on model calls per hour and per day, counted from recorded spans, and a separate OpenRouter key with a credit limit.
- **Deploys upload only committed files** (`git archive HEAD`), so local secrets and private notes can't reach the Space.

## Consequences

- **Good:** one link to a working demo, with no cost beyond the capped model spend.
- **Good:** the deploy path can't publish uncommitted or ignored files.
- **Cost:** the hosted topology differs from local development (one container instead of three), so a hosted-only failure needs the Space's logs to debug.
- **Cost:** visits after an idle period wait for the Space and Neon's compute to wake.
- **Cost:** every visitor acts as staff and can change what other visitors see until the next restart. That is acceptable only because all data is synthetic and no reply leaves the system. Real sign-in is needed before real data.
