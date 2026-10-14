"""The only way the system calls a language model (spec: llm-client, decision record 0006).

complete() refuses to run outside a trace, owns the retry loop, and records exactly one
`llm` span per call: scrubbed messages, response, tokens, provider-reported cost, and one
attempt entry per attempt.
"""

import asyncio
import base64
import binascii
import copy
import hashlib
import random
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from typing import Any

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from app.config import Settings, get_settings
from app.enums import SpanKind
from app.tracing import NoActiveTrace, SpanHandle, current_trace_id, span

RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class AttemptOutcome(StrEnum):
    OK = "ok"
    RETRYABLE = "retryable"
    FATAL = "fatal"


def classify_status(status: int) -> AttemptOutcome:
    """Design D5: transient statuses are worth retrying; any other error status is not."""
    if 200 <= status < 300:
        return AttemptOutcome.OK
    return AttemptOutcome.RETRYABLE if status in RETRYABLE_STATUSES else AttemptOutcome.FATAL


def _image_placeholder(data_url: str) -> str:
    _, _, payload = data_url.partition(",")
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raw = payload.encode()
    return f"[image sha256={hashlib.sha256(raw).hexdigest()} bytes={len(raw)}]"


def scrub(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A copy of `messages` safe to store: inline images become hash + size (design D8).

    The hash still identifies exactly which image was processed, without storing it.
    The caller's messages are never modified.
    """
    safe = copy.deepcopy(messages)
    for message in safe:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            image = part.get("image_url") if isinstance(part, dict) else None
            if isinstance(image, dict) and str(image.get("url", "")).startswith("data:"):
                image["url"] = _image_placeholder(image["url"])
    return safe


# --- The traced client ----------------------------------------------------------------


class LLMError(Exception):
    """A model call failed for good: a fatal error, or retries ran out."""

    def __init__(self, message: str, outcome: AttemptOutcome, attempts: int) -> None:
        super().__init__(message)
        self.outcome = outcome
        self.attempts = attempts


@dataclass(frozen=True)
class ToolCall:
    """One tool call the model asked for. `arguments` is the raw JSON text, unvalidated:
    the caller parses and checks it before running anything."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    generation_id: str
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: Decimal | None
    span_id: uuid.UUID
    tool_calls: tuple[ToolCall, ...] = ()
    # The assistant turn exactly as the API expects it back on the next call. A tool result
    # must follow the assistant message that requested it, with the same tool_call_id.
    assistant_message: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryPolicy:
    """Design D6. `sleep` and `jitter` are injectable so tests run instantly."""

    max_attempts: int = 3
    base_seconds: float = 1.0
    cap_seconds: float = 20.0
    max_retry_after_seconds: float = 60.0
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    jitter: Callable[[float, float], float] = random.uniform

    def wait_before(self, next_attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(retry_after, self.max_retry_after_seconds)
        ceiling = min(self.cap_seconds, self.base_seconds * 2 ** (next_attempt - 2))
        return self.jitter(0, ceiling)  # "full jitter": anywhere between 0 and the ceiling


def make_client(
    settings: Settings, transport: httpx.AsyncBaseTransport | None = None
) -> AsyncOpenAI:
    # max_retries=0: the SDK must not retry behind our back; complete() owns the loop (D1).
    return AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key.get_secret_value(),
        max_retries=0,
        http_client=httpx.AsyncClient(transport=transport) if transport else None,
    )


@lru_cache
def _default_client() -> AsyncOpenAI:
    return make_client(get_settings())


def _retry_after(headers: httpx.Headers) -> float | None:
    try:
        return float(headers["retry-after"])
    except (KeyError, ValueError):
        return None  # absent, or an HTTP-date we don't bother parsing: fall back to jitter


def _body_error_status(error: Any) -> int | None:
    code = error.get("code") if isinstance(error, dict) else None
    try:
        return int(code)
    except (TypeError, ValueError):
        return None


async def complete(
    messages: list[dict[str, Any]],
    *,
    name: str,
    model: str | None = None,
    response_format: dict[str, Any] | None = None,
    temperature: float | None = None,
    tools: list[dict[str, Any]] | None = None,
    client: AsyncOpenAI | None = None,
    policy: RetryPolicy | None = None,
    settings: Settings | None = None,
) -> LLMResult:
    if current_trace_id() is None:
        raise NoActiveTrace(f"model call {name!r} made outside a trace")  # before any request

    settings = settings or get_settings()
    client = client or _default_client()
    policy = policy or RetryPolicy(max_attempts=settings.llm_max_attempts)
    model = model or settings.openrouter_model
    params = {
        k: v
        for k, v in {
            "response_format": response_format,
            "temperature": temperature,
            "tools": tools,
        }.items()
        if v is not None
    }
    # Some endpoints treat a schema as a hint or ignore it, and some can't call tools; route
    # those requests only to endpoints that support every parameter we send. Pydantic still
    # validates the result.
    needs_support = response_format is not None or tools is not None
    extra_body = {"provider": {"require_parameters": True}} if needs_support else None

    async with span(
        name, SpanKind.LLM, input={"messages": scrub(messages), "model": model, "params": params}
    ) as s:
        attempts: list[dict[str, Any]] = []
        s.attributes["attempts"] = attempts

        for n in range(1, policy.max_attempts + 1):
            started = time.perf_counter()
            entry: dict[str, Any] = {"n": n}
            attempts.append(entry)
            retry_after: float | None = None
            try:
                # Two limits: httpx's timeout only bounds the gap between bytes, and a provider
                # that trickles keep-alive bytes never trips it. asyncio.timeout is the
                # wall-clock deadline for the whole attempt.
                async with asyncio.timeout(settings.llm_timeout_seconds):
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        timeout=settings.llm_timeout_seconds,
                        extra_body=extra_body,
                        **params,
                    )
            except (APITimeoutError, TimeoutError):
                outcome, error = AttemptOutcome.RETRYABLE, "timeout"
            except APIConnectionError:
                outcome, error = AttemptOutcome.RETRYABLE, "connection error"
            except APIStatusError as exc:
                outcome, error = classify_status(exc.status_code), f"HTTP {exc.status_code}"
                entry["http_status"] = exc.status_code
                retry_after = _retry_after(exc.response.headers)
            else:
                extra = response.model_extra or {}
                if response.choices:
                    entry.update(outcome=AttemptOutcome.OK, http_status=200)
                    entry["latency_ms"] = round((time.perf_counter() - started) * 1000)
                    return _record_success(s, response, extra)
                # HTTP 200 carrying an error and no answer (design D5).
                body_error = extra.get("error")
                status = _body_error_status(body_error)
                outcome = classify_status(status) if status else AttemptOutcome.FATAL
                error = f"error in 200 response: {body_error or 'no choices'}"
                entry["http_status"] = 200

            entry.update(outcome=outcome, error=error)
            entry["latency_ms"] = round((time.perf_counter() - started) * 1000)
            if outcome is AttemptOutcome.FATAL or n == policy.max_attempts:
                raise LLMError(f"{name}: {error} after {n} attempt(s)", outcome, n)
            wait = policy.wait_before(n + 1, retry_after)
            entry["waited_s"] = round(wait, 3)
            await policy.sleep(wait)

    raise AssertionError("unreachable: the loop always returns or raises")


def _record_success(s: SpanHandle, response: Any, extra: dict[str, Any]) -> LLMResult:
    choice = response.choices[0]
    usage = response.usage
    cost = getattr(usage, "cost", None) if usage else None
    s.model = response.model
    s.prompt_tokens = usage.prompt_tokens if usage else None
    s.completion_tokens = usage.completion_tokens if usage else None
    # str() first: keeps the digits the provider sent (9.42e-05 -> exactly 0.0000942) (D9).
    s.cost_usd = Decimal(str(cost)) if cost is not None else None
    tool_calls = tuple(
        ToolCall(id=c.id, name=c.function.name, arguments=c.function.arguments or "")
        for c in choice.message.tool_calls or ()
    )
    assistant_message: dict[str, Any] = {"role": "assistant", "content": choice.message.content}
    if tool_calls:
        assistant_message["tool_calls"] = [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
            for c in tool_calls
        ]
    s.output = {"text": choice.message.content, "finish_reason": choice.finish_reason}
    if tool_calls:
        s.output["tool_calls"] = [{"name": c.name, "arguments": c.arguments} for c in tool_calls]
    s.attributes.update(
        finish_reason=choice.finish_reason,
        generation_id=response.id,
        provider=extra.get("provider"),
    )
    return LLMResult(
        text=choice.message.content or "",
        model=response.model,
        generation_id=response.id,
        finish_reason=choice.finish_reason,
        prompt_tokens=s.prompt_tokens,
        completion_tokens=s.completion_tokens,
        cost_usd=s.cost_usd,
        span_id=s.id,
        tool_calls=tool_calls,
        assistant_message=assistant_message,
    )
