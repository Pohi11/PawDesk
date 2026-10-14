"""Spec: llm-client, one real call to OpenRouter. Opt-in: `uv run pytest -m live`."""

import json

import pytest
from sqlalchemy import select

from app.db import make_sessionmaker
from app.enums import SpanKind, SpanStatus
from app.llm import complete
from app.models import Span

pytestmark = pytest.mark.live


@pytest.mark.spec("llm-client", "Each call records one model span")
@pytest.mark.spec("llm-client", "Cost comes from the provider, never estimated")
async def test_real_call_records_a_complete_span(tracer, engine):
    async with tracer.start_trace("live test"):
        result = await complete(
            [{"role": "user", "content": "Reply with the single word: OK"}], name="live.hello"
        )

    async with make_sessionmaker(engine)() as s:
        stored = await s.scalar(select(Span).where(Span.id == result.span_id))
    assert (stored.kind, stored.status) == (SpanKind.LLM, SpanStatus.OK)
    assert stored.prompt_tokens > 0 and stored.completion_tokens > 0
    assert stored.cost_usd is not None and stored.cost_usd > 0
    assert stored.output["text"]


@pytest.mark.spec("llm-client", "Model calls can offer tools")
async def test_real_model_calls_a_tool(tracer):
    tool = {
        "type": "function",
        "function": {
            "name": "check_kennel_sizes",
            "description": "Count free kennels per size class for a stay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"],
                "additionalProperties": False,
            },
        },
    }
    async with tracer.start_trace("live test"):
        result = await complete(
            [
                {
                    "role": "user",
                    "content": "Use the tool to check kennels from 2027-03-10 to 2027-03-13.",
                }
            ],
            name="live.tool",
            tools=[tool],
            temperature=0,
        )

    [call] = result.tool_calls
    assert call.name == "check_kennel_sizes"
    assert json.loads(call.arguments) == {"start_date": "2027-03-10", "end_date": "2027-03-13"}
