# Передача контекста ИИ — Anki Study Report

**Снимок:** 2026-07-24

## С чего начать

Читайте источники в таком порядке:

1. [`../README.md`](../README.md);
2. этот файл;
3. [`../roadmap/README.md`](../roadmap/README.md);
4. профильный README соответствующего трека;
5. актуальные production-код и тесты в пределах задачи;
6. профильный контракт и последний отчёт соответствующего этапа.

При противоречиях:

```text
актуальные production-код и тесты
→ актуальные README и профильные документы
→ свежие отчёты и артефакты
→ старые планы и сообщения
→ предположения
```

Не утверждайте, что файл, артефакт или участок кода изучен, если он фактически не был открыт.

## Текущее состояние проекта

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

Dashboard:

- доступен только через loopback-интерфейс;
- защищён токеном;
- получает ограниченные JSON/API-проекции;
- не предоставляет frontend прямой доступ к collection.

Текущий статус Core:

```text
базовая ветка: core
текущий head core после C2: edb140b1197910aae31500a40e4a8287cc46b760
PR C2: #128, merged
C1.5R.0–R.7: завершено и принято владельцем
C1.6: завершено, принято владельцем и влито в core
C1.6B: условный этап, не начат
C1: завершён
C2 implementation: завершён и exact-SHA проверен
C2 integration: влит в core
C2 owner acceptance: повторно открыта после ручной проверки
post-C2 remediation branch/PR: ещё не созданы
C3–C6: новый обязательный путь к Core 1.0
release: не начат
```

## Текущий статус Platform / CI

```text
рабочая ветка: platform/e2e-observability-roadmap
base branch: core
E2E-I1: COMPLETE ON FEATURE BRANCH
финальный implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Fast CI: 30039103625 — PASS
первый standard/full: 30039372012 — PASS
финальный standard/full: 30039708429 — PASS
E2E-I2: следующий этап, не начат
PR в core: не создан
merge в core: не выполнен
release: не выполнялся
```

`E2E-I1` ввёл единый schema-v1 live lifecycle Fast CI и Docker E2E:

```text
Fast CI stream: ci-fast/run-events.jsonl
Docker stream: reports/run-events.jsonl
Public stream: artifacts/reports/run-events.jsonl
```

Актуальный контракт:

- [`run-event-protocol.md`](run-event-protocol.md);
- [`../roadmap/platform/e2e-observability-build-identity.md`](../roadmap/platform/e2e-observability-build-identity.md).

Итоговый отчёт:

- [`../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md).

Важные инварианты:

- Fast CI timing и run-event registry синхронизированы fail closed;
- success artifact обязан содержать validated `run-events.jsonl`;
- transient `.lock`/`.state.json` не являются evidence;
- Docker Compose в CI использует plain non-interactive output;
- browser item-level progress не реализован и относится к `E2E-I2`;
- stable failure codes не реализованы и относятся к `E2E-I3`;
- docs-only commits после successful gates не требуют повторного Fast CI/Docker без отдельной причины;
- не создавать PR и не выполнять merge без прямой просьбы владельца.

## Почему C2 ещё не закрыт владельцем

После merge ручная проверка реального UI выявила:

### Cards

- не применяется нативный root background карточки в compact/expanded preview;
- compact preview перехватывает wheel вместо page scroll;
- wide Inspector имеет лишний нижний safe-area;
- результат Suspend/Bury/Open/Recheck недостаточно наблюдаем;
- информационная композиция остаётся слишком плоской;
- refresh и state changes ощущаются резкими.

### Inspection Profiles

- Basic и Advanced одновременно показывают две проекции одного draft;
- notices и validation messages перегружены;
- editor layout зависит от viewport вместо своей ширины;
- осмысленные field names распознаются недостаточно хорошо;
- normal path всё ещё напоминает schema/admin editor.

### Общий UI

- shape/surface/motion foundation недостаточно цельная;
- многие страницы используют узкую centered область вместо всей рабочей ширины;
- тексты часто повторяют page title или очевидную функцию.

Эти проблемы исправляются одной post-C2 manual acceptance remediation task. Не создавать `C2.1/C2.2`.

## Обновлённый обязательный путь Core

```text
post-C2 manual acceptance remediation
→ C3 Core UI & Shell Consolidation
→ C4 First-party Data Independence
→ C5 Today v2
→ C6 Profile v2 Foundation
→ Core 1.0 owner acceptance
→ отдельное решение о release
```

### C3 — Core UI & Shell Consolidation

- site-wide UI/content review перед implementation;
- полноширинный desktop App Shell без глобального узкого `max-width`;
- shared PageHeader, typography, spacing, shape, surface и motion;
- удаление текстового дублирования;
- удаление Tools и Report surfaces с мёртвым кодом;
- Search как utility icon справа;
- без функциональной перестройки Today/Profile.

### C4 — First-party Data Independence

- inventory текущих integrations;
- перенос полезных данных на поддерживаемые first-party Anki/runtime boundaries;
- удаление runtime dependence на сторонние add-ons;
- только после миграции удалить Sources route/API/tests/docs.

### C5 — Today v2

Daily action-oriented summary: что сегодня, что сделано, что требует внимания, какой следующий шаг. Не дублировать Statistics/Activity/Decks/FSRS.

### C6 — Profile v2 Foundation

Editable nickname, description, avatar, banner и дата начала обучения; полноширинная композиция; реальные progress/milestone data. Не добавлять fake XP/achievements/skills до отдельного G-track.

`C1.6B` и contextual additions не входят в обязательную очередь.

## Актуальные отчёты Core

- [`../reports/core/c1-5r-0-recovery-baseline.md`](../reports/core/c1-5r-0-recovery-baseline.md);
- [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md);
- [`../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md`](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md);
- [`../reports/core/c1-5r-3-front-back-preview-semantics.md`](../reports/core/c1-5r-3-front-back-preview-semantics.md);
- [`../reports/core/c1-5r-4-independent-triage-candidate-sources.md`](../reports/core/c1-5r-4-independent-triage-candidate-sources.md);
- [`../reports/core/c1-5r-5-cards-attention-inbox-redesign.md`](../reports/core/c1-5r-5-cards-attention-inbox-redesign.md);
- [`../reports/core/c1-5r-6-guided-inspection-profiles-ux.md`](../reports/core/c1-5r-6-guided-inspection-profiles-ux.md);
- [`../reports/core/c1-5r-7-integrated-acceptance-closeout.md`](../reports/core/c1-5r-7-integrated-acceptance-closeout.md);
- [`../reports/core/c1-6-canonical-single-card-resolution-loop.md`](../reports/core/c1-6-canonical-single-card-resolution-loop.md);
- [`../reports/core/c2-core-hardening-ui-remediation.md`](../reports/core/c2-core-hardening-ui-remediation.md).

## Канонические контракты Cards

Основные документы:

- [`cards-v2-product-contract.md`](cards-v2-product-contract.md);
- [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md);
- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md);
- [`cards-attention-inbox.md`](cards-attention-inbox.md);
- [`card-display-identity.md`](card-display-identity.md);
- [`card-preview-semantics.md`](card-preview-semantics.md);
- [`inspection-profiles-v1.md`](inspection-profiles-v1.md);
- [`guided-inspection-profiles.md`](guided-inspection-profiles.md).

### Компактная идентичность карточки

Одна backend-проекция используется в Search, Triage, очереди Cards и Inspector:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

Fallback:

```text
вопрос из Browser
→ лицевая сторона reviewer
→ media_only | unavailable
```

Поле `primaryText` у Card отсутствует. Search в режиме заметок сохраняет `primaryText` заметки.

### Предпросмотр

- Inspector показывает санитизированную нативную лицевую сторону;
- расширенный modal показывает санитизированную нативную обратную сторону;
- полный preview загружается только для активной карточки;
- строки очереди не читают media и не рендерят полный HTML;
- sanitizer, media validation, Shadow DOM и parser-backed CSS policy обязательны;
- frontend не получает доступ к collection и не выполняет JavaScript карточек.

Owner scroll decision для следующей remediation:

```text
wide Cards:
- nested vertical scroll только у левой очереди;
- Inspector использует page scroll;
- compact preview не перехватывает wheel.

narrow drawer и answer modal:
- internal scroll сохраняется.
```

### Triage v4

Triage разделяет кандидатов по учебной активности, текущему содержимому, Signals и Search identity. Content scan использует только подтверждённые и актуальные Inspection Profiles, ограничен 500 заметками на запрос и продолжается через явный cursor.

### Cards workspace

```text
>= 1200 px: семантическая очередь + постоянный Inspector
< 1200 px: очередь на всю ширину + немодальная выдвижная панель
```

Очередь не является таблицей, ARIA grid или listbox. Ответ открывается в отдельном true modal. Local filters отделены от query scope.

### Inspection Profiles

```text
конкретный тип заметки
→ чистый черновик Basic
→ ограниченная проверка и выборка
→ явное подтверждение
```

Basic — понятная проекция strict schema v1. Machine IDs, ordinals и mappings находятся в Advanced. Autosave и autoconfirm отсутствуют. Неподтверждённые, устаревшие и повреждённые профили работают fail closed.

Следующая remediation должна показывать Basic и Advanced как взаимоисключающие режимы одного strict draft.

## C1.6 — цикл решения проблемы одной карточки

```text
проблема
→ Safe Action или Open in Anki
→ результат действия
→ Awaiting recheck
→ ограниченная каноническая перепроверка exact card
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

API:

```text
POST /api/triage/query    schema v4
POST /api/triage/recheck  schema v1
```

Успех действия или `action.no_changes` не доказывает resolution. Элемент удаляется только при полностью авторитетном результате без оставшихся причин.

## C2 — подтверждённые результаты

- parser-backed CSS allowlist на vendored `tinycss2`/`webencodings`;
- selector scoping, bounded fail-closed output и safe local media/font rewrite;
- deny-by-default CSP и response security headers;
- Vite-managed same-origin theme bootstrap;
- exact-card authority только для релевантного note type и profile-dependent reasons;
- независимые query/inspect/cache/mutation generations;
- bounded `O(cap)` additional Search memory и один широкий native query одновременно;
- типизированный `409 search_busy`;
- минимальный public `/api/status` и token-protected diagnostics;
- failed authentication не продлевает idle lifetime;
- behavior-based E2E helpers;
- Fast CI, targeted `standard/cards` с restart и final `standard/full` прошли до merge.

Residual risks:

- native Anki Search материализует полную Sequence до add-on processing;
- broad legacy services не переписаны вне доказанных policy seams;
- `style-src 'unsafe-inline'` необходим для runtime Shadow DOM styles;
- приватный пользовательский профиль владельца не является автоматическим CI gate.
