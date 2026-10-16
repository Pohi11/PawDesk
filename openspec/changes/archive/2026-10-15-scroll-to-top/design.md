# Design

## Context

- **The layout (`app/layout.tsx`) is a server component** that wraps every page, so one client component placed there covers the whole dashboard.
- **The tokens in `globals.css` give color a meaning:** orange only where a person must act, green for done. A navigation aid is neither, so it uses ink and white.
- **`globals.css` already shortens every transition** when the system asks for reduced motion, but `window.scrollTo({ behavior: "smooth" })` is not a CSS transition and needs its own check.

## Goals / Non-Goals

**Goals:** a visitor deep in a long page can get back to the top in one press, on desktop and on a phone.

**Non-Goals:** a table of contents or section links; changing the header into a sticky one.

## Decisions

### D1. Show it after one window height
- **Past one window height, the whole first screen is out of sight,** which is the point where scrolling back starts to cost something. Short pages never reach it, so the button never shows there.
- **The scroll handler is passive and runs at most once per animation frame,** so it does not slow scrolling.

### D2. Hidden means hidden for everyone
- **The button stays in the page while hidden** so it can fade and slide in, but it carries `inert`, which removes it from the tab order and the accessibility tree. A button that is invisible but still focusable would trap keyboard users on nothing.
- **When the button hides after a press,** focus falls back to the page, so the next Tab starts from the top, where the visitor now is.

### D3. A progress ring around the button
- **A thin ring fills from 0 to 100% as the page scrolls,** drawn with an SVG circle's `stroke-dashoffset`. It tells the visitor how much page is left, so the button earns its corner.
- **Ink fill, white arrow and ring,** a soft shadow, and a small lift on hover. It matches the header's quiet style and does not borrow a status color.

### D4. Smooth unless reduced motion
- **The press reads `prefers-reduced-motion` at that moment** and passes `behavior: "auto"` (an instant jump) when it is set, `"smooth"` otherwise.

## Risks / Trade-offs

- [The button covers a bit of content in the bottom right corner] → It is 48 px with a 16 px gutter on phones, and only appears mid-page, where the visitor is reading, not acting on, that corner.
