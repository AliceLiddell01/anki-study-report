# Search и Safe Actions

**Статус:** Search query/inspect schema v2; Search metadata schema v1; Safe Actions schema v1  
**Снимок:** 2026-07-22

## Search

Search доступен по маршруту `#/search`. Query выполняется только по явному submit или `Enter`.

В `sessionStorage` сохраняются:

- query;
- mode;
- filters;
- sort;
- page size.

Results, selection и Inspector после reload не восстанавливаются. Raw query не попадает в URL, title, normal logs или public artifacts.

### Cards mode

Cards mode показывает:

- canonical compact identity;
- deck;
- note type;
- template;
- state;
- due;
- interval;
- reviews;
- lapses;
- flag.

Card identity:

```text
displayText
displaySource
displayStatus
displayTruncated
```

Search row и Search Inspector используют один backend projector:

```text
Browser question
→ reviewer front
→ media_only | unavailable
```

Произвольные fields note не используются как fallback. Card alias `primaryText` отсутствует.

### Notes mode

Notes mode сохраняет note projection:

- `primaryText`;
- note type;
- tags;
- card count;
- decks.

Card-only filters очищаются при переходе в Notes. Note mode не получает card display fields.

### Metadata и pagination

Metadata request:

```json
{"kind": "metadata", "requestId": "search-metadata-1"}
```

Query v2 использует native Anki grammar, bounded structured filters, page sizes `25 | 50 | 100` и hard cap 2000.

Inspect v2 загружает одну exact entity после выбора result.

### Selection и Browser handoff

Selection содержит только unique positive decimal IDs, сохраняется между pages одного query fingerprint и ограничено 200 entities.

`Open in Anki Browser` передаёт exact mode и IDs через allowlisted action `open-search-selection`. Display text никогда не преобразуется в native query.

### Strict parsing и errors

Frontend parser проверяет exact keys, schemas, IDs, nested summaries, pagination metadata и coherence display state.

Invalid success payload:

```text
invalid_search_response
```

Backend errors:

```text
invalid_search_request
search_entity_not_found
search_unavailable
search_failed
search_timeout
```

## Safe Actions

Mutation endpoints:

```text
POST /api/entities/cards/actions?token=<token>
POST /api/entities/notes/actions?token=<token>
```

Card allowlist:

```text
suspend
unsuspend
set_flag
clear_flag
bury
unbury
move_to_deck
```

Note allowlist:

```text
add_tags
remove_tags
```

Отсутствуют generic method invocation, arbitrary SQL, delete, note-level bury и move-note.

Request валидирует:

- exact JSON shape;
- unique positive decimal IDs;
- batch `1..200`;
- body cap 8 KiB;
- bounded tags;
- destination deck, разрешённую server.

Один stale ID отклоняет весь batch до mutation. Изменения используют official Anki operation wrappers и создают один native undo step. No-op возвращает `action.no_changes` без mutation.

## Связь Safe Actions с Cards C1.6

Safe Actions остаются единственным mutation path Cards. Open in Anki остаётся единственным native editing handoff.

Успех action и `action.no_changes` не являются resolution proof.

Lifecycle:

```text
Safe Action или Open in Anki
→ Awaiting recheck
→ POST /api/triage/recheck
→ reason reconciliation
```

Только fully authoritative exact-card recheck с нулём current reasons может удалить item из automatic queue.

Search identity, display text и action result не используются для client-side inference resolution.

Полный контракт:

- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md).

## Обновление Search после mutations

После успешного Search action frontend:

1. повторяет current query v2;
2. согласует page и selection;
3. повторяет active inspect v2, если entity существует.

Этот Search refresh не заменяет Cards recheck lifecycle.

## Безопасность и приватность

Frontend не читает collection напрямую. Сохраняются:

- token protection;
- loopback binding;
- action allowlists;
- sanitizer;
- media validation;
- preview isolation.

Compact identity, queries, IDs, deck/note/template names, field values и media filenames не добавляются в remote telemetry.