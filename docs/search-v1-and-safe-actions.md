# Search и Safe Actions

Статус: Search query/inspect schema v2; Safe Actions schema v1; снимок
2026-07-19.

## Search

Search доступен на `#/search` между «Колоды» и «Карточки». Запрос запускается
только по кнопке/Enter. Query, mode, filters, sort и page size сохраняются в
`sessionStorage`; результаты, selection и Inspector после reload не
восстанавливаются. Raw query не попадает в URL, title, normal logs или публичные
артефакты.

Query и inspect требуют `schemaVersion: 2`. Metadata catalog остаётся отдельным
schema v1 request variant.

### Cards mode

Cards mode показывает canonical compact card identity, deck, note type,
template, state, due, interval, reviews, lapses и flag. Card identity содержит:

```text
displayText
displaySource
displayStatus
displayTruncated
```

Search row и Search Inspector heading используют один backend projector. Он
сначала читает native Browser question, затем reviewer front и иначе возвращает
explicit media-only/unavailable state. Arbitrary note fields больше не являются
fallback card identity. Старого card `primaryText` alias в schema v2 нет.

### Notes mode

Notes mode остаётся note projection: `primaryText`, note type, tags, card count
и decks. Card-only state/flag filters очищаются при переходе в Notes. Note mode
не получает card display fields.

### Metadata and pagination

Deck/note-type controls лениво запрашивают all-collection metadata через strict
v1 variant:

```json
{"kind":"metadata","requestId":"search-metadata-1"}
```

Query v2 использует native Anki grammar, bounded structured filters,
`pageCount`, page sizes `25|50|100` и hard cap 2000. Inspector выполняет
отдельный bounded v2 inspect только после выбора строки.

### Selection and Browser handoff

Selection содержит только explicit decimal string IDs, сохраняется между
страницами одного query fingerprint, header checkbox действует на текущую
страницу, cap — 200. `Open in Anki Browser` отправляет exact mode+IDs через
allowlisted `open-search-selection`; display text никогда не становится native
query.

### Strict parsing and errors

Frontend parser проверяет exact keys, schema, IDs, nested summaries, pagination
metadata и display-state coherence. Schema v1 query/inspect, aliases, unknown
fields and malformed success payloads fail closed as
`invalid_search_response`.

Backend errors remain:

```text
invalid_search_request
search_entity_not_found
search_unavailable
search_failed
search_timeout
```

## Safe Actions

Mutation endpoints остаются отдельными:

```text
POST /api/entities/cards/actions?token=<token>
POST /api/entities/notes/actions?token=<token>
```

Card allowlist: `suspend`, `unsuspend`, `set_flag`, `clear_flag`, `bury`,
`unbury`, `move_to_deck`. Note allowlist: `add_tags`, `remove_tags`. Generic
method invocation, arbitrary SQL, delete, note-level bury and move-note
отсутствуют.

Request validates exact JSON, unique positive decimal IDs, batch `1..200`, body
up to 8 KiB, bounded tags and server-resolved deck destinations. Any stale ID
rejects the whole batch. Changing batches use official Anki operation wrappers
and one native undo step; no-op returns `action.no_changes` without mutation.

After success frontend repeats the current v2 query, reconciles page/selection
and repeats active v2 inspect when the exact entity remains. Search identity
does not affect mutation scope or resolution.

## Security and privacy

Frontend never reads collection directly. Token protection, loopback binding,
action allowlists, sanitizer, media validation and preview isolation remain.
Compact identity, queries, IDs, deck/note/template names, field values and media
filenames are not added to remote telemetry.

## C1.6 reuse

C1.6 reuses this exact single-card action transport from the Cards Inspector.
Action success and `action.no_changes` remain action results only; Cards requires
its separate canonical exact-card recheck before declaring resolution. Search
selection/bulk semantics and mutation scope are unchanged.
