"""Spec: llm-client, recording and replaying model responses."""

import httpx
import pytest

from app.cassettes import CassetteTransport
from app.llm import LLMError, RetryPolicy, cassette_transport, complete, make_client
from tests.test_llm import TEST_KEY, Script, fake_settings, image_message, ok

spec = pytest.mark.spec
REQ = "Model responses can be recorded and replayed"
MESSAGES = [{"role": "user", "content": "Is Biscuit welcome?"}]


async def call(tracer, transport, messages=MESSAGES):
    settings = fake_settings()
    async with tracer.start_trace("cassette test"):
        return await complete(
            messages,
            name="cassette",
            client=make_client(settings, transport=transport),
            settings=settings,
            policy=RetryPolicy(max_attempts=3, sleep=lambda s: _noop()),
        )


async def _noop():
    return None


@spec("llm-client", REQ)
async def test_record_then_replay(tracer, tmp_path):
    upstream = Script(ok(text="Yes, Biscuit is welcome."))

    recorded = await call(
        tracer, CassetteTransport(tmp_path, "record", httpx.MockTransport(upstream))
    )
    replayed = await call(tracer, CassetteTransport(tmp_path, "replay"))

    assert recorded.text == replayed.text == "Yes, Biscuit is welcome."
    assert replayed.cost_usd == recorded.cost_usd  # spans and cost still work on replay
    assert len(upstream.requests) == 1  # the replay never reached the model
    [saved] = list(tmp_path.glob("*.json"))
    text = saved.read_text(encoding="utf-8")
    assert TEST_KEY not in text and "Is Biscuit welcome" not in text  # responses only


@spec("llm-client", REQ)
async def test_images_are_never_written(tracer, tmp_path):
    upstream = Script(ok(text="Rabies until 2028."))

    await call(
        tracer,
        CassetteTransport(tmp_path, "record", httpx.MockTransport(upstream)),
        messages=[image_message("data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==")],
    )

    [saved] = list(tmp_path.glob("*.json"))
    assert "iVBORw0KGgo" not in saved.read_text(encoding="utf-8")


@spec("llm-client", REQ)
async def test_missing_recording_fails_without_retry(tracer, tmp_path):
    with pytest.raises(LLMError) as raised:
        await call(tracer, CassetteTransport(tmp_path, "replay"))

    assert raised.value.attempts == 1  # permanent: not retried
    assert "no recorded response for request" in str(raised.value)


@spec("llm-client", REQ)
async def test_a_changed_request_misses_the_recording(tracer, tmp_path):
    upstream = Script(ok(text="Yes."))
    await call(tracer, CassetteTransport(tmp_path, "record", httpx.MockTransport(upstream)))

    with pytest.raises(LLMError):
        await call(
            tracer,
            CassetteTransport(tmp_path, "replay"),
            messages=[{"role": "user", "content": "Is Biscuit welcome? (edited prompt)"}],
        )


def test_settings_choose_the_transport(tmp_path):
    assert cassette_transport(fake_settings()) is None
    replay = cassette_transport(
        fake_settings(llm_cassette_mode="replay", llm_cassette_dir=tmp_path)
    )
    assert isinstance(replay, CassetteTransport) and replay.mode == "replay"
    with pytest.raises(ValueError, match="llm_cassette_dir"):
        cassette_transport(fake_settings(llm_cassette_mode="replay"))
