# AI handoff — Anki Study Report

Snapshot: **2026-07-19**

## Start here

Read in this order:

1. [`../README.md`](../README.md)
2. this file
3. [`../roadmap/README.md`](../roadmap/README.md)
4. the relevant track README
5. current production code/tests for the requested scope
6. the current contract and latest report for that scope

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

Anki Study Report is a local add-on for Anki 26.05+ with a Python runtime and a
React/TypeScript dashboard. The dashboard is loopback-only, token-protected, and
receives bounded JSON/API projections; the frontend never reads the collection
directly.

The accepted product contour through Stage 9.5 remains complete. Future work is
split into tracks; only `C1 → C2` is the mandatory core path.

```text
branch for current core work: core
Core C1: In progress
C1.5R.0: Complete
C1.5R.1: Next, not started
C1.6: Blocked, not started
```

Recovery baseline:
[`../reports/core/c1-5r-0-recovery-baseline.md`](../reports/core/c1-5r-0-recovery-baseline.md).

## C1 corrective status

### Historical evidence retained

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

These are historical technical proofs. Subsequent owner review withdrew C1.5
visual/product acceptance. Do not call the successful runs failures, and do not
use them as evidence that the remediated product is accepted.

### Corrective decomposition

```text
C1.5R.0 Recovery and corrective baseline — Complete
C1.5R.1 Canonical card display identity — Next, not started
C1.5R.2 Declarative compact formatter runtime — Not started
C1.5R.3 Front/back preview semantics — Not started
C1.5R.4 Independent triage candidate sources — Not started
C1.5R.5 Cards attention inbox redesign — Not started
C1.5R.6 Guided Inspection Profiles UX — Not started
C1.5R.7 Integrated acceptance and owner review package — Not started
```

Do not restart the entire C1.5R audit. C1.5R.0 recovered and fixed the baseline;
continue with the exact next increment.

## Accepted C1.5R decisions

### Card identity

One backend projector must own compact card identity for:

```text
Search card row
Search card Inspector identity
Triage item
Cards queue
Cards Inspector heading
```

Current Search behavior is defective because it starts with the note sort field
and then scans arbitrary non-empty fields. Triage/Cards repeat that text. No
unrelated-field fallback is allowed for card identity.

Baseline contract:
[`card-display-identity.md`](card-display-identity.md).

### Preview semantics

- Inspector renders the native sanitized front.
- Expanded preview defaults to native sanitized answer/back.
- Only the active card receives a full preview read.
- Queue rows do not load media/full HTML.
- Sanitizer, media validation, token protection, Shadow DOM, and no-iframe/no-JS
  boundaries remain unchanged.

### Candidate sources and period

- the current seven-day learning period is hidden in the Cards hook and must
  become explicit product state in the relevant remediation increment;
- learning candidates remain period-bound;
- current-content candidates are a separate bounded source and must not vanish
  merely because the selected learning period has zero reviews;
- source status must expose unavailable/partial/truncated behavior explicitly.

### Cards Design Gate

Accepted direction:

```text
Variant A — identity-led dense inbox list
```

Wide desktop:

```text
dense inbox queue + persistent Inspector
```

Around 1024 px:

```text
full-width queue + non-modal detail drawer
```

The drawer:

- is not a modal;
- does not use `inert`;
- does not trap focus;
- has an explicit return-to-queue action;
- does not receive focus automatically when a row is activated.

Do not restore the C1.5 spreadsheet-like table as the default or a hidden mode.

### Inspection Profiles

The normal workflow becomes guided Basic configuration. The strict runtime
editor remains available behind Advanced.

A deterministic suggestion becomes a ready unsaved draft automatically. Do not
require a separate `Use suggestion` step before the user can review it.

Do not silently add compact formatter fields to strict Inspection Profile v1.
The formatter needs its own explicit versioned contract or a separately approved
schema transition. It remains declarative and cannot execute arbitrary code.

## Exact next stage

```text
C1.5R.1 — Canonical card display identity
```

C1.5R.1 should establish and implement the canonical compact identity transition
with backend/frontend/parser/test/doc parity. It must not absorb the formatter
runtime, preview-side changes, candidate-source split, Cards redesign, or guided
Profiles UX unless a narrow prerequisite is unavoidable and documented.

## Verification boundary

Use [`test-matrix.md`](test-matrix.md) and
[`verification-run-policy.md`](verification-run-policy.md).

For C1.5R.0 no Python/frontend/typecheck/build/Fast CI/Docker gate was run or
required. Do not retroactively claim those checks.

For future implementation increments:

```text
focused tests
→ local non-Docker contour as required
→ exact-SHA Fast CI
→ targeted real-Anki scope when the actual diff requires it
→ owner product review only at C1.5R.7
```

Full real-Anki Docker E2E is an integration gate, not a development loop. Do not
run heavy gates blindly or repeat a successful exact-SHA run without a relevant
change.

## Technical invariants

Do not:

- change a dashboard payload on only one side;
- give the frontend direct Anki collection access;
- open the server beyond `127.0.0.1`;
- weaken dashboard-token validation, sanitizer, media validation, or action
  allowlists;
- log the token or full token-bearing URL;
- create an iframe or JavaScript execution surface for cards;
- edit generated dashboard assets manually;
- commit logs, screenshots, cache, profile data, tokens, `.ankiaddon`, or E2E
  output;
- change correct production behavior merely to satisfy an obsolete test;
- start C1.6 before C1.5R and explicit owner product acceptance.

Public behavior changes require synchronized backend, frontend types/validators,
tests, and documentation.

## Other tracks

- Gamification: parallel research/product track; production not approved.
- Telemetry operations: separate protected admin tooling.
- Identity continuity: conditional opt-in gate.
- Extensions: conditional/deferred.
- Platform/CI: separate delivery and real-Anki verification track.

None of these blocks C1.5R or C2 unless a new explicit dependency is recorded.

## Git boundary for core work

Work only on `core` unless the owner explicitly changes the target. Do not create
a PR, merge/rebase to `master`, release, deploy, publish `.ankiaddon`, or update
AnkiWeb as an implicit continuation of a stage. Preserve unrelated changes and
avoid force-push, destructive reset, clean, or stash deletion.
