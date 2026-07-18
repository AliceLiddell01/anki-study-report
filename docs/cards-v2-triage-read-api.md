# Cards v2 canonical triage read API

## Status

**Schema:** `1`

**Endpoint:** `POST /api/triage/query`

**Stage:** C1.2 additive read foundation; pre-1.0 until C2 contract freeze

**UI:** `#/cards` still uses legacy `attentionCards`; this API is not wired to CardsPage in C1.2

The endpoint composes existing bounded card issues, active card-level Signals
and exact Search workset IDs into one deterministic read projection. It does
not persist triage items, execute actions, render full previews, implement
Inspection Profiles or introduce another Search grammar.

## Transport and security

- loopback dashboard server only (`127.0.0.1`);
- current dashboard token is required through the existing token mechanism;
- POST with `Content-Type: application/json` only;
- existing 8 KiB JSON body cap;
- card/deck IDs remain in the body, never in the route/query string;
- collection reads run through the existing serialized Anki `QueryOp` bridge;
- generic client errors contain no exception, token, local path or raw query;
- response contains no full card fields, HTML, media lists, revlog rows or token-bearing URLs.

## Request v1

Automatic queue:

```json
{
  "schemaVersion": 1,
  "dataset": "automatic",
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": []
  },
  "limit": 100
}
```

Exact Search workset:

```json
{
  "schemaVersion": 1,
  "dataset": "search_workset",
  "cardIds": ["123", "456"],
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": ["10"]
  },
  "limit": 200
}
```

All top-level and nested keys are exact. `schemaVersion`, `dataset`, `scope`
and `limit` are required. `cardIds` is required only for `search_workset` and
is rejected for `automatic`.

### Validation and bounds

| Field | Contract |
| --- | --- |
| `schemaVersion` | exactly integer `1` |
| `dataset` | `automatic \| search_workset` |
| timestamps | explicit non-negative safe integer milliseconds; `periodEndMs > periodStartMs` |
| `deckIds` | `0..200` positive decimal signed-64-bit strings; duplicates normalize in first-seen order |
| automatic `limit` | `1..100` |
| `cardIds` | `1..200` positive decimal signed-64-bit strings; duplicates normalize in first-seen order |
| Search workset `limit` | `1..200` |

There is no implicit all-time default. An explicit `periodStartMs: 0` remains
valid because the caller supplied both bounds. The request accepts no query,
SQL, sort expression, HTML, card content or action name.

## Response v1

```json
{
  "schemaVersion": 1,
  "dataset": "automatic",
  "status": "available",
  "generatedAtMs": 1721000000000,
  "totalCount": 1,
  "returnedCount": 1,
  "limit": 100,
  "truncated": false,
  "sourceStatus": {
    "attention": {
      "status": "available",
      "itemCount": 1,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    },
    "signals": {
      "status": "empty",
      "itemCount": 0,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    },
    "searchResolver": {
      "status": "available",
      "itemCount": 1,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    }
  },
  "contentChecks": {"status": "profiles_not_available"},
  "items": []
}
```

Response `status` is `available | partial | unavailable`. Source status is
`available | empty | unavailable | error`. `empty` is a successful read with
no items; it is not an error or proof that an unavailable source has resolved.

`totalCount` is the canonical count before the requested response limit;
`returnedCount == items.length`; `truncated` is true exactly when
`totalCount > returnedCount`.

## Item model

Every item has exact fields:

```text
itemId                 deterministic card:<cardId>
availability           available | missing
cardId                 decimal string
noteId                 decimal string | null
deck                    { deckId: string|null, name: plain bounded text }
noteType                { noteTypeId: string|null, name: plain bounded text }
template                { ordinal: integer|null, name: plain bounded text }
primaryText             plain text, max 240 characters
priority                high | medium | low | null
primaryReasonCode       canonical reason code | null
reasons                 max 4 canonical reasons
sources                 attention | signals | search_workset
cardState               bounded state/suspended/buried/flag summary
inspect                  existing Search inspect identity or null
```

`availability: missing` represents an exact stale/deleted workset card or an
active Signal whose collection entity no longer resolves. It keeps the stable
card anchor but has `inspect: null` and nullable identity/state fields.

Search-only items with no independently detected canonical problem have:

```json
{
  "priority": null,
  "primaryReasonCode": null,
  "reasons": [],
  "sources": ["search_workset"]
}
```

No manual problem reason is invented.

## Reason model

```text
code
family                 learning | content | system | manual
scope                  card | note
priority               high | medium | low
sources                bounded provenance set
evidence               max 4 discriminated objects
detectedAtMs           timestamp | null
```

C1.2 emits only these confirmed card-level learning codes:

```text
learning.leech
learning.repeated_again
learning.low_pass_rate
learning.slow_answer
```

The wider family/scope types reserve explicit future content/note reasons, but
the schema-v1 parser fails closed until their codes and evidence are added by a
later contract change.

## Structured evidence

| `kind` | Exact fields |
| --- | --- |
| `leech_state` | `lapses` |
| `review_counts` | `againCount`, `periodStartMs`, `periodEndMs` |
| `pass_rate` | `passRate` in `0..1`, `periodStartMs`, `periodEndMs` |
| `answer_time` | finite non-negative `averageAnswerSeconds`, period bounds |
| `signal_evidence` | `severity`, `againCount`, `reviewCount`, `windowDays`, `detectorVersion` |

Evidence is data, not localized prose. Non-finite or malformed evidence is
skipped without crashing valid reasons/items. Exact duplicate evidence is
deduplicated. No evidence contains content, full revlog rows, query text or
exception details.

## Source mapping and precedence

### Attention collector

The existing `collect_attention_cards_with_status()` query path remains the
source. The triage adapter asks it not to build `renderedPreview`, then maps only:

| legacy issue | canonical reason |
| --- | --- |
| `leech` | `learning.leech` |
| `repeated again` / `repeated_again` | `learning.repeated_again` |
| `low pass rate` / `low_pass_rate` | `learning.low_pass_rate` |
| `slow answer` / `slow_answer` | `learning.slow_answer` |

Legacy heuristic `missing_audio`, `missing_example`, `missing_image`,
`missing_meaning` and `missing_part_of_speech` are deliberately suppressed in
this projection. Legacy `attentionCards` and Cards v1 are unchanged.

### Signals

`NotificationStore.list_active_card_signals()` reads only active card-level
Signals, bounded to 50. C1.2 maps only `card.repeated_again`; resolved Signals
and notification history are not sources. Unknown codes fail closed and
increment the bounded source `skippedCount`.

### Search resolver

Exact IDs resolve through the existing Search `project_card_row()` projection.
It supplies plain primary text, identities, template and card-state summary.
No `/api/search/inspect` duplicate or query grammar is introduced.

### Overlap precedence

Reason identity is `code + scope`. When attention and Signal both report
repeated Again:

1. one reason remains;
2. both provenance values remain;
3. the highest categorical priority wins;
4. Signal severity/freshness and structured evidence are preferred first;
5. non-duplicate attention evidence remains available.

Search identity projection supplies entity/state fields; attention is the
fallback for bounded text/note/deck names when resolution is missing.

## Priority mapping

| Reason/source | Priority |
| --- | --- |
| `learning.leech` | `high` |
| attention repeated Again | `medium` |
| Signal repeated Again, `warning` | `medium` |
| Signal repeated Again, `critical` | `high` |
| `learning.low_pass_rate` | `medium` |
| `learning.slow_answer` | `low` |

This is a reason-specific mapping, not a new score. `riskScore` is absent from
the API, frontend type and canonical sort. The legacy score remains only in
the untouched Cards v1 payload until its later migration.

## Aggregation and ordering

Item key is `cardId`. Duplicate source rows merge. Reasons sort by:

```text
priority → canonical reason order → evidence recency → reason code
```

Automatic items sort by:

```text
priority → canonical reason order → evidence recency → numeric card ID
```

The canonical reason order is leech, repeated Again, low pass rate, slow
answer. Identical shuffled inputs produce identical output. Search worksets
preserve first-seen explicit ID order and are not re-sorted by problem priority.

## Partial and unavailable semantics

| Situation | Result |
| --- | --- |
| all required reads succeed, including legitimate empty sources | `available` |
| one automatic source or identity enrichment fails | `partial` |
| both automatic canonical sources fail | automatic `unavailable` |
| Search resolver fails | Search workset `unavailable` |
| Search resolver succeeds but canonical enrichment fails | Search workset `partial` |
| one exact card is stale/deleted | response remains readable; item is `missing` |
| body/schema/scope invalid | HTTP 400 `invalid_triage_request` |
| QueryOp timeout | HTTP 504 `triage_timeout` |
| unexpected operation failure | HTTP 503 generic `triage_failed` |

Source errors never become an empty-success resolution. Error codes are short,
bounded and machine-readable; raw exception text is not returned.

## Performance and boundedness

- automatic attention source: 100 rows;
- active card Signals: 50 rows;
- Search workset: 200 exact IDs;
- response limit: 100 automatic / 200 workset;
- reasons per item: 4;
- evidence objects per reason: 4;
- primary text: 240 characters;
- no full preview/media reads in the triage attention adapter;
- no full revlog history or unbounded query/filter/sort surface;
- one serialized QueryOp owns collection access for a request.

The current Search projector resolves each bounded exact card through the same
canonical row helper used by Search. A future measured optimization may add a
batch identity loader, but must preserve this public projection and must not
duplicate Search semantics.

## Compatibility

C1.2 is additive. It does not change:

- `/api/report`, `attentionCards` or `attentionCardsStatus`;
- current CardsPage layout, display modes or preview behavior;
- Search query/inspect routes;
- Safe Actions;
- Signal lifecycle/persistence;
- Notification Center/handoff;
- sanitizer, media validation or Shadow DOM isolation.

## Deferred work

- C1.3: confirmed Inspection Profile contract/runtime and authoritative content reasons;
- C1.5: Cards workspace/Inspector UI migration to this API;
- C1.6: session Search/Notification handoff wiring;
- later C1 increments: actions/recheck/bulk partial outcomes and measured queue presentation.
