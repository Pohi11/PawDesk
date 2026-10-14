"""Spec: llm-client. No test here contacts the real provider."""

import base64
import hashlib

import pytest

from app.llm import AttemptOutcome, classify_status, scrub

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
