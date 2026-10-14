from collections.abc import Awaitable, Callable
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException

from app.api import router
from app.config import get_settings

CONTENT_TYPE = b"content-type"
JSON, UTF8_JSON = b"application/json", b"application/json; charset=utf-8"


class DeclareUTF8JSON:
    """Adds `charset=utf-8` to every `application/json` response, errors included.

    JSON is always UTF-8, but without a declared charset some clients guess another encoding
    (Windows PowerShell 5.1 reads ISO-8859-1, so "–" shows as "â€“"). Middleware rather than a
    default response class, because FastAPI's error handlers build their own responses.
    """

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        async def declare(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (name, UTF8_JSON if (name.lower(), value) == (CONTENT_TYPE, JSON) else value)
                    for name, value in message.get("headers", [])
                ]
            await send(message)

        await self.app(scope, receive, declare if scope["type"] == "http" else send)


app = FastAPI(title="PawDesk API")
app.add_middleware(DeclareUTF8JSON)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# A plain `def` (not `async def`): psycopg's connect is blocking, and FastAPI runs sync
# routes in a thread pool so they don't stall the event loop.
@app.get("/health/db")
def health_db() -> dict[str, str]:
    try:
        with psycopg.connect(get_settings().database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError as exc:
        # Don't echo the exception: connection errors can include the host and user.
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"database": "ok"}
