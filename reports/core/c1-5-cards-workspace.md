# C1.5 — Canonical Cards workspace

**Current status:** `C1.5 — Design Gate complete, implementation in progress`

**Initial branch:** `core`

**Initial HEAD:** `205bf74af77160b346bf96ebb98c3f35bf824bb3`

**Initial divergence:** `0 behind / 17 ahead` of `origin/master`; `0 behind /
0 ahead` of `origin/core`

**Initial worktree:** clean

**Open pull requests from `core`:** none

## Design Gate

### Sources and constraints

The audit covered project roadmap/handoff, the Cards v2 product and triage
contracts, C1.2-C1.4 reports, current Cards/Search/preview/actions/frontend and
Python implementations, tests, Fast CI and real-Anki E2E harness.

Primary external sources applied:

- Anki Manual [Browsing](https://docs.ankiweb.net/browsing.html),
  [Searching](https://docs.ankiweb.net/searching.html), and
  [Card Templates](https://docs.ankiweb.net/templates/intro.html);
- Anki add-on docs [Background Operations](https://addon-docs.ankiweb.net/background-ops.html)
  and [The `anki` Module](https://addon-docs.ankiweb.net/the-anki-module.html);
- W3C APG [Table](https://www.w3.org/WAI/ARIA/apg/patterns/table/),
  [Grid](https://www.w3.org/WAI/ARIA/apg/patterns/grid/),
  [Grid and table properties](https://www.w3.org/WAI/ARIA/apg/practices/grid-and-table-properties/),
  [Modal dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), and
  [Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/).

Anki establishes native Browser/search identity and card/template variability;
the add-on guidance supports serialized collection reads. W3C sources support
native table semantics for a non-composite comparison surface and the modal
focus/portal contract. Product pattern reference: Linear Peek was reviewed;
the Sentry issue-details page returned a source-site error and was not used as
contract authority.

### Legacy baseline audit

Accepted C1.4 real-Anki artifact `29644836731` was generated from the unchanged
legacy Cards production page and provided twelve 1440 px full-page images:

- APKG: table, tiles and Anki preview in light/dark;
- synthetic Japanese/Programming: table, tiles and Anki preview in light/dark.

Observed full-page heights:

| Fixture | Table | Tiles | Anki preview |
| --- | ---: | ---: | ---: |
| APKG | 3,133 px | 3,826 px | 9,877 px |
| Synthetic | 5,743 px | 7,678 px | 19,232 px |

A fresh 1024 px light baseline was captured locally from current HEAD with the
development mock report. The first actionable table row began at 1,111 px,
below the 960 px initial viewport; full page height was 1,573 px for only three
rows.

Legacy duplication:

- hero diagnosis and five KPI cards classify the same items again;
- Risk/Gaps/Patterns/Check tabs overlap instead of representing workflows;
- the problem dropdown repeats the tabs/chips;
- table/tiles/Anki preview repeat the same queue at different costs;
- visible `riskScore` adds unexplained pseudo-precision;
- Anki preview renders full previews for every row and drives extreme height;
- keyboard users cross hero actions, many filters, four tabs, three display
  modes and batch actions before reaching rows;
- long deck/card names expand rows or are repeatedly clamped without a single
  persistent full-detail surface.

No screenshot is committed. Historical source inventory:
`artifacts/screenshots/cards/{apkg,synthetic}/{table,tiles,anki-preview}/{light,dark}.png`.
Fresh local baseline inventory:
`baseline-legacy-1024-light-table.png` in the temporary Design Gate directory.

### Functional prototypes

Two temporary, local-only prototypes used the same realistic triage v2-style
fixture and functional row activation/Inspector updates:

- A: native semantic compact table plus persistent Inspector;
- B: structured vertical list plus persistent Inspector.

Fixture coverage included mixed learning/content reasons, several reasons,
note scope/sibling count, long Japanese and Programming text,
suspended/buried/flag states, a profile warning, partial source, no problems,
100 bounded rows, preview loading and preview unavailable.

Temporary screenshot inventory (not committed):

- `prototype-a-1440-light.png`;
- `prototype-a-1440-dark.png`;
- `prototype-b-1440-light.png`;
- `prototype-b-1440-dark.png`;
- `prototype-a-1024-light-long.png`;
- `prototype-b-1024-light-long.png`;
- `prototype-a-1024-light-empty.png`;
- `prototype-a-1024-dark-100.png`;
- `prototype-a-1024-light-preview-unavailable.png`.

### Decision matrix

Scale: `strong`, `acceptable`, `weak`; it expresses observed suitability, not
false numeric precision.

| Criterion | Table A | List B |
| --- | --- | --- |
| Scanability | strong | acceptable |
| Comparison across rows | strong | weak |
| Information density | strong | acceptable |
| Long-text behavior | acceptable | strong |
| Queue/Inspector balance | strong | acceptable |
| Initial viewport efficiency | strong | acceptable |
| Keyboard tab path | strong | strong |
| Screen-reader semantics | strong | acceptable |
| Active-row clarity | strong | strong |
| Responsive adaptation | acceptable | acceptable |
| Implementation complexity | strong | strong |
| Future C1.6 selection | strong | acceptable |
| Incorrect ARIA risk | strong | strong |
| 100-row performance | strong | acceptable |

Table A is selected. It preserves stable cross-row comparisons, exposes more
items in the initial viewport, maps directly to native table semantics and has
a natural future selection column without implementing it now. At 1024 px,
secondary deck/state information can collapse while priority, card and reason
remain readable. List B is rejected because its long-text advantage belongs in
the persistent Inspector and does not compensate for weaker comparison/density.

The temporary prototype source was removed before production implementation.
The durable UI contract is
[`docs/cards-v2-workspace-ui.md`](../../docs/cards-v2-workspace-ui.md).

## Implementation

Pending.

## Verification evidence

Pending. This section will distinguish local checks, exact-SHA Fast CI,
targeted real-Anki E2E, screenshots, keyboard acceptance and closeout evidence.

## Scope boundary

C1.5 remains read-only. It does not implement C1.6 selection, Safe Action
mutation, recheck/resolution, PR/merge/release/deployment, AnkiWeb publication,
remote telemetry content, a duplicate preview endpoint or a hidden rejected
display mode.

