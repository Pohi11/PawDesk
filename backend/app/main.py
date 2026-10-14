import psycopg
from fastapi import FastAPI, HTTPException

from app.config import get_settings

app = FastAPI(title="PawDesk API")


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
