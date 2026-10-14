"""The only way the system calls a language model (spec: llm-client, decision record 0006).

complete() refuses to run outside a trace, owns the retry loop, and records exactly one
`llm` span per call: scrubbed messages, response, tokens, provider-reported cost, and one
attempt entry per attempt.
"""

import base64
import binascii
import copy
import hashlib
from enum import StrEnum
from typing import Any

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
