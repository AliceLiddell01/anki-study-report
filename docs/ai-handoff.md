# AI handoff — Anki Study Report

Snapshot: **2026-07-19**

## Start here

Read in this order:

1. [`../README.md`](../README.md)
2. this file
3. [`../roadmap/README.md`](../roadmap/README.md)
4. [`../roadmap/core/README.md`](../roadmap/core/README.md)
5. current production code/tests for the requested scope
6. the current focused contract and latest report

When sources disagree, use:

```text
current production code and tests
→ current README and focused docs
→ fresh reports/artifacts
→ older plans/messages
→ assumptions
```

Do not claim a file, artifact, or code path was inspected unless it was actually
opened.

## Current project state

Anki Study Report is a local add-on for Anki 26.05+ with Python runtime and a
React/TypeScript dashboard. The dashboard is loopback-only, token-protected and
receives bounded JSON/API projections; frontend never reads collection directly.

The accepted product contour through Stage 9.5 remains complete. Only `C1 → C2`
is the mandatory core path.

```text
branch for current core work: core
Core C1: In progress
C1.5R.0: Complete
C1.5R.1: Implemented, focused verification pending
C1.5R.2: Blocked
C1.6: Blocked, not started
```

Current reports:

- [`../reports/core/c1-5r-0-recovery-baseline.md`](../reports/core/c1-5r-0-recovery-baseline.md)
- [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md)

## Historical C1.5 evidence

```text
C1.4 runtime/API foundation — accepted
C1.4 configuration UX — remediation required

C1.5 accepted implementation SHA:
0460afe472cd87029368924bdf5640e90271c03c

C1.5 Fast CI:
29648956309 — PASS

C1.5 real-Anki standard/cards E2E:
29649071545 — PASS

C1.5 redacted artifact:
8430943370 — 28 screenshots

C1.5 closeout SHA:
101103585149aa0a30d411ad538fbcc06641a05b
```

These are historical technical proofs. Owner review later withdrew C1.5
visual/product acceptance. Do not call the runs failures and do not use them as
acceptance evidence for C1.5R.

## Corrective decomposition

```text
C1.5R.0 Recovery and corrective baseline — Complete
C1.5R.1 Canonical card display identity — Implemented, focused verification pending
C1.5R.2 Declarative compact formatter runtime — Blocked
C1.5R.3 Front/back preview semantics — Not started
C1.5R.4 Independent triage candidate sources — Not started
C1.5R.5 Cards attention inbox redesign — Not started
C1.5R.6 Guided Inspection Profiles UX — Not started
C1.5R.7 Integrated acceptance and owner review package — Not started
```

Do not restart the C1.5R audit and do not start C1.5R.2 until the focused R1
verification contour passes.

## C1.5R.1 implementation

### Backend

`anki_study_report/card_display_identity.py` now owns compact identity for one
exact card. It renders:

```text
Browser question
→ reviewer front
→ explicit media_only or unavailable state
```

It does not scan arbitrary note fields, render answer/back, read media files or
expose renderer exceptions. The first meaningful rendered line is bounded to
240 characters.

Exact wire fields:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

### Public schemas

```text
Search query/inspect: schema v2
Search metadata: schema v1, unchanged
Triage query/response: schema v3
```

Card rows/details and Triage items no longer carry card `primaryText`. Note-mode
Search keeps note `primaryText`. Old schemas, aliases, unknown keys and
incoherent display states fail closed in strict TypeScript parsers.

### Shared surfaces

The same backend projection is consumed by:

```text
Search card row
Search card Inspector heading
Triage item
Cards queue
Cards Inspector heading
```

The frontend helper localizes only explicit fallback states:

```text
RU: Карточка только с медиа | Текст карточки недоступен
EN: Card with media only | Card text unavailable
```

The current Cards table/split UI remains product-rejected historical C1.5 UI.
C1.5R.1 did not redesign it.

## Accepted later-stage decisions

### Preview semantics — C1.5R.3

- Inspector: native sanitized front.
- Expanded preview: native sanitized answer/back by default.
- Only active card loads full preview.
- Queue rows load no media/full HTML.

C1.5R.1 does not implement these side changes.

### Candidate sources — C1.5R.4

Learning candidates remain period-bound. Current-content candidates become a
separate bounded source and must not disappear when a learning period has zero
reviews. The hidden seven-day period must become explicit product state in that
stage.

### Cards Design Gate — C1.5R.5

```text
wide desktop: dense identity-led inbox + persistent Inspector
around 1024 px: full-width queue + non-modal detail drawer
```

The drawer is non-modal, uses no `inert` or focus trap, has return-to-queue and
does not steal focus on row activation.

### Inspection Profiles — C1.5R.6

Normal workflow becomes guided Basic configuration. Strict runtime editor moves
behind Advanced. Deterministic suggestion becomes a ready unsaved draft
automatically. Inspection Profile v1 must not silently gain formatter fields.

## Exact next action

Run the focused C1.5R.1 verification contour from
[`card-display-identity.md`](card-display-identity.md):

```powershell
python -m pytest -q tests/test_card_display_identity.py tests/test_search_service.py tests/test_search_metadata.py tests/test_search_runtime.py tests/test_triage_service.py tests/test_triage_runtime.py tests/test_dashboard_server.py
cd web-dashboard
pnpm exec vitest run src/lib/cardDisplayText.test.ts src/lib/searchApi.test.ts src/lib/triageApi.test.ts src/hooks/useCardsTriageWorkspace.test.tsx src/pages/SearchPage.test.tsx src/pages/SearchMetadataIntegration.test.tsx src/pages/CardsPage.test.tsx
pnpm run typecheck
```

Until those checks pass, do not mark C1.5R.1 Complete and do not begin C1.5R.2.

## Verification boundary

Use [`test-matrix.md`](test-matrix.md) and
[`verification-run-policy.md`](verification-run-policy.md).

Current connector work did not run Fast CI, Docker, real-Anki E2E, package
validation, full non-Docker check or release verification. Do not claim those
checks. Heavy real-Anki E2E remains an integration gate, not a development loop.

## Technical invariants

Do not:

- change a public payload on only one side;
- give frontend direct collection access;
- open server beyond `127.0.0.1`;
- weaken token validation, sanitizer, media validation or action allowlists;
- log token or full token-bearing URL;
- create iframe/template-JavaScript execution surfaces;
- edit generated dashboard assets manually;
- commit logs, screenshots, cache, profile data, tokens, `.ankiaddon` or E2E output;
- change correct production behavior for an obsolete test;
- start C1.6 before C1.5R and owner acceptance.

## Other tracks

Gamification, telemetry operations, identity continuity, extensions and platform
work remain independent. None blocks C1.5R or C2 without an explicit dependency.

## Git boundary

Work only on `core` unless the owner changes the target. Do not create a PR,
merge/rebase to `master`, release, deploy, publish `.ankiaddon` or update AnkiWeb
as an implicit continuation. Avoid force-push, destructive reset, clean or stash
deletion and preserve unrelated changes.
