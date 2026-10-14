# Proposal

## Why

A real run's resolver summary looked garbled: "Mar 9â€“12" where the model wrote "Mar 9–12". The text in the database is correct UTF-8, and the API sends the correct bytes. The garbling happens in the client reading the API:
- **The API declares** `content-type: application/json` with no charset.
- **JSON is always UTF-8** (RFC 8259), and browsers and httpx read it that way.
- **Some clients don't.** Windows PowerShell 5.1's `Invoke-RestMethod` falls back to ISO-8859-1 when no charset is given, which turns the en dash's three bytes (`E2 80 93`) into three characters that print as `â€“`.

So model output that contains any non-ASCII character (dashes, accented names, curly quotes) reads wrong in a common operator tool, and looks like a bug in the model client.

## What Changes

- **JSON responses declare their encoding:** `application/json; charset=utf-8`. The bytes don't change; only the header does.
- **Regression tests pin the whole path:** a model response that carries an en dash as raw UTF-8, with no charset (as the provider sends it), reaches the saved step output, the span, and the API unchanged, and the same holds through a cassette recording and replay.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `observability-api`: JSON responses declare UTF-8.
- `llm-client`: non-ASCII text in a model response is kept exactly, live and through recordings.

## Impact

- **Backend:** `app/main.py` sets a default JSON response class that adds the charset.
- **Frontend:** none (`fetch().json()` always reads UTF-8).
- **Tests:**
  - an orchestration test with an en dash in the resolver's proposal, read back from the database and the API;
  - a cassette test that records and replays a response with an en dash;
  - an API test on the declared content type.
