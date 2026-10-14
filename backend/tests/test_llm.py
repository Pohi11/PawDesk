"""Spec: llm-client. No test here contacts the real provider."""

import base64
import hashlib
import json
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select, text

from app.config import Settings, get_settings
from app.db import make_sessionmaker
from app.enums import SpanKind, SpanStatus
from app.llm import (
    AttemptOutcome,
    LLMError,
    RetryPolicy,
    classify_status,
    complete,
    make_client,
    scrub,
)
from app.models import Span
from app.tracing import NoActiveTrace

spec = pytest.mark.spec


# --- Failure classification (design D5) -----------------------------------------------


@spec("llm-client", "Transient failures are retried with backoff")
@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_statuses_are_retryable(status):
    assert classify_status(status) == AttemptOutcome.RETRYABLE


@spec("llm-client", "Permanent failures are not retried")
@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 422])
def test_other_error_statuses_are_fatal(status):
    assert classify_status(status) == AttemptOutcome.FATAL


def test_success_status_is_ok():
    assert classify_status(200) == AttemptOutcome.OK


# --- Scrubbing (design D8) ------------------------------------------------------------

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake certificate pixels" * 10
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode()


def image_message(url):
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": "Read this vaccine certificate."},
            {"type": "image_url", "image_url": {"url": url}},
        ],
    }


@spec("llm-client", "Secrets and raw images are never recorded")
def test_inline_image_is_replaced_by_hash_and_size():
    scrubbed = scrub([image_message(DATA_URL)])

    url = scrubbed[0]["content"][1]["image_url"]["url"]
    expected = f"[image sha256={hashlib.sha256(PNG_BYTES).hexdigest()} bytes={len(PNG_BYTES)}]"
    assert url == expected
    assert "base64" not in str(scrubbed)


@spec("llm-client", "Secrets and raw images are never recorded")
def test_scrub_leaves_text_and_remote_images_and_the_original_alone():
    remote = image_message("https://example.test/cert.png")
    original = [image_message(DATA_URL), {"role": "system", "content": "Be brief."}]

    scrubbed = scrub([*original, remote])

    assert original[0]["content"][1]["image_url"]["url"] == DATA_URL  # caller untouched
    assert scrubbed[0]["content"][0] == {"type": "text", "text": "Read this vaccine certificate."}
    assert scrubbed[1] == {"role": "system", "content": "Be brief."}
    assert scrubbed[2] == remote


# --- The traced client, against a scripted fake transport -----------------------------

TEST_KEY = "sk-or-v1-test-secret-never-store-me"


def ok_body(text="Biscuit can stay.", cost=0.0000942, gen_id="gen-1", model="deepseek/test"):
    usage = {"prompt_tokens": 42, "completion_tokens": 68, "total_tokens": 110}
    if cost is not None:
        usage["cost"] = cost
    return {
        "id": gen_id,
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "provider": "FakeProvider",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
        "usage": usage,
    }


def error_body(code):
    return {
        "id": "gen-x",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "error": {"code": code, "message": "provider trouble"},
    }


class Script:
    """Answers each request with the next step: an httpx.Response, or "timeout"."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        step = self.steps.pop(0)
        if step == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        return step


def ok(**kw):
    return httpx.Response(200, json=ok_body(**kw))


def fail(status, retry_after=None):
    headers = {"retry-after": str(retry_after)} if retry_after is not None else {}
    body = {"error": {"code": status, "message": "nope"}}
    return httpx.Response(status, json=body, headers=headers)


def fake_settings(**overrides):
    return Settings(
        database_url=get_settings().database_url, openrouter_api_key=TEST_KEY, **overrides
    )


@pytest.fixture
def llm(tracer, engine):
    """Run complete() inside a trace against a script. Returns (result or error, spans, waits)."""
    settings = fake_settings(llm_timeout_seconds=7.5)

    async def run(script, messages=None, max_attempts=3):
        waits: list[float] = []

        async def fake_sleep(seconds):
            waits.append(seconds)

        # Jitter pinned to its ceiling so waits are deterministic.
        policy = RetryPolicy(max_attempts=max_attempts, sleep=fake_sleep, jitter=lambda lo, hi: hi)
        client = make_client(settings, transport=httpx.MockTransport(script))
        async with tracer.start_trace("llm test") as trace_id:
            try:
                outcome = await complete(
                    messages or [{"role": "user", "content": "Can Biscuit board Fri-Mon?"}],
                    name="intake",
                    client=client,
                    policy=policy,
                    settings=settings,
                )
            except LLMError as exc:
                outcome = exc
        async with make_sessionmaker(engine)() as s:
            spans = list(await s.scalars(select(Span).where(Span.trace_id == trace_id)))
        return outcome, spans, waits

    return run


@spec("llm-client", "Model calls require an active trace")
async def test_call_outside_a_trace_is_refused_before_any_request():
    script = Script(ok())
    settings = fake_settings()
    client = make_client(settings, transport=httpx.MockTransport(script))

    with pytest.raises(NoActiveTrace):
        await complete(
            [{"role": "user", "content": "hi"}], name="x", client=client, settings=settings
        )

    assert script.requests == []


@spec("llm-client", "Each call records one model span")
async def test_successful_call_records_one_complete_span(llm):
    result, spans, _ = await llm(Script(ok()))

    assert result.text == "Biscuit can stay."
    [s] = spans
    assert (s.kind, s.status, s.name) == (SpanKind.LLM, SpanStatus.OK, "intake")
    assert s.input["messages"] == [{"role": "user", "content": "Can Biscuit board Fri-Mon?"}]
    assert s.input["model"]
    assert s.output == {"text": "Biscuit can stay.", "finish_reason": "stop"}
    assert (s.model, s.prompt_tokens, s.completion_tokens) == ("deepseek/test", 42, 68)
    assert s.attributes["finish_reason"] == "stop"
    assert s.attributes["generation_id"] == "gen-1"
    assert s.attributes["provider"] == "FakeProvider"
    assert [a["outcome"] for a in s.attributes["attempts"]] == ["ok"]
    assert s.started_at <= s.ended_at


@spec("llm-client", "Each call records one model span")
@spec("llm-client", "Transient failures are retried with backoff")
async def test_rate_limited_then_succeeds_is_one_span_with_two_attempts(llm):
    result, spans, _ = await llm(Script(fail(429), ok(text="second try")))

    assert result.text == "second try"
    [s] = spans
    assert s.status == SpanStatus.OK
    first, second = s.attributes["attempts"]
    assert (first["http_status"], first["outcome"]) == (429, "retryable")
    assert second["outcome"] == "ok"


@spec("llm-client", "Cost comes from the provider, never estimated")
async def test_reported_cost_is_stored_exactly(llm):
    result, [s], _ = await llm(Script(ok(cost=0.0000942)))

    assert result.cost_usd == Decimal("0.0000942")
    assert s.cost_usd == Decimal("0.0000942")


@spec("llm-client", "Cost comes from the provider, never estimated")
async def test_missing_cost_stays_empty(llm):
    result, [s], _ = await llm(Script(ok(cost=None)))

    assert result.cost_usd is None
    assert s.cost_usd is None
    assert s.status == SpanStatus.OK


@spec("llm-client", "Transient failures are retried with backoff")
async def test_retry_after_is_honored(llm):
    _, _, waits = await llm(Script(fail(429, retry_after=2), ok()))

    assert waits == [2.0]


@spec("llm-client", "Transient failures are retried with backoff")
async def test_attempts_run_out_with_growing_waits(llm):
    script = Script(fail(503), fail(503), fail(503))

    error, [s], waits = await llm(script)

    assert isinstance(error, LLMError)
    assert error.attempts == 3
    assert len(script.requests) == 3
    assert waits == [1.0, 2.0]  # full-jitter ceilings base*2^0, base*2^1
    assert s.status == SpanStatus.ERROR
    assert "503" in s.error


@spec("llm-client", "Transient failures are retried with backoff")
async def test_timeout_is_retried(llm):
    result, [s], _ = await llm(Script("timeout", ok(text="after timeout")))

    assert result.text == "after timeout"
    assert s.attributes["attempts"][0]["error"] == "timeout"


@spec("llm-client", "Permanent failures are not retried")
@pytest.mark.parametrize("status", [400, 401, 402, 403])
async def test_permanent_failure_is_not_retried(llm, status):
    script = Script(fail(status), ok())

    error, [s], waits = await llm(script)

    assert isinstance(error, LLMError)
    assert error.attempts == 1
    assert len(script.requests) == 1
    assert waits == []
    assert s.status == SpanStatus.ERROR


@spec("llm-client", "An error inside a successful response is a failure")
async def test_200_with_a_transient_provider_error_is_retried(llm):
    script = Script(httpx.Response(200, json=error_body(502)), ok(text="recovered"))

    result, [s], _ = await llm(script)

    assert result.text == "recovered"
    first = s.attributes["attempts"][0]
    assert (first["http_status"], first["outcome"]) == (200, "retryable")


@spec("llm-client", "An error inside a successful response is a failure")
async def test_200_with_a_permanent_provider_error_fails(llm):
    script = Script(httpx.Response(200, json=error_body(400)), ok())

    error, [s], _ = await llm(script)

    assert isinstance(error, LLMError)
    assert len(script.requests) == 1
    assert s.status == SpanStatus.ERROR


@spec("llm-client", "Each attempt has a timeout")
async def test_every_attempt_carries_the_configured_timeout(llm):
    script = Script("timeout", ok())

    await llm(script)

    assert len(script.requests) == 2
    for request in script.requests:
        assert request.extensions["timeout"]["read"] == 7.5


@spec("llm-client", "Secrets and raw images are never recorded")
async def test_api_key_is_sent_but_never_stored(llm, engine):
    script = Script(ok(), fail(401))
    await llm(script)
    await llm(script)

    assert TEST_KEY in script.requests[0].headers["authorization"]  # it really was used
    async with make_sessionmaker(engine)() as s:
        stored = await s.scalar(
            text("SELECT coalesce(string_agg(row_to_json(t)::text, ''), '') FROM traces t")
        )
        stored += await s.scalar(
            text("SELECT coalesce(string_agg(row_to_json(s)::text, ''), '') FROM spans s")
        )
    assert stored  # the scan really covered rows
    assert TEST_KEY not in stored
    assert "authorization" not in stored.lower()


@spec("llm-client", "Secrets and raw images are never recorded")
async def test_span_stores_image_hash_not_image(llm):
    _, [s], _ = await llm(Script(ok()), messages=[image_message(DATA_URL)])

    stored_url = s.input["messages"][0]["content"][1]["image_url"]["url"]
    assert stored_url.startswith("[image sha256=")
    assert base64.b64encode(PNG_BYTES).decode() not in str(s.input)


@spec("llm-client", "Structured requests go only to endpoints that support them")
async def test_response_format_requires_supporting_endpoints(tracer):
    script = Script(ok())
    settings = fake_settings()
    client = make_client(settings, transport=httpx.MockTransport(script))
    schema = {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": {}}}

    async with tracer.start_trace("t"):
        await complete(
            [{"role": "user", "content": "hi"}],
            name="x",
            response_format=schema,
            client=client,
            settings=settings,
        )

    body = json.loads(script.requests[0].content)
    assert body["provider"] == {"require_parameters": True}
    assert body["response_format"] == schema


@spec("llm-client", "Structured requests go only to endpoints that support them")
async def test_plain_request_has_no_routing_preferences(tracer):
    script = Script(ok())
    settings = fake_settings()
    client = make_client(settings, transport=httpx.MockTransport(script))

    async with tracer.start_trace("t"):
        await complete(
            [{"role": "user", "content": "hi"}], name="x", client=client, settings=settings
        )

    assert "provider" not in json.loads(script.requests[0].content)
