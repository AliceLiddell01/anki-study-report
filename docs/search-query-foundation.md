# Search Query Foundation

Снимок документации: 2026-07-15.

Этот слой — read-only основа реализованного Search v1. Он выполняет нативный
запрос Anki для Cards и Notes и возвращает компактные данные выбранной
Card/Note; route, таблица, inspector, selection и отдельный mutation boundary
описаны в `docs/search-v1-and-safe-actions.md`.

## Границы модулей

- `search_service.py` валидирует контракт, собирает структурные фильтры через
  `SearchNode`/`build_search_string()`, вызывает `find_cards()`/`find_notes()` и
  строит безопасные bounded-проекции.
- `search_runtime.py` запускает collection read через сериализованный `QueryOp`,
  возвращает результат HTTP-потоку через finite wait и нормализует ошибки.
- `dashboard_server.py` владеет token/HTTP/method/body/status contract.
- `web-dashboard/src/types/search.ts` и `lib/searchApi.ts` — строгие типы и
  runtime client страницы `#/search`; frontend не получает прямой доступ к collection.
- `browser_actions.py` остаётся отдельным узким слоем для открытия native
  Browser и не используется как grammar/service нового read API.

Нативная грамматика остаётся грамматикой Anki: см. официальные справочники
[Searching](https://docs.ankiweb.net/searching.html) и
[Browsing](https://docs.ankiweb.net/browsing.html). Background collection read
следует модели [Background Operations](https://addon-docs.ankiweb.net/background-ops.html).

## API

Оба endpoint требуют текущий dashboard token, принимают только `POST`, JSON
object не больше 8192 байт и не логируют query/token:

```text
POST /api/search/query?token=<token>
POST /api/search/inspect?token=<token>
```

Query request:

```json
{
  "mode": "cards",
  "query": "deck:Japanese tag:marked",
  "filters": [{"type": "deck", "deckId": "123"}],
  "sort": {"key": "entity_id", "direction": "asc"},
  "page": 1,
  "pageSize": 50,
  "requestId": "search-42"
}
```

`mode` — `cards|notes`; native `query` — строка до 4096 символов. `filters` —
AND-список максимум из 12 элементов: `deck`, `note_type`, `tag`, а в Cards
mode также `state` и `flag`. Deck/note type принимают decimal ID string и
разрешаются backend-ом в актуальное имя. Единственный sort v1 —
`entity_id asc|desc`; произвольный SQL/order запрещён. Допустимые `pageSize`:
25, 50, 100; default — 50.

Успешный HTTP envelope имеет вид `{"ok":true,"response":{...}}`. Query
response различает `cards`/`notes` и содержит `items`, `page`, `pageSize`,
`pageCount`, `pageLimit`, `returnedCount`, `boundedTotal`, `hasNext`,
`truncated`, `sort` и переданный `requestId`. Frontend runtime validator
проверяет каждый обязательный row/detail field, вложенные summary/reference
объекты и согласованность всей pagination metadata; неполный success payload
отклоняется как `invalid_search_response`. Все Anki IDs сериализуются decimal
strings, чтобы не терять точность в JavaScript.

Inspect request принимает ровно один mode-specific ID:

```json
{"mode":"cards","cardId":"123","requestId":"inspect-1"}
{"mode":"notes","noteId":"456","requestId":"inspect-2"}
```

Удалённая/устаревшая сущность возвращает `404 search_entity_not_found`.
Validation — `400 invalid_search_request`, отсутствие runtime — `503
search_unavailable`, безопасно нормализованная runtime failure — `503
search_failed`, finite wait — `504 search_timeout`. Traceback, raw query,
collection path и token в product response не попадают.

## Bounding и pagination

`find_cards()`/`find_notes()` сначала возвращают matching IDs. Сервис
детерминированно сортирует уникальные ID, ограничивает рассматриваемый набор
первыми 2000 и загружает Card/Note objects только для запрошенной страницы.

- hard result cap: 2000;
- `pageCount = ceil(boundedTotal / pageSize)` — число фактических bounded pages;
- `pageLimit = ceil(2000 / pageSize)` — предел допустимого номера запроса: 80
  для 25, 40 для 50, 20 для 100;
- пустой набор возвращает `page=1`, `pageCount=0` и пустой `items`;
- допустимая по `pageLimit` страница за текущим `pageCount` возвращается пустой;
- запрос страницы за `pageLimit` отклоняется validation layer;
- `truncated=true`: native match содержал больше 2000 IDs;
- `boundedTotal`: размер capped набора, а не обещание полного collection count;
- offset/page не является snapshot cursor: если collection изменилась между
  запросами, состав и смещения следующей страницы могут измениться.

Оставшееся ограничение: native search всё равно вычисляет полный список
matching IDs до cap. Поэтому работа вынесена в serialized background operation,
но стоимость очень широкого запроса на большой collection не становится
стоимостью настоящего database cursor.

## Безопасный текст и модели

Cards и Notes имеют отдельные row/details модели. `primaryText` берётся из sort
field текущего note type, затем из первого непустого field. HTML, script/style,
iframe/object/embed/svg/math, media markers и cloze syntax преобразуются в
plain text; row ограничен 240 символами. Note inspect ограничен 64 fields,
2000 символами на value, 50 tags, 100 card references и 20 deck summaries.
Rich preview HTML, template JavaScript и media files этот API не возвращает и
не исполняет.

## Metadata не дублируется

Отдельный metadata/catalog endpoint не добавлен. Текущие report/settings
contracts уже публикуют deck choices и note type catalog для существующих
экранов; states, flags и sort v1 — конечные enums в typed contract. Полный tag
catalog пока не требуется shipping consumer. Search UI переиспользует
`deckHub` и `noteTypeCatalog`, не создавая второй source of truth.

## Проверки

Локальный контур:

```powershell
python -m pytest -q tests/test_search_service.py tests/test_search_runtime.py tests/test_dashboard_server.py
cd web-dashboard
pnpm exec vitest run src/lib/searchApi.test.ts
pnpm run typecheck
```

Real-Anki contract расширяет существующий browser smoke для `global`/`full` и
пишет redacted `reports/search-query-contract.json`: valid/invalid token,
Cards/Notes native query, `pageCount`/`pageLimit`, оба полных inspect, Search UI,
Browser bridge, safe action cycles и восстановление collection baseline.
Seed/APKG scripts полагаются на автоматическое сохранение Collection
в Anki 26.05; deprecated collection-level `save()` не вызывается, а отдельный
`col.decks.save(deck)` сохраняется для изменённого deck-manager entity.
