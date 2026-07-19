# Dashboard API и payload-контракт

Снимок документации: 2026-07-19.

Dashboard — локальное приложение, которое получает опубликованный report payload
и несколько narrow API. Frontend не читает Anki collection напрямую.

## Token model

Все чувствительные endpoints требуют текущий dashboard token:

```text
?token=<dashboard-token>
```

Dashboard открывается на loopback URL вида:

```text
http://127.0.0.1:<port>/?token=<token>#/home
```

Неверный token возвращает `403`. Token и полный token-bearing URL не попадают в
normal logs, DOM dumps, public artifacts или telemetry.

## Endpoint map

Основные GET:

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

Основные POST/PUT:

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

Server/dashboard actions remain an allowlist, not arbitrary RPC.

## Search query and inspect

`POST /api/search/query` and `POST /api/search/inspect` are token-protected,
POST-only, JSON-only and capped at 8 KiB.

### Query/inspect schema v2

Normal query and inspect requests require exact `schemaVersion: 2`. Missing or
wrong schema and unknown keys return `400 invalid_search_request`. Schema v1 is
not accepted as an alias.

Query uses native Anki grammar, bounded structured filters, page sizes
`25|50|100` and hard cap 2000. Inspect accepts exactly one decimal-string
`cardId` or `noteId`.

Card rows/details in v2 contain:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

They do not contain card `primaryText`. Note rows/details retain note
`primaryText` and do not receive card display fields.

The backend projector renders Browser question, then reviewer front, then emits
explicit media-only/unavailable state. It never scans arbitrary note fields.
Search row and Search inspect reuse the same projection.

The frontend parser rejects old schemas, aliases, unknown keys, malformed IDs,
count drift and incoherent display status/source/text combinations.

### Metadata schema v1

Search metadata remains an independent exact v1 request variant:

```json
{"kind":"metadata","requestId":"search-metadata-1"}
```

It returns bounded deck/note-type catalogs and truncation markers. Metadata is
not silently upgraded to v2 and v2 query requests are not accepted as metadata.

### Search errors

```text
400 invalid_search_request
404 search_entity_not_found
503 search_unavailable
503 search_failed
504 search_timeout
```

Full contract: [`search-query-foundation.md`](search-query-foundation.md).

## Card display formatter API

C1.5R.2 adds three token-protected, POST-only, `application/json` endpoints with
a 64 KiB body cap:

```text
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
```

All requests use exact `schemaVersion: 1` and reject unknown keys.

`query` accepts only:

```json
{"schemaVersion":1}
```

Its response contains the independent store status, revision, strict formatter
entries, generic `errorCode`, and `quarantined` flag. Allowed status values are:

```text
empty | available | corrupt | future_schema | unavailable
```

`validate` accepts one strict formatter and performs no collection read or
persistence. `update` accepts only exact `save` or `delete` actions with
`expectedRevision`; deletion identifies one `(noteTypeId, templateOrdinal)` key.
A stale revision returns the current revision with HTTP 409.

The API exposes no raw HTML, note values, media contents, filesystem paths,
renderer exceptions, arbitrary expression language, or live card preview.
Search remains schema v2 and Triage remains schema v3; formatter configuration is
not added to either payload.

Full contract: [`card-display-formatter-v1.md`](card-display-formatter-v1.md).

## Canonical triage read API

`POST /api/triage/query` is token-protected, POST/JSON-only and capped at 8 KiB.
It now requires exact `schemaVersion: 3`; schema v2 is rejected because item
identity changed.

`automatic` combines current bounded learning sources, active card Signals and
confirmed-profile content reasons. `search_workset` accepts 1..200 exact card
IDs and preserves first-seen order.

Triage v3 items carry the same four display fields as Search v2 and no
`primaryText`. Available cards copy the Search-owned projection. Missing or
malformed resolver rows use explicit unavailable identity. Legacy
`attention.frontPreview` is not a fallback.

The response retains typed source status, content-check status, counts,
truncation, priority, reasons, evidence, state and exact Search inspect identity.
It contains no full preview/media, raw revlog, note values, arbitrary query,
exception, token or runtime path.

Full contract: [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md).

## Inspection Profiles API

`POST /api/inspection-profiles/query`, `/validate` and `/update` use the current
token, strict JSON and 64 KiB cap. Query returns bounded note-type structures,
fingerprints, lifecycle, stored profile and non-authoritative suggestion.
Validation is read-only; update performs explicit local profile-store changes
with optimistic revision/fingerprint checks.

Only confirmed/current profiles create content reasons. Suggested, disabled,
needs-review, missing/future/corrupt/unavailable states fail closed.

Full contract: [`inspection-profiles-v1.md`](inspection-profiles-v1.md).

## Entity actions API

`POST /api/entities/cards/actions` and `/api/entities/notes/actions` require token,
POST, JSON and an 8 KiB cap.

Card allowlist:

```text
suspend | unsuspend | set_flag | clear_flag | bury | unbury | move_to_deck
```

Note allowlist:

```text
add_tags | remove_tags
```

Batches contain 1..200 exact decimal IDs. Stale IDs reject the full batch.
Mutations use official Anki operation wrappers and one native undo step. Generic
method invocation, SQL and arbitrary commands are prohibited.

Full contract: [`search-v1-and-safe-actions.md`](search-v1-and-safe-actions.md).

## Settings and profile APIs

`GET/POST /api/dashboard/settings` exposes normalized public settings and accepts
only allowlisted partial patches. Unknown/internal fields fail with
`invalid_settings`.

`GET/POST /api/profile` exposes public profile data. Writable fields remain
bounded (`customStudyStartedOn`, `deckOverviewSort`); computed identity and
metrics are not writable.

## Statistics and FSRS

`POST /api/statistics/query` accepts typed scope/period/granularity/comparison
only. `POST /api/statistics/fsrs/query` accepts the documented read-only FSRS
operations. Neither endpoint accepts arbitrary search/SQL or publishes raw
revlog/card/note rows.

## Notification and telemetry boundaries

Notification endpoints use schema v1 bounded lists/preferences and local
notification IDs. Telemetry endpoints accept only opt-in bounded technical
event contracts. Collection content, field names/values, Search queries,
card/note/deck IDs, compact display text, media filenames and token-bearing URLs
are excluded from remote telemetry.

## Payload source of truth

Backend report builder:

```text
anki_study_report/dashboard_payload.py
```

Frontend report type:

```text
web-dashboard/src/types/report.ts
```

Stable report sections include:

```text
metadata
summary
kpis
answerDistribution
activity
comparison
decks
attentionCards
attentionCardsStatus
noteTypeCatalog
forecast
fsrs
recommendations
cache
today
profile
activityHub
deckHub
statisticsHub
```

`today`, `profile`, `activityHub`, `deckHub` and `statisticsHub` remain their
specialized dashboard slices. Canonical Cards reads `/api/triage/query`, not
legacy `attentionCards`. Legacy `attentionCards` remains a report compatibility
surface for other consumers.

## Preview and media

Search card inspect includes the existing sanitized `renderedPreview` alongside
compact identity. Compact identity and full preview are different products.
Only the active card loads full preview data.

Media URLs use:

```text
/api/media?name=<validated-media-name>&token=<token>
```

Backend filename validation, sanitizer, Shadow DOM isolation and token checks
remain mandatory. Arbitrary `file:`, `javascript:`, iframe or template
JavaScript execution is prohibited.

## C1.5R verification state

```text
C1.5R.1 — Complete
C1.5R.2 — Complete
C1.5R.3 — Next, not started
C1.5R.4–R.7 — Not started
C1.6 — Blocked
```

R2 keeps Search v2 and Triage v3 unchanged. Owner-checkout focused frontend,
package validation and the canonical non-Docker gate passed for the implementation
tree committed as `edad09e8ffae443b94e192b266084abb66c37adf`. R3 is now Next, not started.

## C1.5R.3 preview semantics

See [`card-preview-semantics.md`](card-preview-semantics.md). Full preview uses reviewer/native front and answer; Inspector shows front, expanded dialog shows answer, and compact identity remains unchanged.

## C1.5R.4 independent candidate sources

See `docs/triage-candidate-sources-v4.md`. Triage schema v4 separates bounded period learning candidates from bounded current-content candidates and keeps R5 UI work deferred.
