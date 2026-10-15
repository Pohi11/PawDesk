# The hosted demo as one container (decision record 0019; change public-demo-hosting, D1).
# Built by Hugging Face from the deploy bundle, whose root is the repository root. Locally:
#   docker build -f deploy/huggingface/Dockerfile -t pawdesk-space .

# --- Dashboard: install, then build Next's standalone server ------------------------------
FROM node:24-slim AS web-base
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm@12.11.2
WORKDIR /app

FROM web-base AS web-deps
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM web-base AS web-build
COPY --from=web-deps /app/node_modules ./node_modules
COPY frontend/ .
RUN pnpm build

# --- Runtime: the backend's Python environment plus the node binary -----------------------
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/
# Next's standalone server needs only the node binary, not npm or the rest of the image.
COPY --from=node:24-slim /usr/local/bin/node /usr/local/bin/node

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=7860

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ .

WORKDIR /app/web
COPY --from=web-build /app/.next/standalone ./
COPY --from=web-build /app/.next/static ./.next/static
COPY --from=web-build /app/public ./public

COPY deploy/huggingface/start.sh /app/start.sh

# Spaces run the container as user 1000; Next writes its cache under .next at runtime.
RUN useradd --create-home --uid 1000 user && chown -R user /app/web
USER user

EXPOSE 7860
CMD ["bash", "/app/start.sh"]
