# Card preview semantics

## Contract

Compact Search/Cards identity and full card preview are separate systems.

- Queue rows use only compact identity.
- One active Inspector card receives one Search inspect payload.
- Inspector renders the sanitized native **front**.
- The expanded dialog renders the sanitized native **answer/back**.
- The frontend never concatenates front and back. Anki resolves `{{FrontSide}}` while rendering the answer.

## Native source

For Anki 26.05+, full preview calls `Card.render_output(reload=True, browser=False)` once. Its question, answer, CSS, question AV tags and answer AV tags are projected into the existing `RenderedCardPreview` payload. Browser Appearance remains exclusive to compact display identity.

If `render_output()` is unavailable, the explicit adapter uses reviewer `card.question(reload=True, browser=False)` and `card.answer()`. Unsupported signatures fail safely into the existing sanitized template renderer.

## Media and safety

Front replaces question AV markers. Answer replaces both question and answer AV markers because an answer may contain `FrontSide`. `mediaRefs` is a deduplicated union of both sides. Rendering never reads media bytes.

Sanitizer allowlists, URL/path validation, CSS redaction and Shadow DOM isolation remain mandatory. Card JavaScript, iframe/object/embed, remote/file URLs and token/path disclosure remain prohibited.

## Layout and accessibility

Inspector fits content to width inside a bounded vertically scrollable region. The answer dialog uses a wider content region, fits to width only and relies on natural modal vertical scrolling. Image and font readiness remeasure the layout.

The shared modal keeps the application shell inert, focuses the visible title, traps Tab/Shift+Tab, closes on Escape and restores focus to the invoking control when it still exists.

## Reads

Opening the answer dialog reuses the active inspect payload. Queue rows do not receive full preview data or media reads.
