"""Traces and spans recorded while work runs (spec: run-tracing, design D3/D4).

    async with tracer.start_trace("process booking", booking_request_id=rid):
        async with span("compliance.check", SpanKind.CODE, input={...}) as s:
            s.output = {...}

The current trace, span, and tracer live in context variables, so nested code finds its
parent without passing ids around, and `asyncio.gather` children (which each get a *copy*
of the context) become siblings under the same parent.

Every write goes through the tracer's own sessions and is committed immediately, so spans
survive even when the business transaction they describe is rolled back (decision 0006).
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.enums import SpanKind, SpanStatus
from app.models import Span, Trace


class NoActiveTrace(RuntimeError):
    """Work that must be traced was started outside `Tracer.start_trace()`."""


@dataclass
class SpanHandle:
    """What the code inside a span may fill in; written when the span ends."""

    id: uuid.UUID
    output: Any = None
    attributes: dict[str, Any] = field(default_factory=dict)
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: Decimal | None = None


@dataclass(frozen=True)
class _Context:
    tracer: "Tracer"
    trace_id: uuid.UUID
    span_id: uuid.UUID | None


_current: ContextVar[_Context | None] = ContextVar("pawdesk_trace_context", default=None)


def current_trace_id() -> uuid.UUID | None:
    ctx = _current.get()
    return ctx.trace_id if ctx else None


class Tracer:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    # Each write is one short transaction of its own, independent of any business session.

    async def _insert(self, row: Trace | Span) -> uuid.UUID:
        async with self._sessions() as session, session.begin():
            session.add(row)
            await session.flush()  # Postgres generates the uuidv7 id; RETURNING hands it back
            return row.id

    async def _update(self, statement: Any) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(statement)

    @asynccontextmanager
    async def start_trace(
        self, name: str, booking_request_id: uuid.UUID | None = None
    ) -> AsyncIterator[uuid.UUID]:
        trace_id = await self._insert(Trace(name=name, booking_request_id=booking_request_id))
        token = _current.set(_Context(tracer=self, trace_id=trace_id, span_id=None))
        try:
            yield trace_id
        finally:
            _current.reset(token)
            await self._update(
                update(Trace).where(Trace.id == trace_id).values(ended_at=func.now())
            )


@asynccontextmanager
async def span(name: str, kind: SpanKind, input: Any = None) -> AsyncIterator[SpanHandle]:
    """Record `name` as a child of the current span (or as a root span of the trace)."""
    ctx = _current.get()
    if ctx is None:
        raise NoActiveTrace(f"span {name!r} started outside a trace")

    span_id = await ctx.tracer._insert(
        Span(
            trace_id=ctx.trace_id,
            parent_span_id=ctx.span_id,
            kind=kind,
            name=name,
            status=SpanStatus.RUNNING,
            input=input,
        )
    )
    handle = SpanHandle(id=span_id)
    token = _current.set(_Context(tracer=ctx.tracer, trace_id=ctx.trace_id, span_id=handle.id))
    status, error = SpanStatus.OK, None
    try:
        yield handle
    except Exception as exc:
        status, error = SpanStatus.ERROR, f"{type(exc).__name__}: {exc}"
        raise  # the caller gets the original exception, unchanged
    finally:
        _current.reset(token)
        await ctx.tracer._update(
            update(Span)
            .where(Span.id == handle.id)
            .values(
                status=status,
                error=error,
                ended_at=func.now(),
                output=handle.output,
                attributes=handle.attributes,
                model=handle.model,
                prompt_tokens=handle.prompt_tokens,
                completion_tokens=handle.completion_tokens,
                cost_usd=handle.cost_usd,
            )
        )
