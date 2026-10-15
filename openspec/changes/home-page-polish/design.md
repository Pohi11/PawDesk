# Design

## Context

- **The home page** (change `home-page-intro`) has an introduction, the Try panel, and six sections: steps, rules, page cards, about with a skills list, method, and technology tags.
- **The dashboard's tokens** give color a meaning: violet for model steps, blue for code, amber for tools, orange where a person acts, green for done.
- **Interface copy** follows `docs/style/interface-copy.md` (decision record [0018](../../../docs/decisions/0018-plain-voice-for-interface-copy.md)).

## Goals / Non-Goals

**Goals:** a page that reads as written for this product, with one memorable element and fewer, plainer sections.

**Non-Goals:**
- new colors or fonts (the home page stays part of the dashboard);
- changes to the Try panel.

## Decisions

### D1. The introduction shows one request instead of describing the steps
- **The clean sample's message** appears as the pet parent wrote it. The pet, the dates, and the attached card carry violet marks (a model reads them). Under it, the checked facts carry blue marks (code decides them), and the outcome uses the dashboard's state tag.
- **Why this element:** it shows what PawDesk does with the product's own data and colors, where a stat row or a feature grid would fit any product.
- **On phones** it sits below the introduction, so the Try panel stays one scroll away.

### D2. Fewer sections, each holding one kind of content
- **Steps** are a sequence, so they keep their numbers, drawn as one timeline. The guarantees sit under them because they constrain those steps.
- **The posting table names the technologies,** so the separate tag list goes. The model and its provider move into the table.
- **The page cards repeated the navigation.** Each page is linked where the text mentions it (review queue, requests, evals, How it was built).
- **The method keeps numbers** because each change goes through the steps in order.
- **Counts stay generated** from the walkthrough, now inside a sentence instead of a figure row.

### D3. Copy
- **Active voice with a named actor:** "a model reads", "code checks", "someone on staff approves".
- **No all-caps labels, no slogan endings, and three-part lists only where there are three things.**

## Risks / Trade-offs

- [The worked example is hand-written and could drift from the sample] → It quotes the clean sample's message and the facts the end-to-end test asserts for that sample (Biscuit, March 24 to 27, sent with no review).
- [Next keeps the home page mounted, hidden, after a client-side navigation to a run page] → The example's outcome sentence is worded differently from the run page's, so tests that look that sentence up by its text find one element.
