# Core product track

**Track:** `C`

**Role:** the only mandatory sequential path for the main add-on

**Current status:** `C1.5R.0` Complete; `C1.5R.1` Next; `C1.6` blocked

Core does not depend on gamification, accounts, telemetry admin UI, or extension
packs. Parallel tracks may advance independently but do not change core
completion criteria.

## Delivery model

Core is developed in the long-lived `core` branch.

- `C1` and `C2` proceed sequentially in the same branch;
- no PR, merge to `master`, release tag, GitHub Release, `.ankiaddon`, deployment,
  or AnkiWeb publication occurs without separate owner approval after a stable
  Core build;
- synchronization with `master` is deliberate and documented;
- unrelated commits are not merged, rebased, or cherry-picked automatically;
- force-push is prohibited without explicit owner approval;
- commit messages describe the actual change.

The original branch baseline is in
[`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md).
The corrective C1.5R baseline is in
[`reports/core/c1-5r-0-recovery-baseline.md`](../../reports/core/c1-5r-0-recovery-baseline.md).

## Sequence

```text
C1 Cards v2 / Problem Triage
→ C2 Core 1.0 Hardening
→ C3 Contextual Additions, only for a proven gap
```

Selected hardening may occur inside C1 only when required for a safe triage
implementation. Full contract freeze and release closure remain C2 work.

## C1 — Cards v2 / Problem Triage

**Status:** In progress — C1.5R remediation active; C1.6 blocked

### Completed and active increments

- `C1.0 — Core branch baseline`: Complete —
  [`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md)
- `C1.1 — Product contract`: Complete —
  [`docs/cards-v2-product-contract.md`](../../docs/cards-v2-product-contract.md)
- `C1.2 — Canonical triage model and read API`: Complete —
  [`docs/cards-v2-triage-read-api.md`](../../docs/cards-v2-triage-read-api.md),
  Fast CI `29637594843` PASS
- `C1.3 — Inspection Profiles: contract and runtime`: Complete —
  [`docs/inspection-profiles-v1.md`](../../docs/inspection-profiles-v1.md),
  real-Anki `29641398848` PASS
- `C1.4 — Inspection Profiles: user configuration`: technical runtime/API
  foundation accepted; configuration UX included in C1.5R remediation —
  [`docs/inspection-profiles-ui.md`](../../docs/inspection-profiles-ui.md),
  historical real-Anki `29644836731` PASS
- `C1.5 — Canonical Cards workspace`: historical technical evidence retained;
  owner visual/product acceptance withdrawn —
  [`reports/core/c1-5-cards-workspace.md`](../../reports/core/c1-5-cards-workspace.md),
  Fast CI `29648956309` PASS, real-Anki `29649071545` PASS
- `C1.5R — Cards and Inspection Profiles UX remediation`: In progress
- `C1.6 — Handoffs, actions and detector-driven resolution loop`: Blocked, not
  started

C1.5's green runs prove that the old implementation executed and produced the
expected technical artifact. They do not establish product correctness after
owner review rejected display identity, preview semantics, candidate scope,
Cards presentation, and the normal Inspection Profiles path.

### C1.5R decomposition

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

#### C1.5R.0 — Recovery and corrective baseline

**Status:** Complete

Owns recovery, evidence separation, corrected status, display-contract baseline,
roadmap/handoff amendments, and safe removal of premature remote red tests. It
changes no production code or public schema and runs no heavy gate.

#### C1.5R.1 — Canonical card display identity

**Status:** Next, not started

Owns one backend-projected compact identity shared by Search card rows/details,
Triage, Cards queue, and Cards Inspector heading. It removes unrelated-field
fallback and defines a strictly versioned public transition. It does not yet
implement the formatter configuration UI or Cards redesign.

#### C1.5R.2 — Declarative compact formatter runtime

**Status:** Not started

Owns a bounded, local, declarative formatter contract and storage/runtime. It
must not silently extend Inspection Profile v1 and cannot execute arbitrary code.

#### C1.5R.3 — Front/back preview semantics

**Status:** Not started

Owns native rendered front in the Inspector and answer/back in expanded preview,
while preserving sanitizer, media validation, Shadow DOM, modal focus, and
single-active-card reads.

#### C1.5R.4 — Independent triage candidate sources

**Status:** Not started

Separates period-bound learning candidates from bounded current-content
candidates and exposes explicit available/partial/truncated source state.

#### C1.5R.5 — Cards attention inbox redesign

**Status:** Not started

Implements Variant A: dense identity-led inbox list plus persistent Inspector on
wide desktop, and a full-width queue plus non-modal detail drawer around 1024 px.
The rejected spreadsheet table is not retained as a hidden default.

#### C1.5R.6 — Guided Inspection Profiles UX

**Status:** Not started

Makes the deterministic suggestion a ready unsaved Basic draft and moves the
strict runtime editor behind Advanced. Japanese audio and Programming no-audio
expectations must be understandable without exposing machine IDs in the normal
path.

#### C1.5R.7 — Integrated acceptance and owner review package

**Status:** Not started

Runs the risk-appropriate integrated verification and prepares explicit owner
screenshots/review. Technical gates cannot grant owner product acceptance.

### C1 goal

Turn `#/cards` into one problem-triage workflow over the existing Search, Safe
Actions, Signals, and Notification Center foundations.

### C1 dependencies

- completed product contour through Stage 9.5;
- native Cards/Notes Search and inspect;
- allowlisted undoable actions;
- local typed Signals and notification handoff;
- isolated card preview host.

### C1 scope

- one bounded queue from canonical issues, active card signals, and explicit
  Search handoff;
- stable reason/severity model and deterministic ordering;
- safe context and preview;
- reuse of Search/Browser/action contracts;
- bounded bulk triage with typed results in the later C1.6 loop;
- detector-driven resolution rather than manual hiding;
- desktop accessibility, keyboard, RU/EN, light/dark, and bounded performance.

### C1 out of scope

- full Anki editor clone;
- arbitrary rules, SQL, JavaScript, iframe, or template execution;
- remote task sync;
- a second query/action/signal system;
- mobile-first redesign;
- C1.6 implementation before C1.5R and owner acceptance.

### C1 completion criteria

- one canonical triage workflow;
- backend/frontend/types/tests/docs parity;
- bounded large-fixture behavior;
- sanitizer, media, action, loopback, token, and privacy boundaries preserved;
- C1.5R technical verification complete;
- separate owner product acceptance complete;
- C1.6 resolution loop completed before C1 closes.

## C2 — Core 1.0 Hardening

**Status:** Planned after C1

### Goal

Stabilize the existing product as a supportable 1.0 core without adding another
delivery system.

### Dependencies

- C1 public workflow and contracts substantially closed;
- no unresolved C1.5R/C1.6 product or migration blocker;
- current Fast CI, exact-package GHCR E2E, and manual gated release remain
  authoritative.

### Scope

- API/schema inventory, versioning, and deprecation policy;
- migrations, future-schema fail-closed behavior, corruption quarantine, and
  per-profile isolation;
- clean install, update, profile switch, restart, and recovery matrix;
- performance, bundle, query, and history budgets;
- keyboard/accessibility closure across current core;
- packaging, rollback, security, and release checklist validation.

### Out of scope

- new product features;
- gamification, accounts, telemetry operations, or extension ecosystem;
- rebuilding delivery infrastructure already covered by the platform track.

## C3 — Contextual Additions

**Status:** Conditional

C3 closes only concrete questions discovered through C1, Signals, or real usage
that current Statistics, FSRS, and Search cannot answer. Each addition must name
the user decision, data availability, bounded query, placement, interpretation,
and verification scope. If no justified gap exists, C3 closes without feature
expansion.
