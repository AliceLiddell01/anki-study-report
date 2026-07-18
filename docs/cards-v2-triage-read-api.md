# Cards v2 canonical triage read API

## Status

**Schema:** `2`
**Endpoint:** `POST /api/triage/query`
**Stage:** C1.3 additive read/runtime foundation; pre-1.0 until C2 freeze
**UI:** current `#/cards` still consumes legacy `attentionCards`

V2 composes bounded learning sources, exact Search worksets and confirmed
[Inspection Profiles](inspection-profiles-v1.md). It is read-only and does not
persist triage items, run actions, render full previews, add Search grammar or
change the current CardsPage.

## Transport and request v2

- loopback `127.0.0.1` dashboard server;
- current dashboard token required;
- `POST application/json`, 8 KiB body cap;
- IDs are positive signed-64-bit decimal strings in JSON body;
- collection reads use serialized `QueryOp`;
- generic failures contain no exception, path, token, query or content.

Automatic:

```json
{
  "schemaVersion": 2,
  "dataset": "automatic",
  "scope": {"periodStartMs": 1700000000000, "periodEndMs": 1700604800000, "deckIds": []},
  "limit": 100
}
```

Search workset:

```json
{
  "schemaVersion": 2,
  "dataset": "search_workset",
  "cardIds": ["123", "456"],
  "scope": {"periodStartMs": 1700000000000, "periodEndMs": 1700604800000, "deckIds": ["10"]},
  "limit": 200
}
```

All keys are exact. Timestamps are explicit non-negative safe-integer
milliseconds with end greater than start. `deckIds` are 0..200. Automatic
limit is 1..100. Search `cardIds` are 1..200 and limit is 1..200. Duplicate IDs
normalize in first-seen order. The request accepts no query, SQL, sort,
content, HTML or action.

V1 is not accepted as a silent alias because v2 changes reason identity,
source status and content evidence.

## Response

```json
{
  "schemaVersion": 2,
  "dataset": "automatic",
  "status": "available",
  "generatedAtMs": 1721000000000,
  "totalCount": 1,
  "returnedCount": 1,
  "limit": 100,
  "truncated": false,
  "sourceStatus": {
    "attention": {"status": "available", "itemCount": 1, "skippedCount": 0, "truncated": false, "errorCode": null},
    "signals": {"status": "empty", "itemCount": 0, "skippedCount": 0, "truncated": false, "errorCode": null},
    "searchResolver": {"status": "available", "itemCount": 1, "skippedCount": 0, "truncated": false, "errorCode": null},
    "profileChecks": {"status": "available", "itemCount": 1, "skippedCount": 0, "truncated": false, "errorCode": null}
  },
  "contentChecks": {
    "status": "available",
    "confirmedProfileCount": 1,
    "needsReviewProfileCount": 0,
    "disabledProfileCount": 0,
    "suggestedProfileCount": 0,
    "evaluatedNoteCount": 1,
    "failedCheckCount": 1,
    "skippedCount": 0,
    "truncated": false,
    "errorCode": null
  },
  "items": []
}
```

Response status is `available | partial | unavailable`. Source status is
`available | empty | partial | unavailable | error`. Empty means a successful
source with no items, not resolution. `totalCount` is before response limit;
`returnedCount == items.length`; truncation is exact.

Aggregate content status is `available | no_confirmed_profiles |
profiles_need_review | disabled | partial | unavailable`. No confirmed profile
is a valid empty configuration. An unavailable profile store/model source
fails closed.

## Item model

Each item is anchored to `card:<cardId>` and contains availability, card/note/
deck/note-type/template identity, bounded plain `primaryText`, categorical
priority, primary reason, at most four reasons, sources, card state and an
existing Search inspect identity. Missing exact IDs keep the card anchor but
have nullable resolved fields and no inspect action.

Search workset items always preserve explicit first-seen order and include
`search_workset` in sources. A selected card with no independently detected
problem remains neutral (`priority: null`, no reasons); no manual reason is
invented.

## Reasons and identity

Every reason has:

```text
reasonId
code
family                 learning | content
scope                  card | note
priority               high | medium | low
sources
evidence               max 4 discriminated objects
detectedAtMs           timestamp | null
```

Learning identity is stable per canonical learning code, allowing attention
and Signal evidence to merge. Content identity is
`profile:<profileId>:check:<checkId>`, so checks of the same kind remain
separate.

Learning codes:

```text
learning.leech
learning.repeated_again
learning.low_pass_rate
learning.slow_answer
```

Confirmed-profile content codes:

```text
content.required_text_missing
content.audio_missing
content.image_missing
content.text_too_short
content.required_group_missing
```

Evidence kinds `leech_state`, `review_counts`, `pass_rate`, `answer_time` and
`signal_evidence` remain from v1. V2 adds `profile_check`: profile/check kind,
roles, exact field identities, expected condition, optional safe length/
marker result, profile revision, fingerprint, affected sibling count and
template scope. It contains no note value, HTML, filename, template source,
path, token or exception.

## Sources and candidate bounds

### Attention

Automatic triage uses one bounded shared revlog/card/note query (100 results
plus truncation sentinel), under the explicit period/deck scope. The legacy
learning projector consumes the same rows without full rendered previews.
Only `leech`, repeated Again, low pass rate and slow answer become learning
reasons.

Legacy heuristic `missing_*` labels remain in legacy `attentionCards` and are
ignored by canonical triage. A bounded candidate may still receive a
confirmed-profile content reason even when it has no learning reason.

### Signals

At most 50 active card Signals are read. Only `card.repeated_again` maps in v2.
Unknown/malformed rows fail closed and increment skipped count. Notification
history and resolved Signals are not sources.

### Search resolver

Exact target IDs reuse the existing bounded Search card row projection. Search
worksets separately batch-load at most 200 exact card/note field rows for
profile evaluation. They do not create a new query grammar or unselected rows.

### Profile checks

Only `confirmed` profiles with current fingerprint and exact refs evaluate.
Suggested, disabled, needs-review, missing/future/corrupt/unavailable states
emit no authoritative content reason. Learning reasons remain independent.

## Siblings and ordering

A content failure is note-scoped. Multiple candidate siblings produce one
content reason on a deterministic representative:

- automatic: smallest applicable candidate card ID;
- Search workset: first explicitly selected applicable sibling.

Evidence exposes only total affected sibling count. Independent card-level
learning reasons on other siblings remain on those cards. Search order is not
re-sorted. Automatic order remains:

```text
priority → canonical reason order → evidence recency → card ID
```

Reason ordering is deterministic; no riskScore or frontend inference is used.

## Compatibility and verification

Legacy `attentionCards`, existing CardsPage, Search, Safe Actions, Signals,
Notifications, token behavior and preview isolation remain unchanged. The
strict TypeScript v2 parser rejects unknown schemas/enums/evidence/check kinds,
non-finite numbers, invalid IDs, extra fields and count drift.

Focused verification covers backend projection/runtime, sibling dedupe,
profile lifecycle/content reasons, HTTP boundaries and TypeScript parser/
client. The risk-matched `standard/cards` real-Anki run confirms live model/
field reads, Japanese versus Programming profile behavior, fail-closed
fingerprint drift and same-profile restart persistence.
