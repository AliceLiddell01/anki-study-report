# C1.5 — Canonical Cards workspace

**Current status:** `C1.5 — Complete`; `C1.6 — Next, not started`

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

`#/cards` now reads automatic triage schema v2 for the selected deck scope,
seven-day period and bounded limit 100. The workspace keeps active item state
across refresh when possible, aborts superseded requests and applies Search
inspect responses latest-wins.

The production UI is one native table queue plus a persistent Inspector:

- categorical priority, primary text, reason, bounded evidence, deck and state;
- filters for priority, reason family, deck and visible text;
- one active row independent of keyboard focus;
- one sanitized Shadow DOM preview for the active item only;
- portal-based expanded preview that reuses the inspected detail;
- exact-card `open-search-selection` handoff to Anki Browser;
- explicit loading, unavailable, partial, filtered-empty and profile-review
  states;
- no legacy tabs, display switch, `riskScore`, duplicated row previews,
  checkbox, mutation or resolution loop.

Search inspect card details add the existing bounded `renderedPreview` shape.
The change is additive under Search inspect schema version 1; preview
sanitization and media validation remain backend responsibilities.

The real-Anki browser harness now captures workspace light/dark, expanded,
1024 px and APKG-filtered proof. It checks the 100-row performance contour,
keyboard activation, one preview host, exact-card open action, portal modal,
no legacy controls and no horizontal document overflow.

## Verification evidence

### Local automated checks

- `python -m compileall -q anki_study_report docker/anki-e2e`: PASS;
- focused frontend Cards/hook/Search API: 37 PASS;
- focused Python Search/triage/package/E2E helpers: 65 PASS;
- Search/localization regression contour: 17 PASS;
- `node --check docker/anki-e2e/smoke-browser.mjs`: PASS;
- `pnpm run build:addon`: PASS; 17 JS chunks, 457,930-byte largest/entry
  chunk, add-on asset copy complete;
- `.\scripts\run_full_check.ps1 -SkipDocker`: PASS; 52 frontend files / 278
  tests, 708 Python tests PASS, 4 environment-specific symlink/Bash checks
  skipped, package build and validation PASS.

The Python run emitted only the known local `.pytest_cache` access warning.
Generated `__pycache__` directories were removed before the canonical gate.

### Local browser Design/implementation proof

Temporary Chromium screenshots covered 1440 light/dark, expanded preview and
1024 light. The rebuilt 1024 production bundle measured 509 px queue / 376 px
Inspector, zero document overflow, nine rows, one active row and one preview
host. Keyboard Enter activated the next row without moving focus to Inspector;
Escape closed the portal modal and restored the trigger focus. No screenshot or
local server fixture is committed.

This is local synthetic/manual browser evidence, not real-Anki acceptance.

### Cloud acceptance

Accepted implementation HEAD:
`0460afe472cd87029368924bdf5640e90271c03c`.

- Fast CI [`29648956309`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29648956309):
  PASS on the exact accepted HEAD;
- exact package artifact `8430913583`, diagnostics artifact `8430913479`;
- targeted Full Docker / Anki E2E
  [`29649071545`](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29649071545):
  PASS, `standard/cards`, `verify_restart=true`, exact source Fast CI
  `29648956309` and exact package hash verified;
- redacted E2E artifact `8430943370`, digest
  `sha256:332082fda809c1fed0be902a89065c9232a403fd1f5ba15512a23ca86ea3ea9d`;
- artifact manifest: SUCCESS; 28 screenshots total, including four synthetic
  Cards workspace screenshots and one APKG workspace screenshot;
- browser proof: 12 queue rows, one Inspector, one preview host, no checkbox,
  legacy mode or risk score, zero document overflow, no actionable request,
  console or page errors;
- 1024 proof: 518 px queue / 383 px Inspector, zero overflow;
- APKG proof: eight filtered rows, one active preview, native media rendering;
- expanded modal proof: inert and `aria-hidden` app shell, portal outside the
  shell, one dialog;
- restart API proof: 23 cards, 10 APKG attention cards, native render source,
  Japanese profile moved to `needs_review`, Programming stayed `confirmed`,
  learning reason remained, and profile evidence leaked no values.

The accepted screenshots were manually reviewed. Light/dark density, active
row, long text, Inspector balance, preview isolation, expanded modal and 1024
layout were visually coherent; no screenshot is committed.

Diagnostic runs before acceptance are retained rather than hidden:

- `29647972946`: FAIL because Search parser rejected backend
  `fallbackReason: null`; fixed by `15fab44`;
- `29648324031`: FAIL on an over-exact APKG deck label selector; fixed by
  `46004cb`;
- `29648565541`: FAIL on legacy exact Cards H1 checks after the product H1
  changed; fixed by `e8f4b7f`;
- `29648810472`: browser and restart smokes passed, but wrapper retained legacy
  6+6 screenshot counts; fixed with a regression test by `0460afe`.

The documentation-only closeout commit is followed by one final exact-SHA Fast
CI. Its run ID is reported in the final response without a self-referential
second documentation commit. Per policy, no second Docker run follows docs-only
closeout.

## Commits

- `0c536f9` — Design Gate contract and prototype decision;
- `45acab4` — canonical Cards queue/Inspector implementation and coverage;
- `15fab44` — native preview nullable fallback parity;
- `46004cb` — APKG deck E2E selector;
- `e8f4b7f` — canonical Cards heading E2E expectations;
- `0460afe` — canonical Cards screenshot manifest counts.

## Known limitations and C1.6 prerequisites

- C1.5 is read-only and has no bulk selection, Safe Action mutation, awaiting
  recheck or detector-driven resolution UI;
- Search/Notification deep handoffs are not consumed by Cards yet;
- 100 is a bounded non-virtualized contour, not an unbounded inbox;
- C1.6 must keep focus, active item and future selection independent, reuse the
  existing exact-ID actions and make detector re-evaluation authoritative.

No PR, merge, release, deployment, AnkiWeb publication or owner-profile read
was performed. Core C1 remains in progress; only C1.5 is complete.

## Scope boundary

C1.5 remains read-only. It does not implement C1.6 selection, Safe Action
mutation, recheck/resolution, PR/merge/release/deployment, AnkiWeb publication,
remote telemetry content, a duplicate preview endpoint or a hidden rejected
display mode.
