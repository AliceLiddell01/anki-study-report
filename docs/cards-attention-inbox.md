# Cards attention inbox

## Status

This contract owns `C1.5R.5 — Cards attention inbox redesign` for `#/cards`.
It replaces the rejected spreadsheet-like C1.5 table. Owner product acceptance
remains separate and belongs to the integrated R7 package.

## Selected structure

```text
Variant A — identity-led dense inbox

wide desktop (>= 1200 CSS px)
compact summary and filters
ordered inbox list | persistent Inspector

narrow desktop (< 1200 CSS px)
compact summary and filters
full-width inbox list
non-modal detail drawer after explicit activation
```

The old table is not retained behind a switch, feature flag, hidden fallback or
responsive alias. Tiles, tabs, an ARIA grid and listbox semantics are rejected.

## Queue semantics

The queue is an ordinary semantic ordered list. Each list item contains exactly
one native button and therefore one tab stop. The button:

- exposes compact card identity as its accessible name;
- describes priority, primary reason, bounded evidence, metadata and note scope;
- uses `aria-current` for the active item;
- controls the current detail region;
- uses `aria-expanded` only in drawer mode;
- contains no nested actions, checkbox, menu, preview or media read.

Focus and active state are independent. Enter/Space/click activate an item; focus
does not move to the detail surface. The current item has both textual and visual
state and never relies on color alone.

## Item anatomy

Visual scan order is:

1. categorical priority and stable queue position;
2. compact R1 card identity, bounded to two lines;
3. primary localized reason and additional-reason count;
4. one bounded evidence sentence;
5. deck, card state and useful note-type metadata;
6. note scope/sibling impact where applicable;
7. detail affordance.

Numeric risk, raw reason codes, IDs, raw evidence objects, queries, fingerprints,
profile/check IDs and preview HTML are excluded from the queue.

## Detail surfaces

`CardsDetail` is shared by the wide Inspector and narrow drawer. Exactly one detail
surface and one active preview host may be exposed at a time.

Wide Inspector:

- persistent semantic `aside`;
- sticky and independently scrollable when required;
- width `clamp(380px, 34vw, 520px)`;
- queue column never shrinks below 560 px.

Narrow drawer:

- semantic labelled `aside role="region"`;
- fixed below the application header;
- `min(640px, 100vw - 32px)` maximum geometry;
- no `aria-modal`, backdrop, inert application shell or focus trap;
- queue remains operable;
- Escape and visible close control dismiss it;
- close restores focus to the exact activating item or queue heading fallback;
- activating another item updates the open drawer.

The existing `AccessibleModal` remains the only answer-preview modal. Its focus
trap, portal and inert application boundary are preserved; Escape closes that
modal before the drawer.

## Detail content and preview

Detail order is:

1. priority and full compact identity;
2. deck, note type and card state;
3. every canonical reason with priority, scope, source and bounded evidence;
4. R3 safe native front preview;
5. answer expansion through the existing true modal;
6. read-only recommended step;
7. Open in Anki and Inspection Profile handoff where applicable;
8. collapsed safe technical identity.

Only the active item requests Search inspect schema v2. Queue items never render
preview HTML or read media. One inspect cache is shared across Inspector/drawer and
answer expansion; the latter performs no second preview request.

## Learning period

Learning period is explicit, session-local product state with presets:

```text
7 days (default)
30 days
90 days
```

It changes only period-bound learning reasons/evidence. Current-content checks use
the current collection and are not represented as period-bound. A period change:

- aborts the previous query and any continuation;
- starts one Triage schema v4 automatic request with `contentCursor: null`;
- clears accumulated content pages;
- preserves local filters;
- retains the active item only when the new response contains it;
- prevents stale inspect/query responses from winning.

Clear filters resets priority/reason/deck/text and leaves the learning period
unchanged.

## Manual content continuation

Continuation is available only when both v4 content cursor surfaces coherently
report `truncated=true` and the same non-null cursor.

One explicit activation sends exactly one automatic Triage v4 request with:

- the current period/deck scope;
- the current `contentCursor`;
- the existing response limit.

There is no automatic cursor loop. `mergeTriagePages()` uses maps/sets to:

- dedupe items by `itemId`;
- merge reasons by `reasonId` without dropping prior reasons;
- dedupe sources and evidence;
- retain canonical identity and inspect target;
- select the strongest categorical priority;
- order accumulated items with the documented backend priority/reason/recency/ID
  comparator;
- add scanned/evaluated/failure progress;
- carry the latest coherent cursor;
- preserve existing issues after a continuation failure.

Client accumulation is bounded to 500 unique items and 10 additional content
pages. Reaching either bound is explicit and never claims collection completion.
An empty continuation batch advances progress/cursor and announces that no new
issues were found without replacing the queue with a global empty state.

Top-level `response.truncated` and content-source truncation are distinct:

- top-level truncation means only the first response-limit issues are shown and
  has no item cursor;
- content truncation means the current collection scan may continue manually.

## Filters and coverage

Always-visible compact controls:

- priority;
- family/exact reason;
- deck;
- local visible-text match;
- learning period;
- refresh;
- clear filters only when non-period filters are active.

Text filtering is client-only over loaded identity, deck, note type and localized
reason labels. It never becomes arbitrary backend query input.

Workspace coverage is summarized once rather than repeated per item. A native
`details` disclosure reports learning, content, profile and signal status plus
current scanned-note progress. Known error codes map to RU/EN safe copy; unknown
codes receive a controlled fallback. Profiles-needs-review and partial-source
warnings never hide usable learning issues or become fake queue rows.

## State matrix

The UI distinguishes:

- initial loading;
- query error and unavailable sources;
- successful empty;
- filtered empty;
- partial coverage;
- Profiles need review;
- top-level truncation;
- content continuation ready/loading/error/exhausted/capped;
- empty continuation batch;
- inspect loading/error/stale card;
- unavailable front or answer preview.

Continuation errors retain all prior issues and retry the same cursor. Query scope
changes clear stale details/drawer state.

## Accessibility and keyboard

- semantic list and native buttons;
- no `grid`, `listbox`, `option`, roving tabindex or arrow-key composite model;
- visible focus and textual active state;
- labelled/described items and detail region;
- live result announcements without per-row alerts;
- no color-only priority;
- no drawer focus trap or inert shell;
- exact focus restoration;
- reduced-motion drawer transition;
- modal answer behavior unchanged.

## Bounds and performance

The initial server response remains capped at 100 items. The loaded client queue is
bounded to 500 unique items. Filtering is local. Merge is map/set based. No item
installs a global event listener; only the active drawer owns an Escape listener.
Virtualization is not introduced because the measured 100/500-item fixture does
not require a second rendering architecture.

## Preserved contracts

- R1 compact identity and safe fallback states;
- R3 Inspector-front / expanded-answer preview semantics;
- R4 Triage schema v4, independent candidate sources and cursor coherence;
- Search inspect schema v2;
- loopback/token/content-type/body-size boundaries;
- sanitizer, trusted media validation and Shadow DOM preview isolation;
- read-only Cards actions.

## Boundaries

R5 does not implement Safe Actions, mutation, selection/bulk controls, manual
resolve, editor functionality, new detectors, Triage schema v5, Search schema
changes, Guided Inspection Profiles UX, R7 owner acceptance or C1.6.
