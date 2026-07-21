# Cards attention inbox

## Статус

Этот контракт описывает `C1.5R.5 — Cards attention inbox redesign` для `#/cards`.

Он заменяет отклонённую spreadsheet-like table C1.5. Layout C1.5R.5 принят владельцем в составе C1.5R.7 и расширен C1.6 без изменения структуры queue, Inspector/drawer или preview.

## Выбранная структура

```text
Variant A — плотный inbox с приоритетом display identity

wide desktop (>= 1200 CSS px)
compact summary и filters
ordered inbox list | persistent Inspector

narrow desktop (< 1200 CSS px)
compact summary и filters
full-width inbox list
non-modal detail drawer после явной активации
```

Старая table не сохраняется как switch, feature flag, hidden fallback или responsive alias. Tiles, tabs, ARIA grid и listbox semantics отклонены.

## Семантика очереди

Queue — обычный semantic ordered list. Каждый item содержит ровно одну native button и создаёт один tab stop.

Button:

- использует compact card identity как accessible name;
- описывает priority, primary reason, bounded evidence, metadata и note scope;
- использует `aria-current` для active item;
- управляет текущей detail region;
- использует `aria-expanded` только в drawer mode;
- не содержит nested actions, checkbox, menu, preview или media read.

Focus и active state независимы. `Enter`, `Space` и click активируют item, но не перемещают focus на detail surface. Текущий item имеет textual и visual state и не определяется только цветом.

## Анатомия item

Порядок visual scan:

1. categorical priority и стабильная позиция в queue;
2. compact identity карточки, не более двух строк;
3. localized primary reason и количество дополнительных reasons;
4. одно bounded evidence sentence;
5. deck, card state и полезная metadata note type;
6. note scope и sibling impact, когда применимо;
7. detail affordance.

Из queue исключены numeric risk, raw reason codes, IDs, raw evidence objects, queries, fingerprints, profile/check IDs и preview HTML.

## Detail surfaces

`CardsDetail` переиспользуется wide Inspector и narrow drawer. Одновременно существует ровно одна detail surface и один active preview host.

### Wide Inspector

- persistent semantic `aside`;
- sticky и независимо scrollable при необходимости;
- width `clamp(380px, 34vw, 520px)`;
- queue column не сжимается уже 560 px.

### Narrow drawer

- labelled semantic `aside` с `role="region"`;
- fixed ниже application header;
- maximum geometry `min(640px, 100vw - 32px)`;
- без `aria-modal`, backdrop, inert shell и focus trap;
- queue остаётся operable;
- `Escape` и visible close control закрывают drawer;
- focus возвращается точному activating item либо queue heading fallback;
- activation другого item обновляет открытый drawer.

`AccessibleModal` остаётся единственным modal для answer preview. Его focus trap, portal и inert application boundary сохраняются. `Escape` сначала закрывает modal, затем drawer.

## Содержимое details и preview

Порядок sections:

1. priority и полная compact identity;
2. deck, note type и card state;
3. все canonical reasons с priority, scope, source и bounded evidence;
4. safe native front preview;
5. expanded answer через настоящий modal;
6. recommended step;
7. применимые single-card Safe Actions или Open in Anki;
8. Inspection Profile handoff, когда применимо;
9. collapsed safe technical identity;
10. lifecycle action/recheck C1.6.

Только active item запрашивает Search inspect schema v2. Queue items не рендерят preview HTML и не читают media. Один inspect cache переиспользуется Inspector, drawer и answer expansion.

## Learning period

Learning period — явный session-local state:

```text
7 дней — default
30 дней
90 дней
```

Он меняет только period-bound learning reasons/evidence. Current-content checks используют current collection и не считаются period-bound.

При изменении period:

- отменяются прежний query и continuation;
- запускается один automatic Triage v4 request с `contentCursor: null`;
- accumulated content pages очищаются;
- local filters сохраняются;
- active item сохраняется только при наличии в новом response;
- stale inspect/query/recheck responses не могут перезаписать current state.

`Clear filters` сбрасывает priority/reason/deck/text, но не period.

## Ручное continuation current-content scan

Continuation доступен только при coherent v4 cursor state: `truncated = true` и один non-null cursor.

Одна activation отправляет один automatic Triage v4 request с текущими period/deck scope, `contentCursor` и response limit. Automatic cursor loop отсутствует.

`mergeTriagePages()`:

- дедуплицирует items по `itemId`;
- объединяет reasons по `reasonId`;
- дедуплицирует sources/evidence;
- сохраняет canonical identity и inspect target;
- выбирает strongest categorical priority;
- сохраняет canonical ordering;
- суммирует progress;
- переносит latest coherent cursor;
- сохраняет существующие issues после continuation failure.

Client accumulation ограничено:

```text
500 unique items
10 additional content pages
```

Достижение limit показывается явно и не выдаётся за завершённый scan collection.

## Filters и coverage

Всегда видимые controls:

- priority;
- family/exact reason;
- deck;
- local visible-text match;
- learning period;
- refresh;
- clear filters при активных non-period filters.

Text filtering выполняется только по уже загруженным identity, deck, note type и localized reason labels. Он не становится arbitrary backend query.

Workspace coverage показывается один раз. Native `details` disclosure сообщает status learning/content/profiles/signals и progress current-content scan.

## Lifecycle C1.6

После существующего Safe Action или Open in Anki item переходит в `Awaiting recheck`. Action success и `action.no_changes` не доказывают resolution.

Явный `POST /api/triage/recheck`:

- оценивает одну exact card;
- переиспользует canonical detectors Triage v4;
- работает fail closed при partial/unavailable/stale evidence;
- выполняет reconciliation stable `reasonId`;
- удаляет item только после fully authoritative zero-reason result.

Возможные состояния:

```text
Still active
Partially resolved
Resolved
Recheck failed
Evidence stale
```

После полного resolution focus детерминированно переходит на следующий item, предыдущий item или queue heading.

Полный контракт: [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md).

## Accessibility и keyboard

- semantic list и native buttons;
- без `grid`, `listbox`, `option`, roving tabindex и arrow-key composite model;
- visible focus и textual active state;
- labelled/described items и detail region;
- polite live announcements;
- priority не определяется только цветом;
- drawer без focus trap и inert shell;
- deterministic focus restoration;
- reduced-motion drawer transition;
- modal answer behavior не меняется;
- busy state и conflicting-control disabling во время action/recheck.

## Bounds и performance

Initial server response ограничен 100 items. Loaded client queue — 500 unique items. Filtering local. Merge map/set based. Только active drawer владеет listener `Escape`.

Virtualization не вводится: measured fixture 100/500 items не требует второй rendering architecture.

## Сохраняемые контракты

- compact identity и safe fallback states C1.5R.1;
- Inspector-front / expanded-answer semantics C1.5R.3;
- Triage query v4 и cursor coherence C1.5R.4;
- Search inspect schema v2;
- loopback/token/content-type/body-size boundaries;
- sanitizer, trusted media validation и Shadow DOM isolation;
- single-card Safe Actions/Open in Anki;
- exact-card canonical recheck v1;
- reason-level removed/remaining/new reconciliation;
- deterministic focus recovery.

## Границы

C1.6 не добавляет selection/bulk controls, manual resolve, editor functionality, новые detectors, Triage query schema v5 или Search schema changes. Bulk actions остаются только условным C1.6B.