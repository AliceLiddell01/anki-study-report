# AI handoff — Anki Study Report

**Снимок:** 2026-07-22

## С чего начать

Читайте в таком порядке:

1. [`../README.md`](../README.md);
2. этот файл;
3. [`../roadmap/README.md`](../roadmap/README.md);
4. [`../roadmap/core/README.md`](../roadmap/core/README.md);
5. current production code и tests для requested scope;
6. focused contract и latest report соответствующего этапа.

При противоречиях используйте приоритет:

```text
current production code и tests
→ current README и focused docs
→ fresh reports/artifacts
→ older plans/messages
→ assumptions
```

Не утверждайте, что file, artifact или code path изучен, если он фактически не был открыт.

## Текущее состояние проекта

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

Dashboard:

- loopback-only;
- token-protected;
- получает bounded JSON/API projections;
- не даёт frontend прямой доступ к collection.

Принятый product contour до Stage 9.5 завершён.

Текущий Core status:

```text
branch: core
C1.5R.0–R.7: Complete
C1.5R owner product acceptance: Accepted
C1.6: Complete; owner accepted; merged into core
C1.6B: Conditional; not started
Core C1: Complete
C2: Next; not started
```

Core head после C1.6:

```text
928e3fe749ce6aa4b9c414641c4ef66ac46a694b
```

PR C1.6:

```text
#125 — Add canonical single-card resolution loop
merged by rebase into core
```

## Current reports

- [`../reports/core/c1-5r-0-recovery-baseline.md`](../reports/core/c1-5r-0-recovery-baseline.md);
- [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md);
- [`../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md`](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md);
- [`../reports/core/c1-5r-3-front-back-preview-semantics.md`](../reports/core/c1-5r-3-front-back-preview-semantics.md);
- [`../reports/core/c1-5r-4-independent-triage-candidate-sources.md`](../reports/core/c1-5r-4-independent-triage-candidate-sources.md);
- [`../reports/core/c1-5r-5-cards-attention-inbox-redesign.md`](../reports/core/c1-5r-5-cards-attention-inbox-redesign.md);
- [`../reports/core/c1-5r-6-guided-inspection-profiles-ux.md`](../reports/core/c1-5r-6-guided-inspection-profiles-ux.md);
- [`../reports/core/c1-5r-7-integrated-acceptance-closeout.md`](../reports/core/c1-5r-7-integrated-acceptance-closeout.md);
- [`../reports/core/c1-6-canonical-single-card-resolution-loop.md`](../reports/core/c1-6-canonical-single-card-resolution-loop.md).

## Исторический C1.5

Historical C1.5 Fast CI и real-Anki runs доказывают, что старая implementation работала, но не являются acceptance evidence для текущего UX после owner rejection.

C1.5R заменил отклонённые части:

```text
R1 canonical card display identity
R2 declarative compact formatter
R3 front/back preview semantics
R4 independent candidate sources
R5 identity-led Cards inbox
R6 guided Inspection Profiles
R7 integrated acceptance
```

## Current Cards contracts

Основные documents:

- [`cards-v2-product-contract.md`](cards-v2-product-contract.md);
- [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md);
- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md);
- [`cards-attention-inbox.md`](cards-attention-inbox.md);
- [`card-display-identity.md`](card-display-identity.md);
- [`card-preview-semantics.md`](card-preview-semantics.md);
- [`inspection-profiles-v1.md`](inspection-profiles-v1.md);
- [`guided-inspection-profiles.md`](guided-inspection-profiles.md).

## Compact card identity

`anki_study_report/card_display_identity.py` владеет compact identity exact card.

Fallback sequence:

```text
Browser question
→ reviewer front
→ media_only | unavailable
```

Wire fields:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

Один backend projection используют Search row/details, Triage item, Cards queue и Inspector heading.

Card `primaryText` отсутствует. Note-mode Search сохраняет note `primaryText`.

## Preview semantics

- Inspector показывает sanitized native front;
- expanded modal показывает sanitized native answer/back;
- только active card загружает full preview;
- queue rows не читают media и не рендерят full HTML;
- sanitizer, media validation и Shadow DOM isolation обязательны.

## Candidate sources Triage v4

Triage query v4 разделяет:

- period-bound learning candidates;
- bounded current-content candidates;
- active Signals;
- Search identity.

Current-content scan:

- только confirmed/current Inspection Profiles;
- keyset bound 500 notes за request;
- explicit cursor continuation;
- без automatic cursor loop;
- deterministic representative card;
- без preview/media reads.

## Cards attention inbox

Canonical layout:

```text
>= 1200 px: dense semantic inbox + persistent Inspector
< 1200 px: full-width inbox + non-modal drawer
```

Queue — semantic ordered list с одной native button на item. Это не table, ARIA grid, listbox или roving-tabindex composite.

Learning period: 7/30/90 дней. Current-content continuation manual и client-bounded до 500 unique items / 10 additional pages.

## Guided Inspection Profiles

Normal path:

```text
exact note type
→ immediate clean generated Basic draft
→ bounded validation/sample
→ explicit confirm
```

Basic является friendly projection над strict v1 document. Advanced сохраняет exact IDs, mappings, checks и template scope. Autosave/autoconfirm отсутствуют.

Only confirmed/current profiles создают content reasons. `suggested`, `disabled` и `needs_review` fail closed.

## C1.6 — canonical single-card resolution loop

C1.6 завершён, принят владельцем и влит в `core`.

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

### API

```text
POST /api/triage/query    schema v4
POST /api/triage/recheck  schema v1
```

Recheck request содержит одну exact card, expected note ID, `1..4` stable reason IDs и current scope.

Backend переиспользует canonical detectors Triage v4 через serialized `QueryOp`. Второй detector stack отсутствует.

### Resolution rules

- action success и `action.no_changes` не доказывают resolution;
- Open in Anki является handoff, а не mutation proof;
- remaining reasons обновляют item на месте;
- removed + remaining дают Partially resolved;
- new reasons показываются явно;
- zero reasons удаляют item только при fully authoritative result;
- partial/unavailable/error/stale/missing/changed работают fail closed;
- post-removal focus recovery deterministic.

### Out of scope

- bulk selection;
- manual resolve/archive/snooze;
- persistent completion state;
- second action/detector system;
- unbounded reevaluation;
- C1.6B.

### Verification

```text
focused backend/E2E helpers: 81 tests PASS
frontend: 324 tests PASS
Python compileall: PASS
production build/bundle guard: PASS — 429,516 bytes
package: PASS — 77 entries
canonical non-Docker: PASS — 324 frontend, 802 Python, 5 platform skips
Fast CI 29862254960: PASS
final-head Fast CI 29863609253: PASS
targeted standard/cards + restart 29862551442: PASS
final standard/full 29862800106: PASS
```

Не выполнялась отдельная проверка C1.6 на private Anki profile владельца. Local Docker не повторял успешные exact-package cloud E2E runs.

## Exact next action

Следующий обязательный Core этап:

```text
C2 — Core 1.0 Hardening
```

Перед implementation C2 требуется отдельный product/technical planning task. Не начинать C1.6B без отдельного evidence и owner decision.

Не выполнять как implicit continuation:

- merge в `master`;
- release;
- deployment;
- публикацию `.ankiaddon` или AnkiWeb;
- C3 feature expansion.

## Verification boundary

Используйте:

- [`test-matrix.md`](test-matrix.md);
- [`verification-run-policy.md`](verification-run-policy.md).

Heavy real-Anki E2E остаётся integration gate. Не повторять successful exact-SHA runs без concrete reason.

## Technical invariants

Не делать:

- one-sided public payload/schema change;
- direct frontend collection access;
- bind server beyond `127.0.0.1`;
- weaken token validation, sanitizer, media validation или action allowlists;
- log token или full token-bearing URL;
- create iframe/template-JavaScript execution surface;
- manually edit generated dashboard assets;
- commit logs, screenshots, cache, profile data, tokens, `.ankiaddon` или E2E outputs;
- change correct production behavior ради obsolete test;
- create second query/action/signal/detector stack;
- infer resolution on client from action success или queue disappearance;
- start C1.6B/C2/C3 без отдельной task boundary.

## Other tracks

Gamification, telemetry operations, identity continuity, extensions и platform work независимы. Они не блокируют C2 без explicit dependency.

## Git boundary

Работать в target branch, указанной owner/task. Для Core по умолчанию используется `core`.

Не выполнять автоматически:

- merge/rebase в `master`;
- release/deploy/publish;
- force-push;
- destructive reset/clean/stash deletion;
- overwrite unrelated changes.

Commit messages должны описывать фактическое изменение.