# Proposal

## Why

The dashboard opens on the requests list, which assumes the visitor already knows what PawDesk is. Most visitors to the demo arrive cold: they want to try a request, and they need a few plain sentences first on what the desk does and why it was built. Today the explanation lives in the README, which a visitor to the hosted demo never sees.

## What Changes

- **The home page (`/`) becomes the Try page with an introduction.** It opens with a plain-language description of PawDesk and links to the rest of the dashboard, then shows the Try panel, so a visitor can send a request without leaving the page.
- **Below the panel, the page explains the project:**
  - how a request moves through the steps, and which steps are model, code, or a person;
  - the rules that keep a model from approving a booking;
  - the dashboard's other pages and what each one shows;
  - why the project was built, and how its skills map to the code;
  - the technologies used;
  - the method: spec-driven changes, decision records, tests linked to requirements, and an AI coding assistant whose output is reviewed against the spec and the tests.
- **The requests list moves to `/requests`.** The navigation's Requests link and the run page's back link point there.
- **`/demo` redirects to `/`,** so existing links keep working.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: a home page that introduces PawDesk and holds the Try panel; the requests list at `/requests`.

## Impact

- **Frontend:**
  - `app/page.tsx` (the new home page);
  - `app/requests/page.tsx` (the requests list, moved from `app/page.tsx`);
  - `app/demo/page.tsx` (a redirect);
  - `app/layout.tsx` and `components/run-view.tsx` (links).
- **Backend:** none.
- **Tests:** an end-to-end test for the home page, the redirect, and the list's new address; existing end-to-end tests updated to the new addresses.
