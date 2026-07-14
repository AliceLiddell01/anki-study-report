# Search v1 и Safe Actions

Статус: реализовано для Anki 26.05; снимок 2026-07-15.

## Search v1

Search доступен на `#/search` между «Колоды» и «Карточки» в primary navigation.
Запрос запускается только по кнопке/Enter: ввод не создаёт фоновых запросов.
Нативная строка Anki, выбранный режим, фильтры, сортировка и page size хранятся
в `sessionStorage`; результаты, selection и inspector после reload не
восстанавливаются и auto-query не выполняется. Raw query не попадает в URL,
title, normal logs или публичные E2E-артефакты.

Режим `Cards` показывает primary text, deck, note type, template, state, due,
interval, reviews, lapses и flag. Режим `Notes` показывает primary text, note
type, tags, card count и decks. Card-only state/flag filters очищаются при
переходе в Notes. Структурные deck/note type/tag filters объединяются с native
query backend-ом через Anki search nodes, а не строковой конкатенацией.

Deck и note type controls лениво запрашивают all-collection metadata через
строгий variant `POST /api/search/query`:

```json
{"kind":"metadata","requestId":"search-metadata-1"}
```

Ответ содержит bounded каталоги `decks` (`deckId`, `deckName`, `filtered`) и
`noteTypes` (`noteTypeId`, `noteTypeName`), а также truncation markers. Пока
metadata не запрошена или временно недоступна, scoped report catalogs остаются
только UI fallback. Move picker использует live catalog и исключает filtered
колоды; backend всё равно повторно разрешает destination по ID непосредственно
перед native operation.

Pagination использует `pageCount`, page sizes `25|50|100`, hard cap 2000 и
не загружает все details заранее. Inspector выполняет отдельный bounded inspect
только после выбора строки. Текст рендерится React-ом как plain text: template
JavaScript, iframe, rich preview HTML и external media здесь не исполняются.

Selection содержит только явные decimal string IDs, сохраняется между
страницами одного query fingerprint, header checkbox действует только на
текущую страницу, cap — 200. `Open in Anki Browser` отправляет mode+IDs на
allowlisted `open-search-selection`; backend заново разрешает каждый ID и
строит bounded `cid:`/`nid:` query.

Ошибки validation, stale entity, unavailable runtime, timeout и malformed
response показываются локализованно. Новый запрос отменяет предыдущий client
request и только последний response может заменить state. Truncation и bounded
total показываются явно. Не реализованы saved searches, arbitrary columns,
inline note editing, Cards v2, template preview и remote/cloud search.

## Safe Actions

Mutation endpoints отделены по типу:

```text
POST /api/entities/cards/actions?token=<token>
POST /api/entities/notes/actions?token=<token>
```

Card allowlist: `suspend`, `unsuspend`, `set_flag`, `clear_flag`, `bury`,
`unbury`, `move_to_deck`. Note allowlist: `add_tags`, `remove_tags`. Toggle,
reflection, generic method name, raw SQL, note-level bury и move note отсутствуют.

Пример card request:

```json
{"action":"set_flag","cardIds":["123"],"flag":3,"requestId":"cards-1"}
```

Пример note request:

```json
{"action":"add_tags","noteIds":["456"],"tags":["Japanese::Grammar"],"requestId":"notes-1"}
```

Response находится в `{"ok":true,"response":...}` и содержит
`schemaVersion`, `entityType`, `action`, `requestedCount`, `affectedCount`,
`unchangedCount`, `undoable`, `resultCode`, safe `args` и optional `requestId`.
Stable result codes: `cards.suspended`, `cards.unsuspended`, `cards.flag_set`,
`cards.flag_cleared`, `cards.buried`, `cards.unburied`, `cards.moved`,
`notes.tags_added`, `notes.tags_removed`, `action.no_changes`. Frontend
локализует codes; backend English message остаётся вторичной диагностикой.
Frontend runtime validator также сверяет action с result code, args, counts и
undoable marker, поэтому противоречивый success envelope не принимается.

Полный request валидируется до mutation: только JSON object, unknown fields
запрещены, ID — уникальные positive decimal strings, batch `1..200`, body не
больше 8 KiB. Tags: не больше 20 после нативного space parsing, не больше 1000
символов суммарно, без control characters; case/hierarchy `::` передаются
нативному Anki tag layer. Любой stale ID отклоняет всю пачку.

Изменяющая пачка выполняется одним официальным Anki wrapper/
`CollectionOp` и создаёт один native undo step. Используются
`suspend_cards`, `unsuspend_cards`, `set_card_flag`, `add_tags_to_notes`,
`remove_tags_from_notes`, `bury_cards`, `unbury_cards`, `set_card_deck`.
No-op не запускает mutation и возвращает `action.no_changes`, `undoable=false`.
Finite HTTP wait — 20 секунд; timeout не объявляется успехом.

Bury — явное временное состояние выбранных card IDs без sibling expansion.
Unbury также явный, не toggle. Move принимает только server-resolved `deckId`:
destination должна существовать и быть normal deck. Filtered/dynamic
destination отклоняется. Карточки с `odid > 0` также отклоняются кодом
`cards.filtered_source_unsupported`: Anki 26.05 `set_card_deck()` извлекает
такие карточки из filtered deck и очищает FSRS data, поэтому dashboard не
угадывает семантику домашней колоды.

После подтверждённого действия frontend повторяет текущий query, исправляет
page к ближайшему допустимому, очищает/reconciles selection и повторно читает
активный inspector, если entity осталась на странице. Query/mode/filters/sort/
page size сохраняются. Одновременно запускается не больше одной mutation.

Отложены: delete, reschedule, change note type, field editing, bulk template
operations, arbitrary tag/deck commands и действия над неявно расширенными
наборами.

## Проверки

Focused contracts: `tests/test_search_metadata.py`,
`tests/test_entity_actions.py`, `tests/test_entity_action_runtime.py`,
`tests/test_dashboard_server.py`, `web-dashboard/src/lib/searchMetadataApi.test.ts`,
`web-dashboard/src/lib/entityActionsApi.test.ts`, `SearchPage.test.tsx` и
`SearchMetadataIntegration.test.tsx`. Targeted real-Anki proof входит в
`standard/global` и пишет redacted `search-query-contract.json`: только
codes/counts/state summaries, Browser errors и `collectionStable`, без
token/raw query/tag content/ID lists.
