"""Spec: run-tracing. Storage only; recording spans around real calls comes in Phase 3."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.enums import SpanKind, SpanStatus
from app.models import Span, Trace

spec = pytest.mark.spec


async def make_trace(session, name="test run") -> Trace:
    trace = Trace(name=name)
    session.add(trace)
    await session.flush()
    return trace


async def make_span(session, trace, **fields) -> Span:
    span = Span(trace_id=trace.id, kind=fields.pop("kind", SpanKind.CODE), name="step", **fields)
    session.add(span)
    await session.flush()
    return span


@spec("run-tracing", "A trace groups the spans of one run")
async def test_span_without_a_trace_is_rejected(session):
    session.add(Span(trace_id=None, kind=SpanKind.CODE, name="orphan"))

    with pytest.raises(IntegrityError):
        await session.flush()


@spec("run-tracing", "Spans form a tree within their trace")
async def test_nested_span_keeps_its_parent(session):
    trace = await make_trace(session)
    parent = await make_span(session, trace)
    child = await make_span(session, trace, parent_span_id=parent.id)

    stored_parent = await session.scalar(select(Span.parent_span_id).where(Span.id == child.id))

    assert stored_parent == parent.id


@spec("run-tracing", "Spans form a tree within their trace")
async def test_parent_from_another_trace_is_rejected(session):
    trace_a = await make_trace(session, "a")
    trace_b = await make_trace(session, "b")
    parent_in_a = await make_span(session, trace_a)

    with pytest.raises(IntegrityError, match="fk_spans_parent_in_same_trace"):
        await make_span(session, trace_b, parent_span_id=parent_in_a.id)


@spec("run-tracing", "Spans have a kind and a status")
async def test_unknown_kind_is_rejected(session):
    trace = await make_trace(session)

    with pytest.raises(IntegrityError, match="ck_spans_kind"):
        await session.execute(
            text("INSERT INTO spans (trace_id, kind, name) VALUES (:t, 'agent', 'x')"),
            {"t": trace.id},
        )


@spec("run-tracing", "Spans have a kind and a status")
@pytest.mark.parametrize("error", [None, "", "  "], ids=["null", "empty", "blank"])
async def test_error_span_without_a_message_is_rejected(session, error):
    trace = await make_trace(session)

    with pytest.raises(IntegrityError, match="ck_spans_error_has_message"):
        await make_span(session, trace, status=SpanStatus.ERROR, error=error)


@spec("run-tracing", "Spans have a kind and a status")
async def test_new_span_starts_running(session):
    span = await make_span(session, await make_trace(session))

    assert span.status == SpanStatus.RUNNING


@spec("run-tracing", "Spans store payloads, timing, and usage")
async def test_model_call_span_round_trips_exactly(session):
    trace = await make_trace(session)
    payload_in = {"messages": [{"role": "user", "content": "Can Biscuit board Fri-Mon?"}]}
    payload_out = {"pet": "Biscuit", "nights": 3, "notes": None}
    span = await make_span(
        session,
        trace,
        kind=SpanKind.LLM,
        model="deepseek/deepseek-v4.1-flash",
        prompt_tokens=42,
        completion_tokens=68,
        cost_usd=Decimal("0.0000942"),
        input=payload_in,
        output=payload_out,
    )
    session.expunge(span)  # force a real read from Postgres below

    stored = await session.get(Span, span.id)

    assert stored.model == "deepseek/deepseek-v4.1-flash"
    assert (stored.prompt_tokens, stored.completion_tokens) == (42, 68)
    assert stored.cost_usd == Decimal("0.0000942")
    assert stored.input == payload_in
    assert stored.output == payload_out


@spec("run-tracing", "Spans store payloads, timing, and usage")
async def test_cost_is_exact_to_eight_decimal_places_when_summed(session):
    trace = await make_trace(session)
    for _ in range(10):
        await make_span(session, trace, kind=SpanKind.LLM, cost_usd=Decimal("0.00000001"))

    total = await session.scalar(
        select(text("sum(cost_usd)")).select_from(Span).where(Span.trace_id == trace.id)
    )

    assert total == Decimal("0.0000001")


@spec("run-tracing", "Spans store payloads, timing, and usage")
@pytest.mark.parametrize("field", ["prompt_tokens", "completion_tokens"])
async def test_negative_token_count_is_rejected(session, field):
    trace = await make_trace(session)

    with pytest.raises(IntegrityError, match=f"ck_spans_{field}_non_negative"):
        await make_span(session, trace, **{field: -1})


@spec("run-tracing", "Spans store payloads, timing, and usage")
async def test_end_before_start_is_rejected(session):
    trace = await make_trace(session)
    start = datetime(2027, 3, 6, 12, 0, tzinfo=UTC)

    with pytest.raises(IntegrityError, match="ck_spans_ends_after_start"):
        await make_span(session, trace, started_at=start, ended_at=start - timedelta(seconds=1))


@spec("run-tracing", "Spans carry attributes")
async def test_attributes_default_to_an_empty_object(session):
    span = await make_span(session, await make_trace(session))
    session.expunge(span)

    stored = await session.get(Span, span.id)

    assert stored.attributes == {}


@spec("run-tracing", "Spans carry attributes")
async def test_attributes_round_trip(session):
    attributes = {"finish_reason": "stop", "attempts": [{"n": 1, "outcome": "ok"}]}
    span = await make_span(session, await make_trace(session), attributes=attributes)
    session.expunge(span)

    stored = await session.get(Span, span.id)

    assert stored.attributes == attributes


@spec("run-tracing", "Spans carry attributes")
async def test_attributes_must_be_an_object(session):
    trace = await make_trace(session)

    with pytest.raises(IntegrityError, match="ck_spans_attributes_is_object"):
        await session.execute(
            text(
                "INSERT INTO spans (trace_id, kind, name, attributes) VALUES (:t, 'code', 'x', '[1]')"
            ),
            {"t": trace.id},
        )
