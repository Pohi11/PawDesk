# Design

## Context

- **`globals.css` draws a 2 px `--color-code` (blue) outline on `:focus-visible`.** Browsers treat a tapped text field as `:focus-visible`, so the ring appears on touch too.
- **Mobile Chrome and Safari paint a tap highlight** (`-webkit-tap-highlight-color`) over any pressed link or button, separate from the focus ring.

## Goals / Non-Goals

**Goals:** no blue flash or ring when a visitor taps something on a phone.

**Non-Goals:** removing the keyboard focus ring; restyling controls.

## Decisions

### D1. Turn the tap highlight off everywhere
- **`-webkit-tap-highlight-color: transparent` on `html`** is inherited by every element. Buttons and links keep their own hover and pressed styles, so a press still gives feedback.

### D2. Drop the outline only where touch is the main pointer
- **`@media (hover: none) and (pointer: coarse)`** matches phones and tablets used by finger, not a laptop with a touch screen, whose main pointer is still a mouse.
- **Inside it, text fields, menus, and radios lose the `:focus-visible` outline.** Those are the controls a browser marks focus-visible after a tap; the caret, the on-screen keyboard, or the picker already shows their focus.
- **Buttons and links keep the rule.** A tap does not make them focus-visible, so their ring only appears when someone uses a keyboard.

## Risks / Trade-offs

- [A phone or tablet paired with a hardware keyboard shows no ring on a text field] → The caret still marks the field, and every other control keeps its ring.
