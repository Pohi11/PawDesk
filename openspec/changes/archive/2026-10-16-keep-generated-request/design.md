# Design

## Context

- **`makeOne()` selects "Make one up" and calls `generate()`.** Both the "Make one up" choice and the "Make another" button call it, so the choice regenerates on every click.
- **The mount effect calls `generate()` once** to fill the opening preview (change keep-chosen-sample).

## Goals / Non-Goals

**Goals:** a made-up request changes only on page load or "Make another".

**Non-Goals:** keeping a made-up request across page reloads.

## Decisions

### D1. The choice selects; "Make another" generates
- **The "Make one up" choice calls `chooseGenerated()`,** which selects it and calls `generate()` only when there is no request and none is on its way. That covers an opening request that failed.
- **"Make another" keeps calling `makeOne()`.**
- **Edits to the message survive switching away and back:** they are keyed by the request's seed, which no longer changes on a click.
- **Alternative considered:** never generating from the choice. A visitor whose opening request failed would then have no way to retry except "Make another", which only shows once a request exists.

### D2. A test that switches away and back
- **The test counts generate calls,** chooses a sample, chooses "Make one up" again, and checks the heading is unchanged and no new call was made. It then clicks "Make another" and checks a second call was made.
