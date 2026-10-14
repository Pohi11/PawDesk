FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the dependency files first: this layer stays cached until they change,
# so editing code doesn't reinstall every package. Dev tools (pytest, ruff) are left out.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000
# Bring the schema up to date before serving, so `docker compose up` never runs new code
# against an old schema. `exec` makes uvicorn PID 1, so it receives Docker's stop signal.
CMD ["sh", "-c", "/opt/venv/bin/alembic upgrade head && exec /opt/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"]
