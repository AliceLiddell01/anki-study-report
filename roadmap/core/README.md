# Core product track

**Track:** `C`

**Role:** the only mandatory sequential path for the main add-on

**Current status:** `C1.5R.0–R.6` Complete; `C1.5R.7` Next, not started; `C1.6` blocked

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
- `C1.5R — Cards and Inspection Profiles UX remediation`: R0–R6 complete; R7 next
- `C1.6 — Handoffs, actions and detector-driven resolution loop`: Blocked, not
  started

C1.5's green runs prove that the old implementation executed and produced the
expected technical artifact. They do not establish product correctness after
owner review rejected display identity, preview semantics, candidate scope,
Cards presentation, and the normal Inspection Profiles path.

### C1.5R decomposition

```text
C1.5R.0 Recovery and corrective baseline — Complete
C1.5R.1 Canonical card display identity — Complete
C1.5R.2 Declarative compact formatter runtime — Complete
C1.5R.3 Front/back preview semantics — Complete
C1.5R.4 Independent triage candidate sources — Complete
C1.5R.5 Cards attention inbox redesign — Complete
C1.5R.6 Guided Inspection Profiles UX — Complete
C1.5R.7 Integrated acceptance and owner review package — Next, not started
```

#### C1.5R.0 — Recovery and corrective baseline

**Status:** Complete

Owns recovery, evidence separation, corrected status, display-contract baseline,
roadmap/handoff amendments, and safe removal of premature remote red tests. It
changes no production code or public schema and runs no heavy gate.

#### C1.5R.1 — Canonical card display identity

**Status:** Complete

Owns one backend-projected compact identity shared by Search card rows/details,
Triage, Cards queue, and Cards Inspector heading. It removes unrelated-field
fallback and introduces Search query/inspect schema v2 plus Triage schema v3.
Search metadata remains v1. Card `primaryText` aliases are removed while note
mode retains note `primaryText`.

The implementation, strict parsers, RU/EN fallback states, focused tests and
contract docs are committed. Exact-HEAD verification passed: Python compile,
85 focused Python tests, 54 focused Vitest tests and TypeScript typecheck.
The only discovered defect was test-only fetch-mock typing and was corrected
in `a46116e43756eceb3820f4eca76b28645a54a3ff`.
Implementation report:
[`reports/core/c1-5r-1-canonical-card-display-identity.md`](../../reports/core/c1-5r-1-canonical-card-display-identity.md).

It does not implement formatter configuration, preview-side correction,
candidate-source redesign, Cards inbox redesign, 1024 px drawer, Inspection
Profiles redesign, or C1.6 actions.

#### C1.5R.2 — Declarative compact formatter runtime

**Status:** Complete

Owns the independent strict schema v1, profile-local atomic store, exact/default/
disabled resolver, safe ordered formatter token runtime, Search/Triage identity
integration, token-protected query/validate/update API, strict TypeScript client,
package entries and focused documentation/tests. Inspection Profile v1 remains
unchanged and no arbitrary code or formatter UI is introduced.

Owner-checkout focused frontend, typecheck, package validation and the canonical
non-Docker gate passed for the implementation tree committed and pushed as
`edad09e8ffae443b94e192b266084abb66c37adf`. The canonical rerun passed 279 frontend tests and 772
Python tests with five environment-only skips. Fast CI, Docker and real-Anki E2E
were not required for R2. C1.5R.3 is now Next, not started.

#### C1.5R.3 — Front/back preview semantics

**Status:** Complete

Owns native rendered front in the Inspector and answer/back in expanded preview,
while preserving sanitizer, media validation, Shadow DOM, modal focus, and
single-active-card reads. Verification and transfer evidence is recorded in
[`reports/core/c1-5r-3-front-back-preview-semantics.md`](../../reports/core/c1-5r-3-front-back-preview-semantics.md).

#### C1.5R.4 — Independent triage candidate sources

**Status:** Complete

Separates period-bound learning candidates from bounded current-content
candidates, scans only authoritative confirmed Inspection Profiles, exposes
strict schema v4 continuation/source state, and keeps Search schema v2 and the
R1–R3 identity/preview contracts unchanged. Exact implementation and cleanup
evidence is recorded in
[`reports/core/c1-5r-4-independent-triage-candidate-sources.md`](../../reports/core/c1-5r-4-independent-triage-candidate-sources.md).

#### C1.5R.5 — Cards attention inbox redesign

**Status:** Complete

Implements Variant A: dense identity-led semantic inbox plus persistent Inspector
from 1200 px, and a full-width queue plus non-modal detail drawer below that
breakpoint. The rejected spreadsheet table is removed. Learning period is
explicit, current-content continuation is manual/bounded, and R1/R3/R4/Search v2
contracts remain unchanged. Verification and visual evidence are recorded in
[`reports/core/c1-5r-5-cards-attention-inbox-redesign.md`](../../reports/core/c1-5r-5-cards-attention-inbox-redesign.md).

#### C1.5R.6 — Guided Inspection Profiles UX

**Status:** Complete

Makes the deterministic suggestion a ready unsaved Basic draft and moves the
strict runtime editor behind Advanced. Japanese audio and Programming no-audio
expectations are understandable without exposing machine IDs in the normal path.
Final evidence is recorded in
[`reports/core/c1-5r-6-guided-inspection-profiles-ux.md`](../../reports/core/c1-5r-6-guided-inspection-profiles-ux.md).

#### C1.5R.7 — Integrated acceptance and owner review package

**Status:** Next, not started

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

## C1.5R.5 complete

C1.5R.5 is complete after clean reconstruction on `b2d812b4dd303965030108991858fb4bc779e73e`, focused
frontend/backend verification, exact production build and package validation,
isolated baseline/R5 Playwright evidence, canonical non-Docker verification and
clean transfer. Tested implementation: `a30f4db66e73f3f836e69ba90cfc06974ce3df47`. C1.5R.6 is next
and not started; R7 and C1.6 remain blocked by their named dependencies.

## C1.5R.6 completion

Guided Inspection Profiles is complete: generated drafts are immediate and clean,
Basic is the normal path, Advanced preserves strict v1, Japanese/Programming
defaults are understandable, lifecycle/conflict/accessibility/security contracts
are covered, and deterministic Chromium evidence is recorded. C1.5R.7 is next;
C1.6 remains blocked.
