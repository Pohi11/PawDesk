# Tasks

## 1. Pin the path

- [x] 1.1 Add regression tests for non-ASCII model text: an orchestration test where the resolver proposes an offer with an en dash sent as raw UTF-8, read back from the saved step and its span, and a cassette test that records and replays an en dash. Verify both pass on the current code, which shows the model client, resolver, and database keep the text.

## 2. Declare the charset

- [x] 2.1 Add a middleware that declares `charset=utf-8` on every JSON response. Verify with API tests: one inspects a request whose resolver summary has an en dash and checks the header and the text (it fails before the change and passes after), and one checks a 404 and a 422.

## 3. Integration

- [ ] 3.1 Run every backend suite and lint, then check the real API with Windows PowerShell's `Invoke-RestMethod`.
