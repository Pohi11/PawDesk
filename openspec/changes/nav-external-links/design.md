# Design

## Context

- **The navigation bar lives in `app/layout.tsx`** and wraps every page: the logo, the review queue pill, then the page links.
- **These two links leave the dashboard,** unlike every other link in the bar, so they should look and behave differently from the page links.

## Goals / Non-Goals

**Goals:** a visitor can find the source code and the portfolio from any page in one click, on desktop and on a phone.

**Non-Goals:** a footer, social links, or a repository star count.

## Decisions

### D1. Right end of the bar, set apart from the page links
- **`ml-auto` pushes the pair to the right edge,** the usual place for links that leave a site. On a narrow screen the bar already wraps, and the pair wraps as one group, still right-aligned.
- **Pill buttons rather than plain text links,** so they read as exits, not as more dashboard pages. "Source code" is outlined with the GitHub mark, like the review queue pill. "Portfolio" is filled with ink, since it is the main place to go after the demo.

### D2. New tab, safely
- **`target="_blank"` keeps the dashboard open,** which matters when a run is streaming live.
- **`rel="noopener noreferrer"`** stops the new page from reaching back through `window.opener`.
- **A visually hidden "(opens in a new tab)"** goes into each link's accessible name, so screen reader users are not surprised by the new tab. Sighted users see a small arrow icon instead.

## Risks / Trade-offs

- [The repository URL is hard-coded] → It is one constant in `app/layout.tsx`, and the end-to-end test checks it, so a rename shows up as a failing test.
