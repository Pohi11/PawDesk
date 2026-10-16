# Design

## Context

- **`makeOne` selects "Make one up" and then fetches a generated request.** The panel calls it from a mount effect so the page opens with a request in the preview (change sample-request-summaries), and from the "Make one up" and "Make another" buttons.
- **The mount effect runs after the page becomes interactive.** A click that lands between hydration and the effect is applied first, and the effect's selection then replaces it. In the failing trace, the click finished at 27,934 ms and the generate request started at 27,926 ms.
- **Choosing a sample after the effect has run already works:** the generated request only fills its own preview when it arrives.

## Goals / Non-Goals

**Goals:** the visitor's latest choice is the one shown and sent, however quickly it is made.

**Non-Goals:** changing what the page opens on, or the busy state while a request is made up.

## Decisions

### D1. Split selecting from generating
- **`generate()` fetches and stores a made-up request;** `makeOne()` selects "Make one up" and calls it. The mount effect calls `generate()` only.
- **No new state:** the initial selection is already "Make one up", so the mount effect never needed to set it.
- **Alternative considered:** waiting in the tests for the first request before choosing a sample. It hides the problem from the tests, but a visitor who clicks quickly still loses the choice.

### D2. A test that chooses a sample while the opening request is pending
- **The test holds the generate response,** chooses the clean sample, then lets the response through, and checks the clean sample's summary is still shown and sent.
- **It can't force the exact interleaving** of the click and the mount effect, which depends on timing in the browser. The fix removes that interleaving's effect, and repeated end-to-end runs check it: before the fix, about 1 in 25 demo tests failed this way locally.
