#!/usr/bin/env bash
# Starts the hosted demo (change public-demo-hosting, design D1 and D4).
set -euo pipefail

cd /app/backend
/opt/venv/bin/alembic upgrade head

# Every start resets the demo to the seeded dataset, without example requests, so the
# review queue and request list hold only what visitors send. The seed refuses any remote host
# except the one named here, so leaving it unset keeps existing data.
if [[ -n "${PAWDESK_SEED_ALLOWED_HOST:-}" ]]; then
  /opt/venv/bin/python -m scripts.seed --no-requests
fi

# The backend listens on the loopback address only: the dashboard's allowlisted proxy
# stays the one way in, as it is locally.
/opt/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &

cd /app/web
BACKEND_URL=http://127.0.0.1:8000 HOSTNAME=0.0.0.0 node server.js &

# If either process exits, stop the container so the Space restarts it, rather than
# serving pages with no API behind them.
wait -n
exit 1
