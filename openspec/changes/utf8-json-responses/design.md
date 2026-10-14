# Design

## Context

- **Where the text travels:** OpenRouter's HTTP response → httpx → the OpenAI SDK → `llm.complete()` → the resolver's tool-call parsing → `booking_step_results.output` (JSONB) → the API → a client.
- **Every step up to the API is byte-safe:**
  - httpx's `Response.json()` parses the raw bytes, so the charset header can't change the result;
  - the OpenAI SDK parses responses with `Response.json()`;
  - the cassette layer writes and reads its files as UTF-8;
  - `json.loads` on tool-call arguments works on Python strings;
  - the database is `UTF8`, and the saved output holds `E2 80 93` for the en dash.
- **The API's bytes are correct too.** Starlette's `JSONResponse` encodes UTF-8 but declares only `application/json`.

## Goals / Non-Goals

**Goals:** non-ASCII model text reads correctly in any HTTP client, and a test fails if any layer starts mangling it.

**Non-Goals:**
- escaping non-ASCII as `\uXXXX` in responses (it would also work, but makes raw responses harder to read and doesn't fix the header);
- changing how text is stored.

## Decisions

### D1. Declare the charset, not escape the text
- **A default response class** (`UTF8JSONResponse`, a `JSONResponse` with `media_type = "application/json; charset=utf-8"`) is set on the app, so every JSON route gets it without per-route changes.
- **RFC 8259 says the charset parameter has no meaning for JSON,** and conforming clients ignore it. Clients that guess (Windows PowerShell 5.1, some older tools) use it. Adding it costs nothing and removes the guess.
- **Non-JSON routes are untouched:** the event stream (`text/event-stream`, whose spec fixes UTF-8) and the PNG endpoints set their own media types.

### D2. Test the whole path with raw UTF-8 on the wire
- **The scripted model sends what the provider sends:** the en dash as raw UTF-8 bytes in both the message body and the tool-call arguments string, with `content-type: application/json` and no charset. A test that sent `–` escapes would pass even if a layer decoded bytes wrongly.
- **The assertion reads the saved step output from the database** and the summary from the API, and compares the exact string.
- **A cassette test** records and replays the same kind of response, since a recording is written and read as text.

## Risks / Trade-offs

- [A client that relied on the exact header string `application/json`] → The frontend and tests check the media type, not the full header; none compare it exactly.
