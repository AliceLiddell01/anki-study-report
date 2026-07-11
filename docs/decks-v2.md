# Decks v2 — иерархический центр состояния колод

Статус: **implemented in Stage 5**.

## Product role и route

Canonical route остаётся `#/decks`, видимое название — «Колоды». Страница
отвечает на вопрос: какие колоды требуют внимания, где находится проблема и
почему. Она показывает структуру, aggregate health, confidence и переход в
Anki Browser, но не заменяет будущую Statistics v1 и не реализует Cards v2.

Границы продукта:

- Today — текущий день и следующий шаг;
- Activity — scoped история по времени;
- Profile — all-collection lifetime view;
- Decks — scoped hierarchy, health и причины;
- Cards — конкретные карточки внимания.

## Scope и source rows

`StudyReport.deckHub` сохраняет dashboard scope из Settings Hub. Для selected
scope orchestration передаёт уже expanded deck IDs, если `includeChildDecks`
включён. Видимые selected nodes получают только свои scoped direct metrics;
существующие ancestors добавляются как `structuralOnly` context и не входят в
health counters.

Source данных:

```text
Anki current deck catalog (`col.decks.all()`)
+ direct current-home-deck card counts
+ scoped direct revlog/cache aggregates
        │
        └─ deck_hub.build_deck_hub(...)
```

Идентичность узла — стабильный `deckId` плюс полный canonical `fullName`.
`parentId` определяется по существующему canonical parent path; fake parents не
создаются. Duplicate short names остаются различимы по full path.

## Direct и subtree metrics

`directMetrics` — только данные самой колоды. `subtreeMetrics` — direct данные
узла и каждого видимого descendant, сложенные bottom-up ровно один раз.

Для subtree:

- counts суммируются из direct rows;
- pass rate считается из суммы Pass / reviews, не как среднее процентов;
- average answer time взвешивается через total answer seconds;
- active days — union cache date keys; для live source без date rows значение
  `null` и UI показывает «Нет данных»;
- parent row и основной detail используют subtree metrics;
- direct section показывается отдельно; parent без direct cards получает явный
  текст, а не искусственные нули.

Cache schema v2 относит временно перемещённую в filtered deck карту к её
текущей home deck через `odid`. Исторические moves/renames не
реконструируются; изменение schema вызывает controlled rebuild старого cache.

## Health, confidence и descendant issues

Health использует прежние Decks thresholds:

- сильный verdict только от 10 reviews;
- danger: pass rate ниже 70% или fail rate не ниже 32%;
- attention: pass rate ниже 80%, fail rate не ниже 20% или average answer не
  ниже 18 секунд;
- good: pass rate не ниже 90%, fail rate не выше 10% и нет slow signal;
- иначе normal.

Confidence является отдельным полем:

```text
sufficient   Данных достаточно
preliminary  Предварительная оценка
insufficient Недостаточно данных
```

`descendantIssueCount` считает реальные warning/danger descendants и не меняет
aggregate health родителя. Один problematic child входит в summary один раз,
а не повторяется через ancestors. `groupsWithDescendantIssues` отдельно считает
parent groups, содержащие такие nodes.

## Filtered decks

Filtered status берётся из фактического Anki deck `dyn`, не из имени.
Filtered decks:

- отсутствуют в `nodes`, subtree и health counters;
- не получают Browser actions;
- учитываются только безопасным `filteredDecksExcluded` count;
- не загрязняют normal totals, потому что cache/direct association использует
  current home deck при `odid > 0`.

## Search, filter, sort, selection и expansion

Search работает по full/short name, поддерживает Unicode, показывает match и
ancestors, временно раскрывает путь и не изменяет manual expansion state.

Filters: все, attention + danger, danger only, preliminary/insufficient.
Sort: name (default), status, reviews, success. Сортируются только siblings;
tie-breakers — name и deck ID. Числовые имена следуют обычному алфавитному
порядку Anki.

Roots видны сразу, branches collapsed. Chevron и selection — разные buttons.
Обычный вход выбирает первую root по имени; search предпочитает exact match;
status filter — сильнейший matching node. Скрытая selection откатывается к
видимому ancestor или первой видимой строке.

## Detail panel и actions

Detail показывает breadcrumb, health, confidence, максимум три причины,
metrics, direct/subtree distinction, до пяти descendant issues с раскрытием и
до двух существующих рекомендаций.

Typed action:

```json
{"deckId": 123, "mode": "subtree"}
{"deckId": 123, "mode": "direct"}
```

Backend заново разрешает current deck ID/name, отклоняет unknown/deleted,
filtered deck и неизвестный mode. Query строится только backend-side:

```text
deck:"<escaped full name>"
deck:"<escaped full name>" -deck:"<escaped full name>::*"
```

Quotes, backslashes, wildcards и HTML-significant characters экранируются.
Arbitrary query endpoint для Decks v2 не добавлен; существующий strict
`open-browser-search` остаётся для прежних card actions.

## Accessibility и layout

Используется semantic hierarchical list/table без fake `treegrid`. Disclosure
— настоящий button с `aria-expanded`; Enter/Space работают нативно. Selection
использует отдельный button с `aria-pressed`, focus ring отличается от selected
row. Full path доступен через `title`, а status/issues имеют текст, не только
цвет. Sticky detail не создаёт отдельного scroll/focus trap.

Desktop layout — примерно 60/40, на более узкой ширине detail переходит вниз.
Indentation ограничена пятью визуальными уровнями, deep path остаётся в
breadcrumb/full name.

## Payload contract и performance

`deckHub` additive и normalized:

```text
deckHub
├─ schemaVersion / scope / summary
├─ nodes { deckId -> node }
└─ rootIds[]
```

Legacy `decks` не удалён и продолжает обслуживать Home/Cards/старые fixtures.
В nodes нет recursive descendant copies, card/note content, raw revlog, token
или paths. Catalog собирается одним Anki backend call плюс одним grouped card
count query; aggregation — один bottom-up pass. Collapsed UI рендерит только
visible rows. Pure tests включают 161-node fixture. В clean Docker fixture с 23
public nodes compact `deckHub` занял 23 256 bytes; `/api/report` вырос с
145 134 до 168 401 bytes (+23 267 bytes, 16,03%). Рост линейный, card lists и
recursive descendant copies отсутствуют.

## Empty/edge states

Покрыты no decks, empty Default, filtered-only, one deck, parent without direct
cards, six levels, duplicate short names, long/Unicode names, missing parent,
duplicate/cyclic malformed input и 150+ decks. Corrupt references разрываются
детерминированно без recursion loop.

## Tests и Docker proof

Основные contracts:

```text
tests/test_deck_hierarchy.py
tests/test_dashboard_payload.py
tests/test_stats_cache.py
tests/test_browser_actions.py
tests/test_dashboard_actions.py
web-dashboard/src/lib/deckTree.test.ts
web-dashboard/src/pages/DecksPage.test.tsx
docker/anki-e2e/seed-collection.py
docker/anki-e2e/smoke-browser.mjs
```

Docker fixture содержит multiple roots, direct parent cards, healthy aggregate
с danger child, attention/preliminary nodes, duplicate short names, deep
Unicode hierarchy и filtered deck. Smoke проверяет hierarchy interactions,
обе Browser modes, token absence, console/network errors и light/dark Decks
screenshots в artifact manifest.

## Explicit non-goals

Нет deck create/rename/delete, drag-and-drop, deck options, card moving,
custom health thresholds, historical deck trends, filtered analytics,
Statistics/FSRS page, Search route, Notifications, Cards v2 и mobile-first
drawer.
