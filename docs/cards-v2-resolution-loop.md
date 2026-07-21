# Канонический цикл решения одной карточки

## Статус

**Этап:** `C1.6`  
**Поставка:** реализовано, проверено, принято владельцем и влито в `core`  
**Merge commit:** `928e3fe749ce6aa4b9c414641c4ef66ac46a694b`  
**Scope:** одна активная карточка автоматической очереди за раз

Cards Inspector и drawer на 1024 px используют один lifecycle:

```text
issue
→ существующий Safe Action или Open in Anki
→ результат действия
→ Awaiting recheck
→ каноническая bounded-перепроверка точной карточки
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

Успешное действие, включая `action.no_changes`, никогда само по себе не доказывает resolution. Ограничение очереди и исчезновение карточки из первых 100 строк также не являются доказательством resolution.

## Пути действий

- Для learning issues показываются только применимые существующие single-card Safe Actions: `suspend`/`unsuspend` и `bury`/`unbury`.
- Для content-only issues основным путём редактирования остаётся Open in Anki; при необходимости показывается переход к Inspection Profiles.
- Open in Anki является handoff, а не заявлением о mutation. После успешного handoff item остаётся активным до явной перепроверки.
- Одновременно выполняется не более одной mutation. Mutation requests не отменяются.
- Reads используют latest-wins cancellation и sequence guards: устаревший open, inspect или recheck response не может заменить более новое состояние active card.

В C1.6 не входят:

- bulk selection и checkbox;
- manual Done/Resolve/Hide/Archive/Snooze;
- persistent completion store;
- второй action или detector stack.

`C1.6B` остаётся Conditional.

## Каноническая перепроверка точной карточки

`POST /api/triage/recheck` schema v1 принимает:

- один `cardId`;
- ожидаемый `noteId`;
- текущие стабильные `reasonIds`;
- текущий Cards scope.

Endpoint:

- loopback-only;
- token-protected;
- принимает только JSON;
- ограничен 8 KiB;
- сериализован через существующий `QueryOp` bridge.

Service оценивает только запрошенную карточку и переиспользует те же канонические компоненты, что и Triage v4:

- bounded learning detectors в выбранном period/deck scope;
- active local Signal projection;
- Search-owned identity точной карточки;
- current confirmed Inspection Profiles.

Отсутствуют второй detector stack, client-side inference resolution, автоматический cursor loop и collection-wide scan.

Response возвращает `entityStatus`, typed source status, content-check status и текущий canonical item.

Состояния `partial`, `unavailable` и `error` работают fail closed: прежние reasons остаются active/stale, а UI не может показать Resolved. Предыдущий profile reason также fail closed, если authority profile больше не является current.

## Reconciliation причин

Ключ сравнения — стабильный `reasonId`:

- remaining reasons сохраняют item и обновляют priority, primary reason, evidence, state и recommended step на месте;
- removed + remaining reasons дают Partially resolved;
- new reasons явно показываются и сохраняют item active;
- отсутствие current reasons удаляет item только после полностью authoritative recheck;
- missing, changed и outside-scope identity имеют отдельные non-success states.

После удаления focus перемещается:

1. на следующий item в той же позиции очереди;
2. затем на предыдущий item;
3. на heading очереди, если она стала пустой.

Filters, загруженные pages и порядок очереди сохраняются.

## Accessibility и локализация

Resolution state использует вежливую live status region и busy state во время action/recheck. Конфликтующие controls временно disabled. Keyboard activation остаётся native. Восстановление focus после удаления детерминировано.

Все новые labels и states имеют RU/EN parity.

## Verification

Полное evidence:

- [`../reports/core/c1-6-canonical-single-card-resolution-loop.md`](../reports/core/c1-6-canonical-single-card-resolution-loop.md).

Подтверждены:

```text
focused backend/E2E helpers: 81 tests PASS
frontend: 324 tests PASS
Python compileall: PASS
production build/bundle guard: PASS
package: 77 entries PASS
canonical non-Docker: 324 frontend, 802 Python passed, 5 platform skips
Fast CI 29862254960: PASS
final-head Fast CI 29863609253: PASS
targeted real-Anki standard/cards 29862551442: PASS
final full real-Anki 29862800106: PASS
```

Не выполнялась отдельная проверка на приватном Anki-профиле владельца. Локальный Docker не дублировал успешные exact-package cloud E2E runs.