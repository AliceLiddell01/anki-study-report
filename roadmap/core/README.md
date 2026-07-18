# Core product track

**Track:** `C`
**Role:** единственный обязательный последовательный путь основного add-on
**Current status:** `C1.3` Complete; `C1.4` Next

Core track не зависит от gamification, accounts, telemetry admin UI или extension packs. Параллельные tracks могут развиваться отдельно, но не меняют критерии готовности core.

## Delivery model

Core разрабатывается в самостоятельной долгоживущей ветке `core`.

- `C1` и `C2` выполняются последовательно в одной ветке;
- pull request, merge в `master`, release tag, GitHub Release, `.ankiaddon`, deployment и AnkiWeb publication запрещены до отдельного явного одобрения владельца после стабильного Core build;
- синхронизация с `master` выполняется только осознанно, с зафиксированной причиной и проверкой перенесённых изменений;
- автоматический merge/rebase несвязанных изменений не выполняется;
- force-push запрещён без отдельного разрешения владельца;
- промежуточные commit messages описывают фактическое изменение, а не только номер этапа.

Baseline ветки и ограничения текущего сеанса зафиксированы в
[`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md).

## Последовательность

```text
C1 Cards v2 / Problem Triage
→ C2 Core 1.0 Hardening
→ C3 Contextual Additions (только при доказанном gap)
```

Часть hardening work может выполняться внутри `C1`, если она непосредственно нужна для безопасной реализации triage. Полный contract freeze и release closure остаются в `C2`, чтобы не замораживать API до завершения следующего крупного пользовательского workflow.

## C1 — Cards v2 / Problem Triage

**Status:** In progress — `C1.3` Complete; `C1.4` Next

### Current increments

- `C1.0 — Core branch baseline`: Complete — [`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md)
- `C1.1 — Product contract`: Complete — canonical contract [`docs/cards-v2-product-contract.md`](../../docs/cards-v2-product-contract.md), evidence report [`reports/core/c1-1-product-contract.md`](../../reports/core/c1-1-product-contract.md)
- `C1.2 — Canonical triage model and read API`: Complete — technical contract [`docs/cards-v2-triage-read-api.md`](../../docs/cards-v2-triage-read-api.md), evidence report [`reports/core/c1-2-triage-model-read-api.md`](../../reports/core/c1-2-triage-model-read-api.md), exact-SHA [Fast CI run 29637594843](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29637594843) PASS
- `C1.3 — Inspection Profiles: contract and runtime`: Complete — contract [`docs/inspection-profiles-v1.md`](../../docs/inspection-profiles-v1.md), evidence report [`reports/core/c1-3-inspection-profiles-runtime.md`](../../reports/core/c1-3-inspection-profiles-runtime.md), accepted `standard/cards` restart [run 29641398848](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29641398848) PASS
- `C1.4 — Inspection Profiles: user configuration`: Next — not started

`C1.1` completes only the product/IA contract. It does not complete C1 and does not implement the queue, API, Inspection Profiles, bulk action results or migrations.

`C1.2` adds the bounded token-protected read foundation only. Current
CardsPage remains on legacy `attentionCards`; the full workspace, Inspector,
profiles, handoff UI and mutations remain later C1 increments. Local focused
and canonical non-Docker gates passed, and Fast CI run `29637594843` passed on
the exact implementation/report candidate `e7c4eded97886dc902499a0f4bdb44e842599bde`.

`C1.3` adds the versioned profile-local store, semantic note-type fingerprint,
non-authoritative suggestions, confirmed-only allowlisted checks, three
token-protected runtime endpoints and canonical triage schema v2 with
note-level sibling-deduplicated content reasons. The accepted exact-SHA
`standard/cards` restart run confirms profile-local persistence, fingerprint
mismatch detection, fail-closed content checks and isolation between Japanese
and Programming profiles while preserving profile-independent learning reasons.
It adds strict TypeScript foundation but no settings/Cards UI. C1 remains in
progress; C1.4 is next and has not started.

### Goal

Превратить `#/cards` в единый problem-triage workspace поверх уже реализованных Search, Safe Actions, Signals и Notification Center.

### Dependencies

- completed product contour through Stage 9.5;
- native Cards/Notes Search and inspect;
- allowlisted undoable actions;
- local typed Signals and notification handoff;
- existing isolated card preview host.

### Scope

- unified bounded queue from card issues, active card signals and explicit Search handoff;
- stable reason/severity model and deterministic sorting;
- context/evidence panel with safe preview;
- existing Search/Browser/action contracts instead of duplicate APIs;
- bounded bulk triage with typed partial/no-change/failure results;
- detector-driven resolution rather than manual hiding;
- targeted performance, keyboard, accessibility and RU/EN/light/dark closure.

### Out of scope

- full Anki editor clone;
- arbitrary rules, SQL, JavaScript or iframe execution;
- remote task sync;
- a second query/action/signal system;
- mobile-first redesign.

### Activation criteria

Already met. This is the active core stage.

### Completion criteria

- one canonical triage workflow;
- backend/frontend/types/tests/docs parity;
- bounded large-fixture behavior;
- sanitizer, media, action, loopback and token boundaries remain intact;
- targeted real-Anki Cards scope passes; full E2E runs only when the verification matrix requires it.

## C2 — Core 1.0 Hardening

**Status:** Planned after C1; selected prerequisite work may run inside C1

### Goal

Stabilize the existing product as a supportable 1.0 core without adding a second CI/CD system.

### Dependencies

- C1 public workflow and contracts substantially closed;
- current Fast CI, exact-package GHCR E2E and manual gated release remain authoritative.

### Scope

- API/schema inventory, versioning and deprecation policy;
- migrations, future-schema fail-closed behavior, corruption quarantine and per-profile isolation;
- clean install, update, profile switch, restart and recovery matrix;
- performance and bundle/query/history budgets;
- keyboard/accessibility closure across current core;
- packaging, rollback, security and release checklist validation.

### Out of scope

- new product features;
- gamification, accounts, telemetry operations or extension ecosystem;
- rebuilding delivery infrastructure already covered by the platform track.

### Activation criteria

- C1 contract is stable enough to freeze;
- no unresolved migration or recovery blocker makes a 1.0 promise misleading.

### Completion criteria

- published compatibility/migration/deprecation policy;
- measured performance and accessibility budgets;
- install/update/recovery matrix passes;
- exact artifact, security and release gates remain canonical.

## C3 — Contextual Additions

**Status:** Conditional

### Goal

Close only concrete questions discovered through C1, Signals or real usage that current Statistics/FSRS/Search cannot answer.

### Dependencies

- C1 complete;
- C2 contracts stable enough for additive work;
- each proposal has a documented user decision and metric/query definition.

### Scope

- contextual evidence or comparisons embedded in an existing workflow;
- clearer metric explanations;
- bounded coverage/performance improvements.

### Out of scope

- another general Statistics page;
- duplicate FSRS analytics;
- arbitrary charts, vanity metrics or scheduler changes;
- an Analytics Pack disguised as core.

### Activation criteria

Every addition must name the user decision, data availability, bounded query, placement, interpretation and verification scope. If no justified gap exists, `C3` is closed without feature expansion.

### Completion criteria

Each accepted addition has canonical definitions, API parity, contextual UX, tests and a bounded verification plan.
