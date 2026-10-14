"""The shared structured-extraction helper (used by intake and records)."""

import json

import httpx
import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.db import make_sessionmaker
from app.llm import make_client
from app.models import Span
from app.structured import InvalidModelOutput, extract, response_format_for
from tests.test_llm import Script, fake_settings, ok


class Point(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: int
    y: int


class PointError(InvalidModelOutput):
    pass


async def run(tracer, engine, *steps, **kwargs):
    script = Script(*steps)
    settings = fake_settings()
    client = make_client(settings, transport=httpx.MockTransport(script))
    async with tracer.start_trace("structured") as trace_id:
        try:
            outcome = await extract(
                Point,
                [{"role": "user", "content": "a point"}],
                name="point",
                schema_name="point",
                client=client,
                settings=settings,
                **kwargs,
            )
        except InvalidModelOutput as exc:
            outcome = exc
    async with make_sessionmaker(engine)() as s:
        names = sorted(await s.scalars(select(Span.name).where(Span.trace_id == trace_id)))
    return outcome, script, names


async def test_valid_first_answer(tracer, engine):
    (point, repaired), script, names = await run(tracer, engine, ok(text='{"x": 1, "y": 2}'))

    assert (point, repaired) == (Point(x=1, y=2), False)
    assert names == ["point.extract"]
    assert json.loads(script.requests[0].content)["temperature"] == 0


async def test_one_repair_then_success(tracer, engine):
    (point, repaired), _, names = await run(
        tracer, engine, ok(text='{"x": 1}'), ok(text='{"x": 1, "y": 3}')
    )

    assert (point, repaired) == (Point(x=1, y=3), True)
    assert names == ["point.extract", "point.repair"]


async def test_custom_error_class_after_failed_repair(tracer, engine):
    error, script, _ = await run(
        tracer, engine, ok(text="nope"), ok(text="nope"), error_cls=PointError
    )

    assert isinstance(error, PointError)
    assert "point output invalid after repair" in str(error)
    assert len(script.requests) == 2


def test_response_format_for_any_model():
    rf = response_format_for(Point, "point")

    assert rf["json_schema"]["name"] == "point"
    assert rf["json_schema"]["schema"]["required"] == ["x", "y"]
    assert rf["json_schema"]["schema"]["additionalProperties"] is False
    with pytest.raises(KeyError):
        rf["json_schema"]["schema"]["title"]
