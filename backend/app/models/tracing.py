"""Traces and spans, modeled on OpenTelemetry (spec: run-tracing, design D9)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import SpanKind, SpanStatus
from app.models.base import Base, UUIDPrimaryKey
from app.models.types import str_enum


class Trace(UUIDPrimaryKey, Base):
    """One run, e.g. processing one booking request end to end."""

    __tablename__ = "traces"
    __table_args__ = (CheckConstraint("ended_at >= started_at", name="ends_after_start"),)

    booking_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("booking_requests.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Span(UUIDPrimaryKey, Base):
    """One step inside a trace: a model call, a tool call, plain code, or a human action."""

    __tablename__ = "spans"
    __table_args__ = (
        # Target for the composite parent key below.
        UniqueConstraint("trace_id", "id"),
        # The parent must be a span *in the same trace*: (trace_id, parent_span_id) has to
        # match an existing (trace_id, id). With MATCH SIMPLE (the default), a NULL
        # parent_span_id skips the check, which is how root spans work.
        ForeignKeyConstraint(
            ["trace_id", "parent_span_id"],
            ["spans.trace_id", "spans.id"],
            name="fk_spans_parent_in_same_trace",
        ),
        CheckConstraint("ended_at >= started_at", name="ends_after_start"),
        CheckConstraint("prompt_tokens >= 0", name="prompt_tokens_non_negative"),
        CheckConstraint("completion_tokens >= 0", name="completion_tokens_non_negative"),
        CheckConstraint("cost_usd >= 0", name="cost_non_negative"),
        CheckConstraint(
            "status <> 'error' OR coalesce(btrim(error), '') <> ''", name="error_has_message"
        ),
        CheckConstraint("jsonb_typeof(attributes) = 'object'", name="attributes_is_object"),
    )

    trace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("traces.id"))
    parent_span_id: Mapped[uuid.UUID | None] = mapped_column()
    kind: Mapped[SpanKind] = mapped_column(str_enum(SpanKind, "kind"))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[SpanStatus] = mapped_column(
        str_enum(SpanStatus, "status"),
        default=SpanStatus.RUNNING,
        server_default=SpanStatus.RUNNING.value,
    )
    input: Mapped[Any | None] = mapped_column(JSONB)
    output: Mapped[Any | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model: Mapped[str | None] = mapped_column(String(200))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    # Exact decimal, never float: 0.0000942 has no exact binary representation, and
    # summing many float costs drifts.
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 10))
    error: Mapped[str | None] = mapped_column(Text)
    # OpenTelemetry-style structured metadata: attempts, finish reason, provider, params.
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
