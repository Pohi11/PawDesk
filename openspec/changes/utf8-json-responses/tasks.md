# Tasks

## 1. Pin the path

- [ ] 1.1 Add regression tests for non-ASCII model text: an orchestration test where the resolver proposes an offer with an en dash sent as raw UTF-8, read back from the saved step and its span, and a cassette test that records and replays an en dash. Verify both pass on the current code, which shows the model client, resolver, and database keep the text.

## 2. Declare the charset

- [ ] 2.1 Set a default JSON response class that declares `charset=utf-8`. Verify with an API test that inspects a request whose resolver summary has an en dash and checks the header and the text; it fails before the change and passes after.

## 3. Integration

- [ ] 3.1 Run every backend suite and lint, then check the real API with Windows PowerShell's `Invoke-RestMethod`.
