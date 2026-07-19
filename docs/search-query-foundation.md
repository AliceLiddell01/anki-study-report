# Search Query Foundation

Снимок документации: 2026-07-19.

Этот слой — read-only основа Search. Он выполняет нативный запрос Anki для
Cards и Notes, возвращает compact metadata для all-collection filter controls и
строит bounded-данные выбранной Card/Note. C1.5R.1 обновил card identity и
Search query/inspect до schema v2; metadata остаётся schema v1.

## Границы модулей

- `search_service.py` валидирует query/inspect, вызывает
  `find_cards()`/`find_notes()` и строит bounded-проекции.
- `card_display_identity.py` — единственный backend projector compact card
  identity для Search, exact-card resolution и Triage.
- `search_metadata.py` владеет отдельным metadata request/response v1.
- `search_runtime.py` запускает collection read через serialized `QueryOp`.
- `dashboard_server.py` владеет token/HTTP/method/body/status contract.
- `web-dashboard/src/types/search.ts` и `lib/searchApi.ts` содержат строгие v2
  types и runtime parsers.
- frontend не получает прямой доступ к collection.

Нативная грамматика остаётся грамматикой Anki. Compact card identity использует
официальный card renderer в двух контекстах: Browser question, затем reviewer
front. Она не строится из arbitrary note fields.

## Endpoints

Оба endpoint требуют dashboard token, принимают только `POST`, JSON object не
больше 8192 байт и не логируют query/token:

```text
POST /api/search/query?token=<token>
POST /api/search/inspect?token=<token>
```

Query v2:

```json
{
  "schemaVersion": 2,
  "mode": "cards",
  "query": "deck:Japanese tag:marked",
  "filters": [{"type": "deck", "deckId": "123"}],
  "sort": {"key": "entity_id", "direction": "asc"},
  "page": 1,
  "pageSize": 50,
  "requestId": "search-42"
}
```

Inspect v2:

```json
{"schemaVersion":2,"mode":"cards","cardId":"123","requestId":"inspect-1"}
{"schemaVersion":2,"mode":"notes","noteId":"456","requestId":"inspect-2"}
```

Missing/wrong schema and unknown fields are rejected. V1 is not a compatibility
alias because card row semantics changed.

## Search metadata v1

Metadata intentionally remains a separate v1 variant on the query endpoint:

```json
{"kind":"metadata","requestId":"search-metadata-1"}
```

Response contains schemaVersion 1, bounded deck/note-type catalogs and
truncation markers. The v2 query schema does not leak into metadata and metadata
is not accepted as a query alias.

## Query and pagination

`mode` is `cards|notes`; query length is at most 4096. Filters are an AND-list
of at most 12 `deck`, `note_type`, `tag`, and card-only `state`/`flag` entries.
Only deterministic `entity_id asc|desc` sort is accepted. Page sizes are
`25|50|100`, with hard result cap 2000.

`find_cards()`/`find_notes()` first return matching IDs. The service sorts and
deduplicates IDs, caps the considered set to 2000, and loads Card/Note objects
only for the requested page. `pageCount` describes actual bounded pages;
`pageLimit` is derived from the hard cap. This is not a database cursor.

## Card row v2

A card row contains exact card/note/deck/note-type/template identity, scheduling
state and:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

The four fields are produced by `project_card_display_identity(card)`. The
projector:

1. renders Browser Appearance question;
2. falls back to native reviewer front;
3. emits explicit media-only/unavailable state.

It removes active/embedded content, media markers and filenames; keeps inline
Japanese nodes adjacent; selects the first meaningful rendered line; and bounds
the result to 240 characters. It never scans the note sort field or first
non-empty field, never renders answer/back, and never reads media files.

`primaryText` is not present on card rows or card details in schema v2.

## Note row v2

Note-mode Search remains note-centric. It retains `primaryText` derived from the
note sort field and subsequent fields, plus tags/card/deck summaries. It does
not receive `displayText` or card display state because one note may generate
multiple cards.

## Inspect

Card inspect reuses the same card row projector, so its compact heading equals
the Search row and Triage/Cards identity for the same exact card. It additionally
returns bounded metadata and the existing sanitized `renderedPreview`.

Note inspect retains bounded note fields, tags, card references and deck
summaries. Deleted/stale entities return `404 search_entity_not_found`.

Errors remain typed:

```text
400 invalid_search_request
404 search_entity_not_found
503 search_unavailable | search_failed
504 search_timeout
```

Tracebacks, raw query, collection path, media filenames and token do not enter
product responses.

## Frontend parser

The v2 parser validates exact top-level and nested keys, decimal-string IDs,
counts/pagination, enums and display-state coherence. It rejects:

- schema v1 query/inspect payloads;
- `primaryText` on a card row/detail;
- missing or extra display fields;
- future/unknown keys;
- available identity with empty text;
- media-only/unavailable identity with incoherent source/text/truncation.

## Verification

C1.5R.1 is **Complete**. C1.5R.2 adds an optional request-local declarative
formatter resolver while Search query/inspect remains exact schema v2 and
metadata remains v1. R2 completion still requires the owner-checkout focused
frontend, package, canonical non-Docker and Git hygiene gates.

## C1.5R.3 preview semantics

See [`card-preview-semantics.md`](card-preview-semantics.md). Full preview uses reviewer/native front and answer; Inspector shows front, expanded dialog shows answer, and compact identity remains unchanged.
