# Продуктовая ветка Core

**Трек:** `C`  
**Роль:** единственный обязательный последовательный путь основного add-on  
**Текущий статус:** `C1 Complete`; `C1.6B Conditional`; `C2 Next, not started`

Core не зависит от gamification, accounts, telemetry admin UI или extension packs. Параллельные треки могут развиваться независимо, но не меняют критерии завершения Core.

## Модель поставки

Core разрабатывается в долгоживущей ветке `core`.

- `C1` и `C2` выполняются последовательно;
- merge в `master`, release tag, GitHub Release, `.ankiaddon`, deployment и публикация AnkiWeb требуют отдельного owner approval;
- sync с `master` выполняется осознанно и документируется;
- unrelated commits не merge/rebase/cherry-pick-ятся автоматически;
- force-push запрещён без явного owner approval;
- commit messages описывают фактическое изменение.

Baselines:

- [`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md);
- [`reports/core/c1-5r-0-recovery-baseline.md`](../../reports/core/c1-5r-0-recovery-baseline.md).

## Последовательность

```text
C1 Cards v2 / Problem Triage — Complete
→ C2 Core 1.0 Hardening — Next
→ C3 Contextual Additions — только при доказанном пробеле
```

# C1 — Cards v2 / Problem Triage

**Статус:** Complete

## Завершённые increments

| Increment | Статус | Основной источник |
| --- | --- | --- |
| `C1.0 — Core branch baseline` | Complete | [`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md) |
| `C1.1 — Product contract` | Complete | [`docs/cards-v2-product-contract.md`](../../docs/cards-v2-product-contract.md) |
| `C1.2 — Canonical triage model and read API` | Complete | [`docs/cards-v2-triage-read-api.md`](../../docs/cards-v2-triage-read-api.md) |
| `C1.3 — Inspection Profiles: contract and runtime` | Complete | [`docs/inspection-profiles-v1.md`](../../docs/inspection-profiles-v1.md) |
| `C1.4 — Inspection Profiles: user configuration` | Complete | [`docs/inspection-profiles-ui.md`](../../docs/inspection-profiles-ui.md) |
| `C1.5 — Canonical Cards workspace` | Historical technical evidence; product acceptance withdrawn | [`reports/core/c1-5-cards-workspace.md`](../../reports/core/c1-5-cards-workspace.md) |
| `C1.5R — UX remediation` | R0–R7 Complete; owner accepted | reports C1.5R |
| `C1.6 — Canonical single-card resolution loop` | Complete; owner accepted; merged | [`docs/cards-v2-resolution-loop.md`](../../docs/cards-v2-resolution-loop.md) |
| `C1.6B — Bounded bulk actions` | Conditional; not started | отдельный activation decision |

## C1.5R decomposition

```text
C1.5R.0 Recovery and corrective baseline — Complete
C1.5R.1 Canonical card display identity — Complete
C1.5R.2 Declarative compact formatter runtime — Complete
C1.5R.3 Front/back preview semantics — Complete
C1.5R.4 Independent triage candidate sources — Complete
C1.5R.5 Cards attention inbox redesign — Complete
C1.5R.6 Guided Inspection Profiles UX — Complete
C1.5R.7 Integrated acceptance and owner decision — Complete
```

### C1.5R.1 — Canonical card display identity

Одна backend-projected compact identity используется Search, Triage, Cards queue и Inspector. Search query/inspect schema v2; note mode сохраняет note `primaryText`; card alias удалён.

Отчёт:

- [`reports/core/c1-5r-1-canonical-card-display-identity.md`](../../reports/core/c1-5r-1-canonical-card-display-identity.md).

### C1.5R.2 — Declarative compact formatter runtime

Реализованы strict schema v1, profile-local atomic store, exact/default/disabled resolver, safe token runtime и formatter API. Arbitrary code и formatter UI не добавлены.

Отчёт:

- [`reports/core/c1-5r-2-declarative-compact-formatter-runtime.md`](../../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md).

### C1.5R.3 — Front/back preview semantics

Inspector показывает native sanitized front, expanded modal — answer/back. Сохраняются sanitizer, media validation, Shadow DOM и accessibility modal.

Отчёт:

- [`reports/core/c1-5r-3-front-back-preview-semantics.md`](../../reports/core/c1-5r-3-front-back-preview-semantics.md).

### C1.5R.4 — Independent triage candidate sources

Разделены period-bound learning candidates и bounded current-content candidates. Автоматически сканируются только authoritative confirmed Inspection Profiles. Triage query schema v4 использует explicit cursor continuation.

Отчёт:

- [`reports/core/c1-5r-4-independent-triage-candidate-sources.md`](../../reports/core/c1-5r-4-independent-triage-candidate-sources.md).

### C1.5R.5 — Cards attention inbox redesign

Реализован identity-led semantic inbox, persistent Inspector от 1200 px и non-modal drawer ниже breakpoint. Spreadsheet table удалена. Learning period явный; current-content continuation ручной и bounded.

Отчёт:

- [`reports/core/c1-5r-5-cards-attention-inbox-redesign.md`](../../reports/core/c1-5r-5-cards-attention-inbox-redesign.md).

### C1.5R.6 — Guided Inspection Profiles UX

Suggestion сразу становится clean unsaved Basic draft. Strict editor находится в Advanced. Japanese/Programming defaults понятны без machine IDs.

Отчёт:

- [`reports/core/c1-5r-6-guided-inspection-profiles-ux.md`](../../reports/core/c1-5r-6-guided-inspection-profiles-ux.md).

### C1.5R.7 — Integrated acceptance

Candidate `df633563490f80346617871ec5640adf99154956` прошёл focused harness regression, canonical non-Docker и full real-Anki E2E с restart. Owner product acceptance получен.

Отчёт:

- [`reports/core/c1-5r-7-integrated-acceptance-closeout.md`](../../reports/core/c1-5r-7-integrated-acceptance-closeout.md).

## C1.6 — Canonical single-card resolution loop

**Статус:** Complete; owner accepted; merged into `core`

Implementation/runtime candidate:

```text
edaf9030dbba355593e52cf8922d4c7985ce4b75
```

Final PR head:

```text
9e4b74b0bc3a0a34590217550a7e8be4263c7fd6
```

Merged core commit:

```text
928e3fe749ce6aa4b9c414641c4ef66ac46a694b
```

Lifecycle:

```text
issue
→ existing Safe Action or Open in Anki
→ action result
→ Awaiting recheck
→ exact-card canonical bounded recheck
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

C1.6 добавляет strict `POST /api/triage/recheck` schema v1, reason reconciliation и deterministic focus recovery.

Сохраняются:

- существующие Safe Actions и Open in Anki;
- Triage query v4 detectors;
- Search identity/inspect contracts;
- fail-closed partial/unavailable/stale behavior;
- single-card scope;
- RU/EN и accessibility.

Не добавлены bulk selection, manual resolve/archive/snooze, persistent completion state, second detector/action system и unbounded reevaluation.

Verification:

```text
focused backend/E2E helpers: 81 tests PASS
frontend: 324 tests PASS
canonical non-Docker: 324 frontend, 802 Python, 5 skips
Fast CI 29862254960: PASS
final-head Fast CI 29863609253: PASS
targeted standard/cards 29862551442: PASS
final standard/full 29862800106: PASS
```

Отдельная проверка на private Anki profile владельца не выполнялась. Local Docker не дублировал successful exact-package cloud E2E.

Контракты и evidence:

- [`docs/cards-v2-resolution-loop.md`](../../docs/cards-v2-resolution-loop.md);
- [`reports/core/c1-6-canonical-single-card-resolution-loop.md`](../../reports/core/c1-6-canonical-single-card-resolution-loop.md).

## C1.6B — Bounded bulk actions

**Статус:** Conditional; not started

C1.6B активируется только после отдельного evidence, подтверждающего bounded multi-card task, и отдельного owner decision. Он не требуется для завершения C1.

## Критерии завершения C1

Все обязательные критерии выполнены:

- один canonical triage workflow;
- parity backend/frontend/types/tests/docs;
- bounded large-fixture behavior;
- сохранены sanitizer, media, action, loopback, token и privacy boundaries;
- C1.5R technical verification и owner acceptance завершены;
- C1.6 single-card resolution loop реализован, проверен, принят и влит;
- C1.6B остаётся optional.

# C2 — Core 1.0 Hardening

**Статус:** Next; not started

## Цель

Стабилизировать существующий продукт как поддерживаемый Core 1.0 без новой delivery system и без feature expansion.

## Зависимости

- Core C1 закрыт;
- отсутствуют unresolved blockers C1.5R/C1.6;
- Fast CI, exact-package GHCR E2E и manual gated release остаются authoritative.

## Scope

- inventory API/schema, versioning и deprecation policy;
- migrations, future-schema fail-closed, corruption quarantine и per-profile isolation;
- matrix clean install, update, profile switch, restart и recovery;
- performance, bundle, query и history budgets;
- keyboard/accessibility closure;
- packaging, rollback, security и release checklist validation.

## Вне scope

- новые product features;
- gamification, accounts, telemetry operations или extension ecosystem;
- rebuild delivery infrastructure, уже покрытой Platform track.

# C3 — Contextual Additions

**Статус:** Conditional

C3 закрывает только конкретные gaps, найденные через C1, Signals или реальное использование, на которые текущие Statistics, FSRS и Search не могут ответить.

Каждое addition обязано определить user decision, data availability, bounded query, placement, interpretation и verification scope. При отсутствии доказанного gap C3 закрывается без feature expansion.