# Design

## Context

- **Where the copy lives.** The dashboard's text is spread across about fifteen files: page intros in `app/*/page.tsx`, labels and state names in `components/ui.tsx`, outcome sentences in `lib/story.ts`, eval and comparison labels in `app/evals/page.tsx` and `lib/comparison.ts`. The Try page also shows each demo sample's `title` and `expect`, which come from `backend/app/demo.py`.
- **What tests pin it.** The end-to-end demo test matches several strings exactly, such as "Send and watch it run" and "Waiting for you: message contains instruction-like text." `lib/story.test.ts` matches the outcome sentences. The README's GIF is built from the end-to-end test's frames, so new wording means a new GIF.
- **Traceability.** Frontend tests carry `[spec <capability>: <requirement>]` in their names ([0012](../../../docs/decisions/0012-frontend-test-traceability.md)), and backend tests use the `spec` marker ([0004](../../../docs/decisions/0004-spec-test-traceability.md)).
- **Generated text.** The build walkthrough renders specs and decision records. Decision records are never rewritten, so their text stays out of scope.

## Goals / Non-Goals

**Goals:**
- copy a reader can't mistake for a template, with every decision tied to whoever made it;
- the checkable rules enforced by the build, so new copy (such as the generated-request Try page) meets them without a review pass.

**Non-Goals:**
- the README, specs, and decision records;
- backend routing reasons ("capacity: no free large kennel for the stay"). They read as log lines, backend tests pin them, and the run view shows them as evidence;
- layout or visual changes.

## Decisions

### D1. The rules: a guide for judgment, a list for the build

The rules are adapted from the MIT-licensed checklist at github.com/hardikpandya/stop-slop and split by who can apply them:

| Rule | Applied by |
|---|---|
| Banned filler words and phrases ("simply", "exactly", "it's worth noting") | the copy check |
| No em dash inside a sentence | the copy check |
| Name who acted; avoid passive voice in sentences that report a decision | the outcome tests (`lib/story.ts`) and review |
| No contrast slogans ("X, not Y"), no three-part runs for rhythm, no punchline endings | review, using the guide |

The guide (`docs/style/interface-copy.md`) states each rule with a PawDesk example and lists three deliberate exceptions:
- **"never" and "every" may state a guarantee the tests prove,** such as "A model never approves a booking." The checklist bans them as vague; here they're the most precise claim available.
- **A list of three is fine when the things are three,** such as send, edit, or decline.
- **Short labels can drop the subject.** A state tag reads "Sent", not "The desk sent it."

Alternatives:
- **Guide only, no check.** The next feature would bring the filler back, and nobody would see it until a reader did.
- **A model-based style check in CI.** It costs money on every run, and two runs can disagree, which breaks "deterministic beats LLM". The banned list catches the cheap cases for free, and people judge the rest.
- **Everything in the decision record.** Decision records are immutable, and the word list will grow. The record says why the guide exists, and the guide holds the rules that change.

### D2. One list file, read by both test suites

`docs/style/copy-rules.json` holds `{"banned": [...]}`. The frontend check and the backend sample test both read it. A file outside both packages is a small coupling, but two lists would drift apart, and the scenario "One list for both checks" exists to catch that.

The first list, matched as whole words regardless of case: `just`, `simply`, `really`, `actually`, `exactly`, `truly`, `genuinely`, `honestly`, `literally`, `seamlessly`, `effortlessly`, `deeply`, `fundamentally`, `crucially`, `importantly`, `robust`, `powerful`, `leverage`, `unlock`, `delve`, `game-changer`, `it's worth noting`, `at its core`, `here's`, `let's dive`.

### D3. The frontend check reads the TypeScript syntax tree, not raw text

`tests/copy.test.ts` parses each `.ts`/`.tsx` file under `app/`, `components/`, and `lib/` (except `*.test.ts`) with the TypeScript compiler API, which is already a dev dependency. It collects:
- JSX text;
- string literals and template literal parts.

It skips:
- import and export paths;
- the `"use client"` directive;
- any string inside a `className` or `style` attribute;
- object keys.

Comments aren't in the tree, so they're skipped too. Each finding reports file, line, and the matched word.

Alternative: a regex over the file text. It would match comments and Tailwind class strings. Whole-word matching protects `justify-self-end` from "just", but not a comment such as `// just in case`. The syntax tree costs about forty lines and has no false positives from code.

Known gap: class strings kept outside a `className` attribute, such as the `TONE` map in `components/ui.tsx`, are scanned as text. None contains a banned word today. If one ever does, the check reports it and the fix is to rename the class, which is cheap.

### D4. Outcome sentences come from one function, tested per actor

`outcome()` in `lib/story.ts` already builds the sentence. It changes to:

| State | Before | After |
|---|---|---|
| sent, no approval | Sent automatically. Every check passed and the reply promised nothing more. | The checks passed it, so it went out without a person. |
| sent, approved | Sent after Dana approved the reply. | Dana approved the reply, and the desk sent it. |
| sent, edited | Sent after Dana edited the reply. | Dana edited the reply and sent it. |
| sent, rejected | Declined by Sam. A polite decline was sent. | Sam declined the request, and the pet parent got a polite no. |
| failed | Stopped while approved. It can be retried. | Stopped while sending the reply. Processing it again resumes from that step. |

The failed sentence maps each `failed_step` state to plain words: `received` and `extracting` → reading the request; `checking` → running the checks; `resolving` → looking for other options; `drafting` → writing the reply; `ready` → approving the reply (the checks' approval runs in that state); `approved` and `rejected` → sending the reply. A state missing from the map falls back to "working on it", so a raw name never shows. The resume claim holds: `process_request` retries a failed request from `failed_step`, and every state is a step it can resume. Resuming runs from the command line, so the sentence says "processing it again" and doesn't suggest a button.

### D5. The rewrite, page by page

The full before and after for every string goes in the build commits. The table shows the changes that carry a rule:

| Where | Before | After | Rule |
|---|---|---|---|
| Home, none waiting | Every request so far was decided by the checks or already handled by staff. | The checks or your staff have decided every request so far. | name the actor |
| Home, some waiting | Each one needs a person before anything is sent. The rest were decided by the checks. | A person decides each one before anything goes out. The checks decided the rest. | name the actor |
| Try page intro | …watch the desk handle it live, with real model calls. Samples are handled as of March 3, 2027, the day their certificates were made for. | Pick a sample from a made-up pet parent, send it, and watch each step run with real model calls. The desk treats today as March 3, 2027, so the sample certificates' dates line up with the stays. | passive, clarity |
| Sample "Clean boarding request" | Every check passes: drafted, approved by the system, and sent. | The checks pass it and the reply goes out with no person involved. | three-part run |
| Sample "Prompt injection attempt" | The instruction-like text is flagged in code; the request waits for staff. | Code spots the planted instruction and holds the request for staff. | passive |
| Sample "Expired vaccine" | Compliance fails; the resolver proposes an updated record; staff review. | The vaccine check fails. The resolver suggests an updated record, and staff review the reply. | staccato clauses |
| Sample "Pet not on file" | Intake can't match the pet; no agent runs; a person follows up. | Intake can't find the pet on file, so the request goes to a person. | staccato clauses |
| Metrics intro | Costs are exactly what the model provider reported… Nothing here is estimated. | Costs are the amounts the model provider reported for each call. Times run from each step's recorded start to its end. | adverb, punchline ending |
| Metrics charts | Where the money goes / How long each model step takes / Where requests are now | Cost by model step / Average time per model step / Requests by state | cute headings |
| Evals intro | How well the model steps do on labeled, synthetic examples. | Scores for the model steps on labeled synthetic examples. | fragment opener |
| Evals measure | Wrong decisions nobody would notice | Wrong decisions not sent to a person | vague extreme |
| Evals measure | Messages read completely right | Messages with every field right | adverb |
| Comparison intro | The same N booking requests, the same model, and the same checking tools. … An unsafe confirmation is a booking confirmed that should not have been. | Both ran the same N booking requests with one model and one set of checking tools. … An unsafe confirmation counts a reply that confirmed a booking the checks would have stopped. | three-part run, passive |
| Run view | The desk's path / Select a step to see exactly what it was given and what it returned. | Steps / Select a step to see its input and output. | cute heading, adverb |
| Run view panels | What they asked / What was sent / Why it went this way / Every step it took | Message from the pet parent / Sent reply or Draft reply / Routing reasons / State changes | Wh- headings |
| Run view option | Checked and works | Verified by the checks | vague |
| Review card | There is no drafted reply for this request, so it can't be sent from here. | This request has no draft, so you can't send it from here. | passive |
| Build page intro | …every change, every requirement with the tests that prove it, and every decision. Nothing on these pages is written by hand. | The changes, requirements, tests, and decision records on these pages come from the repository and the latest test run. The method section below is written by hand. | false claim, three-part run |
| Build method title | Models are measured, not trusted | Model steps are scored and traced | contrast slogan |
| Build method text | A record is never rewritten; a changed mind is a new record. | A committed record stays as written. A new record replaces it when the decision changes. | quotable |

Strings with no rule broken stay as they are, such as "Review queue", "Send reply", and "Nothing is waiting for you."

## Risks / Trade-offs

- [The banned list will flag a legitimate use one day, such as "just" in a pet's care note shown as an example] → User data never passes through the check, since it scans source and not rendered pages. A source string that needs the word can be reworded.
- [The generated-request change (`demo-generated-requests`) is in progress and adds Try page copy] → When that branch merges `main`, the copy check runs on its new strings and reports anything banned. Its scenario text ("Bordetella expired on March 1, 2027.") already follows the rules.
- [Copy quality beyond the list depends on review] → The guide gives each rule a PawDesk example, so a reviewer has something concrete to compare against.
- [Exact-text assertions in the end-to-end test break on every wording change] → The test updates in the same commit as the copy. The GIF is regenerated in a later commit from the new frames.
