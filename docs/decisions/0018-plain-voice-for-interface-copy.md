# 0018 — Interface copy follows a written guide, and the build checks what it can

- **Date:** 2026-10-14
- **Status:** Accepted

## Context

The dashboard's text read as templated. It used slogans built on a contrast ("Models are measured, not trusted"), phrases repeated three times for rhythm, filler adverbs ("exactly"), and passive sentences that left out who acted ("A polite decline was sent").

The passive sentences matter more than the rest. PawDesk's main safety property is who approves a booking: the deterministic checks or a named person, never a model. A status sentence that doesn't say who decided hides the one fact a reader most needs.

Two strings were also false. The build page said nothing on it was written by hand, but its method section was. A request that failed while sending read "Stopped while approved", which showed a raw state name.

Rewriting the text once fixes today's copy. Each new feature brings new copy, so the fix needs something that keeps it fixed.

## Options considered

1. **Rewrite once, with no rules written down.** The next feature brings the same patterns back, and nothing notices until a reader does.
2. **Rewrite, and write a guide.** It covers the rules that need judgment, but a guide doesn't stop a filler word from being committed.
3. **Rewrite, write a guide, and check the mechanical rules in the test suites.** The checkable rules are a list of banned words and phrases, and no em dash inside a sentence. A shared list file is read by a dashboard test and a backend test (the demo sample descriptions come from the backend).
4. **A model-based style check in CI.** It catches more than a word list, but it costs money on every run, and two runs can disagree on the same text. That breaks the project's rule that anything with a checkable answer is checked by plain code.

## Decision

Option 3.
- **The guide:** [`docs/style/interface-copy.md`](../style/interface-copy.md). It gives each rule a PawDesk example and lists three exceptions: "never" can state a guarantee the tests prove, a list of three is fine when there are three things, and short labels can drop the subject.
- **The list:** [`docs/style/copy-rules.json`](../style/copy-rules.json). Words are matched as whole words, ignoring case.
- **The dashboard check** parses the source with the TypeScript compiler and reads only text a user can see: JSX text and string values. It skips class names, import paths, object keys, and comments.
- **Outcome sentences** name the actor, and their unit tests pin that per actor.

The guide is a separate file because decision records don't change after they're committed, and the word list and examples will grow.

## Consequences

- **Good:** New copy, such as the generated-request Try page, meets the mechanical rules without a review pass. A banned word fails the build with its file and line.
- **Good:** Who decided is part of each outcome sentence's tested contract, not only a style preference.
- **Cost:** A list can't judge tone. Contrast slogans and repetition still depend on review against the guide.
- **Cost:** The list file sits outside both packages, so the frontend and backend tests each read a file from `docs/`. Two copies would drift apart, which is worse.
