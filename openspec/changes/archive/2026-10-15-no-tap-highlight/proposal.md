# Proposal

## Why

On a phone, tapping a button, a link, or a text box draws a blue box or ring around it. The browser's tap highlight and the focus ring both show up on touch, where the visitor already knows what they tapped, so the page flashes blue on every press.

## What Changes

- **No tap highlight:** the dashboard turns off the browser's tap highlight on every element.
- **No focus ring on tapped text fields on touch screens:** a tapped text box, menu, or radio already shows focus through the caret, the on-screen keyboard, or the picker, so the outline is dropped on devices whose main pointer is a finger.
- **Keyboard focus is unchanged:** a visitor who moves with Tab still sees the focus ring on every control.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `run-dashboard`: tapping on a touch screen draws no highlight.

## Impact

- **Frontend:** `app/globals.css` only.
- **Tests:** an end-to-end test that emulates a phone and a desktop keyboard.
