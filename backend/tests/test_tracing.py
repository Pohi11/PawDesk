"""Spec: run-tracing, recording spans while work runs (design D3/D4)."""

import asyncio

import pytest
from sqlalchemy import select

from app.db import make_sessionmaker
from app.enums import SpanKind, SpanStatus
from app.models import Owner, Span, Trace
from app.tracing import NoActiveTrace, span

spec = pytest.mark.spec


async def read_span(engine, span_id) -> Span:
    """Read through a fresh connection, as another process would."""
    async with make_sessionmaker(engine)() as s:
        return await s.get(Span, span_id)


@spec("run-tracing", "Spans are recorded while work runs")
async def test_running_span_is_visible_from_another_connection(tracer, engine):
    async with tracer.start_trace("t"), span("slow step", SpanKind.CODE) as s:
        seen = await read_span(engine, s.id)
        assert (seen.status, seen.ended_at) == (SpanStatus.RUNNING, None)

    finished = await read_span(engine, s.id)
    assert finished.status == SpanStatus.OK
    assert finished.ended_at is not None


@spec("run-tracing", "Spans are recorded while work runs")
async def test_output_and_attributes_are_written_when_the_span_ends(tracer, engine):
    async with tracer.start_trace("t"), span("step", SpanKind.TOOL, input={"q": 1}) as s:
        s.output = {"answer": 42}
        s.attributes["note"] = "done"

    stored = await read_span(engine, s.id)
    assert (stored.input, stored.output, stored.attributes) == (
        {"q": 1},
        {"answer": 42},
        {"note": "done"},
    )


@spec("run-tracing", "Spans are recorded while work runs")
async def test_failing_work_is_recorded_and_the_exception_reaches_the_caller(tracer, engine):
    boom = ValueError("kennel exploded")

    with pytest.raises(ValueError) as raised:
        async with tracer.start_trace("t"), span("step", SpanKind.CODE) as s:
            raise boom

    assert raised.value is boom
    stored = await read_span(engine, s.id)
    assert stored.status == SpanStatus.ERROR
    assert stored.error == "ValueError: kennel exploded"
    assert stored.ended_at is not None


@spec("run-tracing", "Spans are recorded while work runs")
async def test_trace_gets_an_end_time(tracer, engine):
    async with tracer.start_trace("t") as trace_id:
        pass

    async with make_sessionmaker(engine)() as s:
        assert (await s.get(Trace, trace_id)).ended_at is not None


@spec("run-tracing", "Spans are recorded while work runs")
async def test_span_outside_a_trace_is_refused():
    with pytest.raises(NoActiveTrace):
        async with span("orphan", SpanKind.CODE):
            pass


@spec("run-tracing", "Parent links follow the code structure")
async def test_nested_span_has_the_outer_span_as_parent(tracer, engine):
    async with tracer.start_trace("t"), span("outer", SpanKind.CODE) as outer:
        async with span("inner", SpanKind.CODE) as inner:
            pass
        async with span("after inner", SpanKind.CODE) as after:
            pass

    assert (await read_span(engine, outer.id)).parent_span_id is None
    assert (await read_span(engine, inner.id)).parent_span_id == outer.id
    assert (await read_span(engine, after.id)).parent_span_id == outer.id


@spec("run-tracing", "Parent links follow the code structure")
async def test_concurrent_siblings_share_the_parent(tracer, engine):
    async def child(name):
        async with span(name, SpanKind.LLM) as s:
            await asyncio.sleep(0.05)  # make sure both are open at the same time
            async with span(f"{name}.inner", SpanKind.CODE) as inner:
                pass
            return s.id, inner.id

    async with tracer.start_trace("t"), span("orchestrator", SpanKind.CODE) as parent:
        (a, a_inner), (b, b_inner) = await asyncio.gather(child("intake"), child("records"))

    assert (await read_span(engine, a)).parent_span_id == parent.id
    assert (await read_span(engine, b)).parent_span_id == parent.id
    assert (await read_span(engine, a_inner)).parent_span_id == a
    assert (await read_span(engine, b_inner)).parent_span_id == b


@spec("run-tracing", "Traces survive rolled-back work")
async def test_span_survives_a_rolled_back_business_transaction(tracer, engine):
    business = make_sessionmaker(engine)()
    try:
        with pytest.raises(RuntimeError):
            async with tracer.start_trace("t"), span("step", SpanKind.CODE) as s:
                business.add(Owner(full_name="Ghost", email="ghost@example.test"))
                await business.flush()
                raise RuntimeError("step failed")
        await business.rollback()
    finally:
        await business.close()

    async with make_sessionmaker(engine)() as check:
        ghost = await check.scalar(select(Owner).where(Owner.email == "ghost@example.test"))
    assert ghost is None
    assert (await read_span(engine, s.id)).status == SpanStatus.ERROR
