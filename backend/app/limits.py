"""Ceilings on model use for the public demo (spec: demo-hosting, design D3).

What costs money is model calls, and every one is already recorded as an `llm` span, so the
limits count those spans. That survives restarts, needs no table of its own, and a reseed
(which records no spans) doesn't use any of it up.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import SpanKind
from app.models import Span

HOUR = timedelta(hours=1)
DAY = timedelta(hours=24)


@dataclass(frozen=True)
class DemoLimits:
    """Most model calls allowed in the last hour and the last 24 hours. None means no limit."""

    per_hour: int | None = None
    per_day: int | None = None


async def model_calls_since(session: AsyncSession, window: timedelta) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(Span)
        .where(Span.kind == SpanKind.LLM, Span.started_at >= func.now() - window)
    )


async def limit_reached(session: AsyncSession, limits: DemoLimits) -> str | None:
    """The explanation to show when a limit is reached, or None when a run may start."""
    for limit, window, period in (
        (limits.per_hour, HOUR, "hourly"),
        (limits.per_day, DAY, "daily"),
    ):
        if limit is not None and await model_calls_since(session, window) >= limit:
            return f"The demo reached its {period} limit on model calls. Try again later."
    return None
