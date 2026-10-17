# Design

## Context

- **The dashboard sets `cacheComponents: true`.** With it, Next.js keeps the page being left mounted but hidden (React `<Activity>`) and shows it again, with its state, on Back or on a link to the same route.
- **The panel's `busy` flag covers both sending and making up a request.** `send()` sets it and clears it only when the send fails. On success it calls `router.push` and relies on the panel unmounting, which no longer happens, so the panel comes back with `busy` still set.

## Goals / Non-Goals

**Goals:** the panel is usable after coming back from a run, by Back or by link.

**Non-Goals:** turning off `cacheComponents` or the kept page state. Keeping the chosen request and edits to its message across a visit to a run is useful.

## Decisions

### D1. A separate `sending` flag, cleared when the panel is hidden
- **`sending` is its own state.** Both buttons are disabled while either `busy` (making up a request) or `sending` is set, as before.
- **An effect's cleanup clears `sending`.** React runs effect cleanups when an `<Activity>` boundary hides its content, and runs the effects again when it is shown, while state is kept. Hiding happens after the navigation to the run has been committed, so the send has done its job by then. On a real unmount the cleanup's state update does nothing.
- **Why not reuse `busy`:** clearing it could re-enable "Make another" while a request is still being made up, and its result would then race the visitor's next click.
- **Alternatives considered:**
  - **Clearing the flag right after `router.push`.** `push` returns before the run page has loaded, so the button would read "Send and watch it run" again for a moment while the run opens, inviting a second send.
  - **Listening for `pageshow`.** It covers the browser's back-forward cache after a full page load, not a client-side navigation, which is what happens here.
  - **Turning off `cacheComponents`.** It loses partial prerendering and the kept page state for one flag.

### D2. Tests for both ways back
- **One end-to-end test per way back:** send the clean sample, wait for the run, go back with browser Back or the navigation's "Try a request" link, and check the send button is enabled and none is labelled "Sending". Both fail without the fix.
