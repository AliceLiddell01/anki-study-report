# C1.5 — Canonical Cards workspace

> [!IMPORTANT]
> **Amendment after owner product review:** this report is retained as historical
> technical acceptance evidence. Subsequent owner review withdrew visual/product
> acceptance. The former statements that C1.5 was product-complete, that C1.6 was
> next, and that the accepted screenshots established visual coherence are
> superseded. Current status and corrective decisions are recorded in
> [`c1-5r-0-recovery-baseline.md`](c1-5r-0-recovery-baseline.md).

**Historical technical status:** implementation and exact-SHA gates passed

**Current product status:** `C1.5 product acceptance — withdrawn`

**Current remediation status:** `C1.5R — In progress`; `C1.6 — Blocked`

**Initial branch:** `core`

**Initial HEAD:** `205bf74af77160b346bf96ebb98c3f35bf824bb3`

**Initial divergence:** `0 behind / 17 ahead` of `origin/master`; `0 behind /
0 ahead` of `origin/core`

**Initial worktree:** clean

**Open pull requests from `core`:** none

## Historical Design Gate

### Sources and constraints

The C1.5 audit covered roadmap/handoff, Cards v2 product and triage contracts,
C1.2–C1.4 reports, current Cards/Search/preview/actions implementations, tests,
Fast CI, and real-Anki E2E harness.

External sources included the Anki Manual's Browser/Search/Card Templates, Anki
add-on background-operation guidance, and W3C table/grid/modal-dialog patterns.
They supported native Browser identity, serialized collection reads, native
semantic table behavior for the then-selected surface, and portal/focus behavior
for the expanded modal.

### Legacy baseline audit

Accepted C1.4 real-Anki artifact `29644836731` represented the unchanged legacy
Cards page and provided twelve 1440 px full-page images:

- APKG table, tiles, and Anki preview in light/dark;
- synthetic Japanese/Programming table, tiles, and Anki preview in light/dark.

Observed historical full-page heights:

| Fixture | Table | Tiles | Anki preview |
| --- | ---: | ---: | ---: |
| APKG | 3,133 px | 3,826 px | 9,877 px |
| Synthetic | 5,743 px | 7,678 px | 19,232 px |

A temporary 1024 px development baseline placed the first actionable row at
1,111 px, below the 960 px initial viewport, and reached 1,573 px for only three
rows.

The legacy page duplicated diagnosis/KPIs/tabs/problem filter/display modes,
showed unexplained `riskScore`, rendered full previews for every row, and forced
long keyboard paths before the queue.

No screenshot was committed. Historical source inventory was recorded as:

```text
artifacts/screenshots/cards/{apkg,synthetic}/{table,tiles,anki-preview}/{light,dark}.png
```

### Temporary prototypes and historical decision

Two temporary local prototypes used the same triage-v2-style fixture:

- A: native compact table plus persistent Inspector;
- B: structured vertical list plus persistent Inspector.

The original C1.5 decision selected Table A for row comparison and density. That
decision is historical and is now superseded by the C1.5R product direction:

```text
Variant A — identity-led dense inbox list
wide desktop: dense list + persistent Inspector
~1024 px: full-width queue + non-modal detail drawer
```

The rejected spreadsheet-like table is not retained as the C1.5R default or a
hidden mode. The current corrective contract is
[`../../docs/card-display-identity.md`](../../docs/card-display-identity.md).

## Historical implementation

C1.5 changed `#/cards` to read automatic triage schema v2 for the selected deck
scope, a fixed seven-day period, and a bounded limit of 100. It implemented one
native table queue plus persistent Inspector:

- categorical priority, primary text, reason, bounded evidence, deck, and state;
- priority/reason/deck/text filters;
- one active row independent of keyboard focus;
- one sanitized Shadow DOM preview for the active item;
- portal-based expanded preview reusing the inspected detail;
- exact-card `open-search-selection` handoff;
- explicit loading/unavailable/partial/empty/profile-review states;
- no legacy tabs, display switch, `riskScore`, duplicated row previews,
  checkbox, mutation, or resolution loop.

Search inspect card details added the bounded `renderedPreview` shape under
Search inspect schema version 1. Sanitization and media validation remained
backend responsibilities.

The real-Anki harness captured workspace light/dark, expanded, 1024 px, and APKG
proof. It checked 100-row performance, keyboard activation, one preview host,
exact-card open, portal modal, absence of legacy controls, and no horizontal
page overflow.

These statements describe what the old implementation did. They are not the
current product specification.

## Historical verification evidence

### Local checks recorded at C1.5

- `python -m compileall -q anki_study_report docker/anki-e2e`: PASS;
- focused frontend Cards/hook/Search API: 37 PASS;
- focused Python Search/triage/package/E2E helpers: 65 PASS;
- Search/localization regression contour: 17 PASS;
- `node --check docker/anki-e2e/smoke-browser.mjs`: PASS;
- `pnpm run build:addon`: PASS, 17 JS chunks, 457,930-byte largest/entry chunk;
- `run_full_check.ps1 -SkipDocker`: PASS, 52 frontend files/278 tests and 708
  Python tests with four environment-specific skips, package build/validation
  PASS.

The local browser proof recorded a 1024 layout with 509 px queue and 376 px
Inspector, no document overflow, nine rows, one active row, and one preview host.
Enter activated another row without moving focus; Escape closed the expanded
portal modal and restored trigger focus.

### Exact-SHA cloud evidence

```text
accepted implementation SHA:
0460afe472cd87029368924bdf5640e90271c03c

Fast CI:
29648956309 — PASS

exact package artifact:
8430913583

diagnostics artifact:
8430913479

real-Anki standard/cards E2E:
29649071545 — PASS

redacted E2E artifact:
8430943370

digest:
sha256:332082fda809c1fed0be902a89065c9232a403fd1f5ba15512a23ca86ea3ea9d
```

The artifact manifest succeeded and contained 28 screenshots, including five
Cards screenshots and four Inspection Profiles screenshots. Browser automation
recorded 12 queue rows, one Inspector, one preview host, no checkbox/legacy
mode/risk score, zero document overflow, no actionable request/console/page
errors, a 1024 split, APKG native media rendering, and a portal modal.

Restart/API proof recorded 23 cards, 10 APKG attention cards, native render
source, Japanese profile transition to `needs_review`, Programming remaining
`confirmed`, preserved learning reason, and no raw value leak in profile
evidence.

### Superseded visual-acceptance statement

The original report stated that the screenshots had been manually reviewed and
that density, long text, Inspector balance, preview isolation, expanded modal,
and the 1024 layout were visually coherent.

That statement is retained only as historical record of the earlier review and
is **superseded**. Later owner product review rejected the product behavior and
presentation. The successful artifact remains technical evidence, not owner
product acceptance.

### Diagnostic runs retained

- `29647972946`: FAIL because Search parser rejected backend
  `fallbackReason: null`; fixed by `15fab44`;
- `29648324031`: FAIL on an over-exact APKG deck-label selector; fixed by
  `46004cb`;
- `29648565541`: FAIL on legacy exact Cards H1 checks after product H1 changed;
  fixed by `e8f4b7f`;
- `29648810472`: browser and restart smokes passed, but wrapper retained legacy
  screenshot counts; fixed by `0460afe`.

The successful final run is not repeated or relabeled as failed.

## Historical commits

- `0c536f9` — Design Gate contract and prototype decision;
- `45acab4` — canonical Cards queue/Inspector implementation and coverage;
- `15fab44` — native preview nullable fallback parity;
- `46004cb` — APKG deck E2E selector;
- `e8f4b7f` — canonical Cards heading E2E expectations;
- `0460afe` — canonical Cards screenshot manifest counts;
- `1011035` — documentation closeout.

## Defects confirmed after owner review

The current remediation baseline confirms:

1. card compact identity is derived through note sort-field/arbitrary-field
   fallback and is repeated by Search/Triage/Cards;
2. the Inspector and expanded preview both show front rather than front then
   answer/back;
3. the learning period is fixed and hidden in the Cards hook;
4. current-content candidates depend on the selected period's revlog candidates;
5. the C1.5 table/split layout is rejected;
6. Inspection Profiles exposes the strict runtime editor as the normal path and
   requires an extra `Use suggestion` step.

See
[`c1-5r-0-recovery-baseline.md`](c1-5r-0-recovery-baseline.md) for the full
corrective decomposition and evidence inventory.

## Current limitations and boundary

C1.5 remains historical read-only implementation evidence. It did not implement
bulk selection, Safe Action mutation, awaiting recheck, detector-driven
resolution, or C1.6 handoffs.

No PR, merge, release, deployment, AnkiWeb publication, or owner-profile read was
part of C1.5.

Current status:

```text
C1.5 technical evidence — retained
C1.5 product acceptance — withdrawn
C1.5R — In progress
C1.5R.1 — Next, not started
C1.6 — Blocked, not started
Core C1 — In progress
```
