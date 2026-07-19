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
C1.5R.1: Complete
C1.5R.2: Next, not started
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
C1.5R.1 Canonical card display identity — Complete
C1.5R.2 Declarative compact formatter runtime — Next, not started
C1.5R.3 Front/back preview semantics — Not started
C1.5R.4 Independent triage candidate sources — Not started
C1.5R.5 Cards attention inbox redesign — Not started
C1.5R.6 Guided Inspection Profiles UX — Not started
C1.5R.7 Integrated acceptance and owner review package — Not started
```

C1.5R.1 is closed. Do not restart its audit without new evidence. The next
Core increment is C1.5R.2, which remains not started.

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

## C1.5R.1 focused verification closeout

```text
tested implementation HEAD:
a46116e43756eceb3820f4eca76b28645a54a3ff

branch:
core

origin/core synchronization:
0 behind / 0 ahead

origin/master divergence:
0 behind / 71 ahead
```

Exact-HEAD evidence:

```text
Python compile: PASS
Focused Python: 85 passed, 1 environment-only cache warning
Focused Vitest: 8 files, 54 tests passed
TypeScript typecheck: PASS
Search Safe Actions regression contour: PASS
Git hygiene: PASS
```

The first typecheck found a test-only fetch-mock typing defect. No production
code changed during verification. The correction touched three frontend test
files and was committed as:

```text
a46116e43756eceb3820f4eca76b28645a54a3ff — test: type fetch mocks for strict contract checks
```

Fast CI, Docker, real-Anki E2E, package/build verification and owner product
acceptance were not run in C1.5R.1V.

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

```text
C1.5R.2 — Declarative compact formatter runtime
```

C1.5R.2 is next but not started. It owns a bounded local declarative formatter
contract and storage/runtime. It must not execute arbitrary code, must not
silently extend Inspection Profile v1, and must preserve the canonical compact
identity fallback implemented in C1.5R.1.

Do not absorb preview semantics, candidate-source redesign, Cards inbox
redesign, guided Profiles UX, integrated C1.5R acceptance or C1.6 into R2.

## Verification boundary

Use [`test-matrix.md`](test-matrix.md) and
[`verification-run-policy.md`](verification-run-policy.md).

C1.5R.1V did not run Fast CI, Docker, real-Anki E2E, package validation,
full non-Docker check or release verification. Do not claim those checks. Heavy real-Anki E2E remains an integration gate, not a development loop.

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
