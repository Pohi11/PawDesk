# Design

## Context

- **The Try panel is `<section id="try">` on `/`,** below the introduction and the worked example. The hero's own "Try a request" link already points at `#try`.
- **The navigation's link points at `/`,** a leftover from when the Try panel had its own page.

## Goals / Non-Goals

**Goals:** every "Try a request" link lands on the Try panel.

**Non-Goals:** moving the Try panel higher on the page, or highlighting the current page in the navigation.

## Decisions

### D1. Link to `/#try` with the Next.js `Link`
- **One address works from every page:** from another page Next.js loads `/` and scrolls to the element with id `try`; on `/` it only scrolls. The section's `scroll-mt-6` keeps the heading clear of the top edge.
- **Alternative considered:** a click handler that calls `scrollIntoView`. It needs client code in the layout and does nothing a fragment link doesn't already do.

## Risks / Trade-offs

- [Following the link on `/` twice does nothing the second time] → the address doesn't change, so the browser has nowhere new to scroll. The panel is already in view by then.
