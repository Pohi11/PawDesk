"""Recorded model responses for deterministic, offline runs (spec: llm-client; decision
record 0016).

An httpx transport under the model client. Everything above it (retries, spans, cost)
runs unchanged, so a replayed run still produces full traces.

    record  call the model, save each 200 response body as <sha256 of request body>.json
    replay  answer only from saved bodies; a missing one is a 404 (permanent, not retried)

Only response bodies are stored. Request bodies (which hold images) and headers (which
hold the key) are never written.
"""

import hashlib
import json
from pathlib import Path

import httpx

MODES = ("off", "record", "replay")


def request_key(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


class CassetteTransport(httpx.AsyncBaseTransport):
    def __init__(
        self, directory: Path, mode: str, upstream: httpx.AsyncBaseTransport | None = None
    ) -> None:
        if mode not in ("record", "replay"):
            raise ValueError(f"cassette mode must be record or replay, got {mode!r}")
        self.directory = directory
        self.mode = mode
        self._upstream = upstream

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        key = request_key(body)
        path = self._path(key)

        if self.mode == "replay":
            if not path.is_file():
                message = f"no recorded response for request {key} (re-record the cassettes)"
                return httpx.Response(404, json={"error": {"code": 404, "message": message}})
            return httpx.Response(200, json=json.loads(path.read_text(encoding="utf-8")))

        upstream = self._upstream or httpx.AsyncHTTPTransport()
        response = await upstream.handle_async_request(request)
        content = await response.aread()
        if response.status_code == 200:
            self.directory.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(json.loads(content), indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        return httpx.Response(response.status_code, headers=response.headers, content=content)

    async def aclose(self) -> None:
        if self._upstream is not None:
            await self._upstream.aclose()
