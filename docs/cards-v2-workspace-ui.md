# Cards v2 Workspace UI

## Status and boundary

This C1.5 contract is retained as historical technical evidence. Owner product
acceptance was withdrawn after screenshot and real-profile review; C1.5R
supersedes the native-table Design Gate with a dense structured inbox list,
correct compact identity, explicit period/source semantics, native front in the
Inspector, and native answer/back in the expanded modal. C1.5R does not add bulk
selection, mutation, Safe Actions, recheck/resolution, a card editor, an ARIA
grid, or a second preview renderer. Those C1.6 concerns must not be implied by
inactive controls.

The queue consumes triage schema v2. Card details and the active preview reuse
the existing bounded Search inspect surface; opening Anki reuses the exact-ID
`open-search-selection` action. All rendering remains local and read-only.

## Design Gate decision

Selected structure: a native semantic compact `<table>` plus persistent
`<aside>` Inspector on wide desktop.

Rejected structure: a vertical list of structured interactive articles plus
the same Inspector. The list gave long Japanese and Programming text more
horizontal freedom, but repeated metadata positions, reduced comparison across
rows and showed fewer candidates per viewport. It did not outperform the
table on narrow desktop or accessibility strongly enough to overturn the
default.

An interactive ARIA grid was not prototyped. Cards requires row activation,
ordinary controls and reading/comparison—not spreadsheet cell navigation. A
grid would add composite focus and keyboard obligations without a current user
capability that needs them.

Qualitative scale: `strong`, `acceptable`, `weak`.

| Criterion | Native table | Structured list | Decision evidence |
| --- | --- | --- | --- |
| Scanability | strong | acceptable | stable columns expose priority, card and reason |
| Row comparison | strong | weak | list metadata must be rediscovered per item |
| Information density | strong | acceptable | table shows more candidates in the initial viewport |
| Long text | acceptable | strong | two-line clamping preserves the queue; full text is in Inspector |
| Queue/Inspector balance | strong | acceptable | table uses the wider pane efficiently |
| Initial viewport | strong | acceptable | first row follows compact summary and filters |
| Keyboard tab path | strong | strong | one activator per row in either model |
| Screen-reader semantics | strong | acceptable | native headers preserve cross-row meaning |
| Active-row clarity | strong | strong | textual/visual current-row state in both |
| Responsive adaptation | acceptable | acceptable | secondary columns collapse before the panes stack |
| Implementation complexity | strong | strong | both avoid composite widgets |
| Future C1.6 selection | strong | acceptable | a future checkbox column has a natural location |
| Incorrect ARIA risk | strong | strong | both use native semantics; no grid |
| 100-row performance | strong | acceptable | compact rows and no inactive preview reads |

## Desktop and responsive layout

Wide desktop uses:

```text
page heading + short read-only description
compact bounded summary and filters
workspace/profile/source warnings when present
native triage table                 | persistent Inspector
```

The Inspector is sticky within the viewport, independently scrollable when
needed and does not shrink the queue below a readable width. At approximately
1024 px, the least important queue metadata moves to the row secondary line or
is hidden while priority, primary text and primary reason remain visible. The
queue and Inspector still share the viewport. Below the usable split threshold
they stack in document order: filters, queue, Inspector. There is no draggable
splitter.

Horizontal overflow is a last resort; the chosen fallback removes secondary
columns before requiring it. The expanded preview modal remains usable at
1024 px and portals outside the inert application shell.

## Compact summary and filters

The summary states returned/candidate counts and discloses the automatic
100-item cap and truncation. Counts describe the current bounded response,
not an invented global total.

Always-visible controls are deliberately small:

- priority;
- reason family or exact reason;
- deck;
- visible-text filter;
- refresh.

Card state/source/profile filters may appear in an advanced disclosure if the
fixture proves they are needed. The default request is the automatic dataset,
seven-day learning window, selected deck IDs when available, and limit 100.
Filters never recreate Risk/Gaps/Patterns/Check tabs. Empty filtered results
keep controls visible and offer a clear/reset action.

## Queue semantics and row anatomy

The queue is a native table with real column headers. It is not an ARIA grid,
does not implement arrow-key cell navigation and has no bulk checkbox in C1.5.
Each data row exposes one predictable activation control covering the row's
summary. Internal actions are not repeated in every row.

Required scan-path information:

1. textual High/Medium/Low priority;
2. compact primary/front text;
3. primary reason label;
4. additional-reason count when non-zero;
5. one bounded evidence summary;
6. deck and relevant state;
7. note scope/sibling effect when the primary reason is note-scoped.

The queue does not show `riskScore`, raw queries, full evidence objects, full
previews, every metric, template diagnostics, legacy tabs, tiles, or Anki
preview display modes. Long text is clamped in the row and available in full
in the Inspector. A long deck name wraps or truncates with its exact value
available in accessible text/title; it cannot expand the table indefinitely.

## Active item and focus

Active item and keyboard focus are separate states. Enter or Space on a row
activator updates `aria-current`, Inspector details and the active preview.
Click activation behaves identically. Activation never moves focus into the
Inspector. Tab continues through ordinary controls; no roving tabindex or
arrow-key contract is invented.

Latest activation wins. An earlier inspect response is aborted or ignored.
Refreshing preserves the active card only when the exact card remains in the
new response. An empty queue clears the Inspector. A deleted/stale active card
shows an unavailable state without resurrecting a row.

Focus indicators do not rely on color alone. Priority labels, warning text,
active-row semantics, loading announcements and action results remain textual
in light and dark themes.

## Inspector anatomy

The Inspector has an accessible heading and these sections:

1. priority, full primary text, deck, note type/template and relevant state;
2. safe active-card preview with loading/unavailable status;
3. all canonical reasons, not only a count;
4. bounded evidence, window/freshness/source and note/card scope;
5. exact card/note technical identity in a secondary disclosure;
6. recommended read-only step;
7. `Open in Anki`, `Review Inspection Profile` when applicable, and Refresh.

Reason text is derived from stable reason codes. Evidence displays only the
allowlisted typed fields in triage v2. It does not echo raw note values,
queries, tokens, media paths or template source. A note-scoped reason names
the sibling impact once; it does not create fake sibling rows.

## Preview behavior

Only the active item starts a Search inspect request. Queue rows never fetch
rendered HTML/media. The existing Search inspect response is extended
additively to carry the same sanitized `RenderedCardPreview` shape already
used by `AnkiCardShadowPreview`; no duplicate detail endpoint is introduced.

Inspector preview behavior:

- bounded height and internal scrolling;
- `AnkiCardShadowPreview` Shadow DOM isolation;
- token-protected validated media URLs;
- no iframe, template JavaScript or raw `innerHTML` in the application DOM;
- preview loading/failure announced without hiding reasons or actions;
- no duplicate fetch when expanding an already-loaded preview.

`Expand preview` uses `AccessibleModal` with `portal`. Focus moves inside,
stays contained, Escape and a visible close button dismiss it, and focus
returns to the trigger. The modal renders the same cached sanitized preview.

## Workspace state matrix

| State | Queue | Inspector / action behavior |
| --- | --- | --- |
| Loading | compact skeleton/status | no stale active details |
| Ready | canonical ordered rows | active exact-card inspect |
| No problems | explicit success-empty copy | no active card |
| Filtered empty | controls retained, clear filters | no active card |
| Partial source | available rows plus source warning | reason/source limitations remain visible |
| Profiles need review | one workspace warning | link to Inspection Profiles; no fake queue rows |
| Truncated | `100` plus cap disclosure | inspected rows remain exact |
| Query error | retryable workspace error | no broken row actions |
| Inspect loading | active row retained | announced loading; reasons remain visible |
| Stale/deleted card | row may disappear on refresh | typed unavailable state and retry/refresh |
| Preview unavailable | row/details remain | explicit preview fallback; Open in Anki remains safe |
| Open action failure | queue unchanged | announced error and retry |

## Design examples

### Japanese: missing audio plus repeated Again

`覚える（おぼえる）` appears once, High, with `Missing audio` as the primary
reason, `+1 reason`, `note · 2 sibling cards`, and a bounded Again summary.
The Inspector explains the confirmed/current profile requirement and the
card-level repeated-Again evidence separately.

### Programming: low pass rate

A long Promise/microtask question is clamped to two lines. `Low pass rate` and
the bounded percentage/answer count remain comparable in their columns. The
Inspector shows the complete question and evidence window.

### Note-scoped missing field

One deterministic representative card states `Missing example · note scope ·
3 sibling cards`. Sibling cards are not duplicated unless they have their own
independent card-level learning reasons.

### Multi-reason item

The row shows the deterministic primary reason and `+2 reasons`; the Inspector
lists all three with family, scope, source and typed evidence. No numeric risk
score substitutes for the explanation.

### Partial source

One workspace-level warning names the unavailable source. Learning history and
confirmed content items that are still valid remain usable. The UI does not
claim complete coverage.

### Profiles need review

One warning links to `#/settings/inspection-profiles`. It explains suppressed
content checks. It does not create one system item per profile and does not
hide independent learning reasons.

### Stale or deleted card

Search inspect returns the typed not-found error. The Inspector says the card
is no longer available and offers Refresh. It neither builds a raw Browser
query from display text nor marks the issue resolved.

### Empty result

The queue states that no current issues were found for the selected scope and
keeps filters/Refresh available. This is distinct from unavailable or partial
sources.

### Truncated automatic queue

The summary says `Showing 100 · more candidates exist`. Ordering remains the
canonical server order. There is no client-side promise of a total beyond the
bounded response.

## Open in Anki and C1.6 boundary

`Open in Anki` sends the active exact card ID through the existing token-bound
`open-search-selection` action with `mode: "cards"`. Display text never becomes
an arbitrary native query. Success only means the Browser open request was
accepted; it does not resolve, mutate, or recheck the issue.

C1.6 may add explicit selection, contextual bounded Safe Actions, recheck and
resolution state. It must preserve active item separately from selection and
must earn any additional keyboard model. C1.5 intentionally provides no dead
checkbox, mutation button, awaiting-recheck state, or hidden rejected mode.

## C1.5R.3 preview semantics

See [`card-preview-semantics.md`](card-preview-semantics.md). Full preview uses reviewer/native front and answer; Inspector shows front, expanded dialog shows answer, and compact identity remains unchanged.
