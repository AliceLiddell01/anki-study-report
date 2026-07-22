# Передача контекста ИИ — Anki Study Report

**Снимок:** 2026-07-22

## С чего начать

Читайте источники в таком порядке:

1. [`../README.md`](../README.md);
2. этот файл;
3. [`../roadmap/README.md`](../roadmap/README.md);
4. [`../roadmap/core/README.md`](../roadmap/core/README.md);
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
восстановленный base для post-C2 remediation: edb140b1197910aae31500a40e4a8287cc46b760
рабочая ветка follow-up: c2-manual-acceptance-remediation
C1.5R.0–R.7: завершено и принято владельцем
C1.6: завершено, принято владельцем и влито в core
C1.6B: условный этап, не начат
Core C1: завершён
C2: реализация и exact-SHA verification campaign завершены, изменения включены в core
post-merge manual acceptance remediation: реализация подготовлена; cloud/manual gates фиксируются в PR и append-only отчёте
C3: условный этап, не начинать автоматически
```

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

### Triage v4

Triage разделяет кандидатов по учебной активности, кандидатов по текущему содержимому, Signals и Search identity. Content scan использует только подтверждённые и актуальные Inspection Profiles, ограничен 500 заметками на запрос и продолжается только через явный cursor.

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

Basic — понятная проекция strict schema v1. Basic/Advanced взаимоисключающие режимы одного editor; machine IDs, ordinals и mappings находятся в Advanced. Autosave и autoconfirm отсутствуют. Неподтверждённые, устаревшие и повреждённые профили работают fail closed.

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

## C2 — Core 1.0 Hardening

C2 завершён, прошёл обязательную exact-SHA campaign и включён в `core`. Текущий follow-up закрывает замечания ручной приёмки без создания нового этапа.

Финальный проверенный head:

```text
9d5d7724aedac375fde3c9a6752baf1b4aee86ba
```

Ключевые результаты:

- parser-backed CSS allowlist на vendored `tinycss2`/`webencodings`;
- selector scoping, bounded fail-closed output и safe local media/font rewrite;
- deny-by-default CSP и response security headers;
- Vite-managed same-origin theme bootstrap вместо запрещённого inline script;
- exact-card authority только для релевантного note type и profile-dependent reasons;
- независимые query/inspect/cache/mutation generations;
- bounded `O(cap)` additional Search memory и один широкий native query одновременно;
- типизированный `409 search_busy`;
- минимальный public `/api/status` и token-protected diagnostics;
- failed authentication не продлевает idle lifetime;
- behavior-based E2E helpers;
- UI remediation Cards и Inspection Profiles без изменения product model;
- Fast CI, targeted `standard/cards` с restart и final `standard/full` — PASS по подтверждению владельца.

Известные исторические runs:

```text
Fast CI 29882753539: PASS для предыдущего head
standard/cards 29882991519: FAIL после успешного handoff; выявил stale Cards hook и CSP bootstrap defect
финальная campaign для 9d5d7724...: Fast CI PASS, standard/cards PASS, standard/full PASS
```

Номера трёх финальных runs не были переданы в доступный контекст и не должны выдумываться.

Residual risks:

- native Anki Search материализует полную Sequence до add-on processing;
- broad legacy services не переписаны вне доказанных policy seams;
- `style-src 'unsafe-inline'` остаётся необходимым для runtime Shadow DOM styles;
- приватный пользовательский профиль владельца отдельно не проверялся;
- private-profile acceptance текущего follow-up остаётся ручным действием владельца.

## Следующее точное действие

Завершить exact-SHA Fast CI, один targeted `standard/cards` с restart и финальный `standard/full` для ветки `c2-manual-acceptance-remediation`, затем передать владельцу draft PR и новые screenshots для ручной приёмки. Private-profile actions выполняет только владелец.

Не выполнять как неявное продолжение:

- merge или rebase в `master`;
- release tag, GitHub Release или публикацию `.ankiaddon`;
- deployment;
- AnkiWeb publish;
- C1.6B;
- C3;
- несвязанный cleanup.

## Границы проверки

Используйте:

- [`test-matrix.md`](test-matrix.md);
- [`verification-run-policy.md`](verification-run-policy.md).

Real-Anki Docker E2E — integration gate, а не обычный цикл разработки.

## Технические инварианты

Запрещено:

- односторонне менять payload или schema;
- предоставлять frontend прямой доступ к collection;
- открывать локальный сервер наружу;
- ослаблять token validation, sanitizer, media validation или action allowlists;
- логировать token или полный token-bearing URL;
- создавать iframe/JavaScript execution surface для карточек;
- редактировать generated dashboard assets вручную;
- коммитить логи, screenshots, cache, profile data, tokens, `.ankiaddon` или E2E outputs;
- менять корректное production-поведение только ради устаревшего теста;
- создавать второй стек запросов, действий или детекторов;
- считать успех действия доказательством resolution;
- начинать C1.6B, C3, release или publication без отдельной границы задачи.

## Границы Git

Follow-up PR остаётся draft до ручной приёмки владельцем. Не выполнять автоматически merge, force-push, destructive reset/clean, переписывание несвязанных изменений, release или публикацию.
