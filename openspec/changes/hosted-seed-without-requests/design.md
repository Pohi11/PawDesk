# Design

## Context

- **The hosted start script reseeds on every start** ([0019](../../../docs/decisions/0019-host-demo-on-hugging-face-and-neon.md)): it truncates every table and loads the seed, so data on the Space only lives until the next restart.
- **The seed's requests depend on nothing else and nothing depends on them.** No seeded reservation points at a seeded request, and the one approval belongs to the Biscuit request. The demo samples, the generator, and the capacity checks read the facility, owners, pets, and reservations only.
- **Local tooling relies on the requests.** Tests and the e2e suite use the seeded requests (for example the review queue and request list pages), so the default seed keeps them.

## Goals / Non-Goals

**Goals:** the hosted demo starts with an empty review queue and request list, and keeps every other seeded row.

**Non-Goals:** changing the local seed, stopping the reseed on start, or removing seeded reservations.

## Decisions

### D1. A command-line flag, passed by the start script
- **`--no-requests` on the seed command,** read in `main()`, passed down as `seed(session, today, requests=False)`. The default stays the full dataset.
- **The start script names it,** so the hosted behaviour is visible in the one file that defines a hosted start, next to the reseed it changes.
- **Alternative considered:** an environment variable set on the Space. It would hide the choice in the Space's settings, outside the repository, and a missing variable would silently bring the requests back.

### D2. Seeded reservations stay
- **They model kennels already booked** (every medium kennel is taken 4–7 days out), which the capacity search and the demo's alternatives rely on. They hold no request id, so they don't show as requests.

## Risks / Trade-offs

- [A first visitor sees an empty review queue and request list] → Each page already has an empty state, and the Try page is where the demo starts.
