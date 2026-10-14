# Interface copy

How the dashboard's text is written. Decision record [0018](../decisions/0018-plain-voice-for-interface-copy.md) explains why this guide exists. The rules are adapted from the MIT-licensed checklist at [github.com/hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop).

The build checks two of the rules on every test run, and review covers the rest.

## Checked by the build

**No banned words or phrases.** The list is in [`copy-rules.json`](copy-rules.json). Both the dashboard check (`frontend/tests/copy.test.ts`) and the demo sample check (`backend/tests/test_demo_copy.py`) read it. Most entries are filler adverbs that add emphasis without adding a fact.

| Instead of | Write |
|---|---|
| Costs are exactly what the provider reported. | Costs are the amounts the provider billed for each call. |
| Simply pick a sample. | Pick a sample. |

**No em dash inside a sentence.** Use a comma or a period, or split the sentence. A string that is only "—" is allowed: it marks a missing value in a table or figure.

## Checked in review

**Name who decided.** In PawDesk the most important fact about a booking is who approved it: the checks or a named person, never a model. A passive sentence hides that.

| Instead of | Write |
|---|---|
| Declined by Sam. A polite decline was sent. | Sam declined the request, and the pet parent got a polite no. |
| The rest were decided by the checks. | The checks decided the rest. |

**State the point once.** Skip slogans built on a contrast, setups that announce a point, and endings written to be quoted.

| Instead of | Write |
|---|---|
| Models are measured, not trusted. | Model steps are scored and traced. |
| A record is never rewritten; a changed mind is a new record. | A committed record stays as written. A new record replaces it when the decision changes. |

**Don't repeat for rhythm.** Repeating a phrase three times ("the same requests, the same model, and the same tools") reads as a template. Say it once.

**Plain headings.** Name what the panel holds ("Routing reasons", "Cost by model step"), not a question or a flourish ("Why it went this way", "Where the money goes").

**Make only true claims.** If a sentence describes what the system does, it has to match the code. "Nothing on these pages is written by hand" was false while the page had a hand-written section.

## Exceptions

- **"Never", "every", and "always" can state a guarantee the tests prove.** "A model never approves a booking" is the most precise claim available. They're out only when they're vague, as in "Wrong decisions nobody would notice."
- **A list of three is fine when there are three things,** such as send, edit, or decline.
- **Short labels can drop the subject.** A state tag reads "Sent", not "The desk sent it."
