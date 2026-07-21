# Dashboard API и payload contract

**Снимок документации:** 2026-07-22

Dashboard — локальное приложение, которое получает опубликованный report payload и несколько узких API. Frontend не читает Anki collection напрямую.

## Token model

Все чувствительные endpoints требуют текущий dashboard token:

```text
?token=<dashboard-token>
```

Dashboard открывается по loopback URL:

```text
http://127.0.0.1:<port>/?token=<token>#/home
```

Invalid token возвращает `403`. Token и полный token-bearing URL не попадают в normal logs, DOM dumps, public artifacts или telemetry.

## Карта endpoints

### Основные GET

```text
/api/status
/api/health
/api/server/status
/api/report
/api/media
/api/cache/status
/api/dashboard/settings
/api/profile
/api/logs/status
/api/logs/recent
/api/logs/download
/api/integrations/status
/api/notifications/summary
/api/notifications
/api/settings/notifications
/api/notifications/toasts
/api/telemetry/status
```

### Основные POST/PUT

```text
/api/cache/rebuild
/api/cache/refresh
/api/server/<action>
/api/logs/clear
/api/dashboard/settings
/api/profile
/api/statistics/query
/api/statistics/fsrs/query
/api/search/query
/api/search/inspect
/api/triage/query
/api/triage/recheck
/api/inspection-profiles/query
/api/inspection-profiles/validate
/api/inspection-profiles/update
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
/api/entities/cards/actions
/api/entities/notes/actions
/api/actions/<action>
/api/notifications/read
/api/notifications/read-all
/api/settings/notifications
/api/notifications/toasts
/api/notifications/toast-delivered
/api/telemetry/events
/api/telemetry/delete
/api/telemetry/check-send
```

Server/dashboard actions остаются allowlist, а не arbitrary RPC.

## Search query и inspect

`POST /api/search/query` и `POST /api/search/inspect`:

- token-protected;
- POST-only;
- JSON-only;
- body cap 8 KiB.

Normal query и inspect требуют exact `schemaVersion: 2`. Schema v1 не является alias. Query использует native Anki grammar, bounded filters, page sizes `25 | 50 | 100` и hard cap 2000. Inspect принимает ровно один decimal-string `cardId` или `noteId`.

Card rows/details v2:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

Card alias `primaryText` отсутствует. Note rows/details сохраняют note `primaryText` и не получают card display fields.

Frontend parser отклоняет old schemas, aliases, unknown keys, malformed IDs, count drift и incoherent display state.

Search metadata остаётся отдельным request variant v1:

```json
{"kind": "metadata", "requestId": "search-metadata-1"}
```

Search errors:

```text
400 invalid_search_request
404 search_entity_not_found
503 search_unavailable
503 search_failed
504 search_timeout
```

Полный контракт: [`search-v1-and-safe-actions.md`](search-v1-and-safe-actions.md).

## Triage query v4

`POST /api/triage/query`:

- token-protected;
- POST/JSON-only;
- body cap 8 KiB;
- exact `schemaVersion: 4`.

Automatic query объединяет bounded period-learning, current-content, active Signal и Search identity sources. Current-content continuation является manual и cursor-bounded. Search workset принимает `1..200` exact card IDs и сохраняет first-seen order.

Response содержит typed source/content status, counts, cursor coherence, stable reasons и Search-owned compact identity. Full preview/media, raw revlog, note values, arbitrary query, exception, token и runtime path отсутствуют.

## Exact-card recheck v1

`POST /api/triage/recheck`:

- token-protected;
- POST/JSON-only;
- body cap 8 KiB;
- exact `schemaVersion: 1`;
- serialized through `QueryOp`.

Request содержит:

```text
cardId
expectedNoteId
reasonIds (1..4)
scope
```

Recheck оценивает только exact card и переиспользует canonical sources Triage v4. Response возвращает typed source status, `entityStatus`, `contentChecks` и current canonical item либо `null`.

Resolved допустим только при fully authoritative coverage и нуле current reasons. Partial/unavailable/error source, profile-authority change, identity mismatch, missing/changed entity или collection failure работают fail closed.

Полные контракты:

- [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md);
- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md).

## Card display formatter API

Endpoints:

```text
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
```

Они token-protected, POST-only, используют exact schema v1 и body cap 64 KiB.

Store statuses:

```text
empty | available | corrupt | future_schema | unavailable
```

`validate` ничего не сохраняет и не читает collection. `update` принимает только `save`/`delete` с `expectedRevision`. API не раскрывает raw HTML, note values, media contents, paths, renderer exceptions или arbitrary expression language.

Полный контракт: [`card-display-formatter-v1.md`](card-display-formatter-v1.md).

## Inspection Profiles API

```text
POST /api/inspection-profiles/query
POST /api/inspection-profiles/validate
POST /api/inspection-profiles/update
```

Endpoints используют current token, strict JSON и cap 64 KiB.

Query возвращает bounded structures, fingerprints, lifecycle, stored profile и non-authoritative suggestion. Validation read-only. Update изменяет local profile store с optimistic revision/fingerprint checks.

Content reasons создают только confirmed/current profiles. Suggested, disabled, needs-review, missing, future, corrupt и unavailable states fail closed.

Полный контракт: [`inspection-profiles-v1.md`](inspection-profiles-v1.md).

## Entity actions API

```text
POST /api/entities/cards/actions
POST /api/entities/notes/actions
```

Требования: token, POST, JSON, body cap 8 KiB.

Card allowlist:

```text
suspend | unsuspend | set_flag | clear_flag | bury | unbury | move_to_deck
```

Note allowlist:

```text
add_tags | remove_tags
```

Batch содержит `1..200` exact decimal IDs. Один stale ID отклоняет весь batch. Mutations используют official Anki wrappers и один native undo step.

Action success, включая `action.no_changes`, не доказывает resolution Cards. Resolution определяется только явным `/api/triage/recheck`.

## Settings и Profile API

`GET/POST /api/dashboard/settings` публикует normalized public settings и принимает только allowlisted partial patches.

`GET/POST /api/profile` публикует public profile data. Writable fields:

```text
customStudyStartedOn
deckOverviewSort
```

Computed identity и metrics read-only.

## Statistics и FSRS

`POST /api/statistics/query` принимает typed scope/period/granularity/comparison.

`POST /api/statistics/fsrs/query` принимает documented read-only FSRS operations.

Arbitrary search/SQL и raw revlog/card/note rows запрещены.

## Notifications и telemetry

Notification endpoints используют bounded schema v1 и local notification IDs. Telemetry endpoints принимают только opt-in bounded technical events.

Remote telemetry исключает collection content, field names/values, Search queries, card/note/deck IDs, compact display text, media filenames и token-bearing URLs.

## Payload source of truth

Backend:

```text
anki_study_report/dashboard_payload.py
```

Frontend:

```text
web-dashboard/src/types/report.ts
```

Canonical Cards использует `/api/triage/query` и `/api/triage/recheck`. Legacy `attentionCards` остаётся compatibility surface для других consumers.

## Preview и media

Search inspect содержит sanitized `renderedPreview` рядом с compact identity. Full preview загружается только для active card.

Media URL:

```text
/api/media?name=<validated-media-name>&token=<token>
```

Обязательны backend filename validation, sanitizer, Shadow DOM isolation и token checks. `file:`, `javascript:`, iframe и template JavaScript execution запрещены.

## Текущий статус Core

```text
C1.5R.0–R.7 — Complete; owner accepted
C1.6 — Complete; owner accepted; merged into core
C1.6B — Conditional; not started
Core C1 — Complete
C2 — Next; not started
```