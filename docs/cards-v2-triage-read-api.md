# Cards v2 canonical triage read API

## Status

**Schema:** `3`

**Endpoint:** `POST /api/triage/query`

**Stage:** C1.5R.1 identity correction Complete; C1.5R.2 formatter integration pending canonical verification

**UI:** current `#/cards` consumes automatic Triage v3 with a bounded 100-item
queue. The table/split presentation remains product-rejected historical C1.5 UI
and is not accepted by this schema change.

Triage v3 is read-only. It composes bounded learning sources, exact Search
worksets and confirmed Inspection Profiles. Search inspect remains the active
card preview source. C1.5R.1 established compact identity and schema v3. C1.5R.2 optionally
formats the same Search-owned identity without changing Triage v3. Neither stage
redesigns candidate sources, preview sides, workspace UI or actions.

## Transport and request v3

- loopback `127.0.0.1` server;
- current dashboard token required;
- `POST application/json`, 8 KiB cap;
- exact keys;
- positive signed-64-bit decimal IDs;
- serialized collection reads through `QueryOp`;
- no query, SQL, content, HTML or action input.

Automatic:

```json
{
  "schemaVersion": 3,
  "dataset": "automatic",
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": []
  },
  "limit": 100
}
```

Search workset:

```json
{
  "schemaVersion": 3,
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

Timestamps are non-negative safe-integer milliseconds with end greater than
start. `deckIds` are 0..200. Automatic limit is 1..100. Search workset IDs are
1..200 and preserve first-seen order after deduplication.

Schema v2 is rejected; it is not a silent alias because item identity changed.

## Response v3

The response keeps the v2 dataset/status/count/source/content-check structure
and uses `schemaVersion: 3`:

```json
{
  "schemaVersion": 3,
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
    },
    "profileChecks": {
      "status": "empty",
      "itemCount": 0,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    }
  },
  "contentChecks": {
    "status": "no_confirmed_profiles",
    "confirmedProfileCount": 0,
    "needsReviewProfileCount": 0,
    "disabledProfileCount": 0,
    "suggestedProfileCount": 0,
    "evaluatedNoteCount": 0,
    "failedCheckCount": 0,
    "skippedCount": 0,
    "truncated": false,
    "errorCode": null
  },
  "items": []
}
```

Response status is `available | partial | unavailable`. Source status is
`available | empty | partial | unavailable | error`. Empty means successful
source with no items. Counts and truncation remain exact.

## Item model v3

Each item is anchored to `card:<cardId>` and contains availability, exact
card/note/deck/note-type/template identity, categorical priority, reasons,
sources, card state, Search inspect identity and the canonical display fragment:

```json
{
  "displayText": "【に】（する）",
  "displaySource": "reviewer_front",
  "displayStatus": "available",
  "displayTruncated": false
}
```

`primaryText` is removed from Triage items. The strict frontend parser rejects
that alias and any other unknown key.

For available cards, Triage copies the exact Search v2 card-row display identity.
It does not re-render or re-extract text. For missing exact card IDs it emits:

```json
{
  "displayText": "",
  "displaySource": "none",
  "displayStatus": "unavailable",
  "displayTruncated": false
}
```

Legacy attention `frontPreview` is not a fallback. A malformed resolver identity
also fails closed to the explicit unavailable state.

## Display parity

For one exact card and response generation:

```text
Search card row
Search card Inspector heading
Triage item
Cards queue item
Cards Inspector heading
```

all consume the same backend projection. Queue rows do not load full preview
HTML or media. Only the active card uses Search inspect for the sanitized preview.

## Reasons and sources

Reason schema, source aggregation and ordering remain unchanged from v2.
Learning codes are:

```text
learning.leech
learning.repeated_again
learning.low_pass_rate
learning.slow_answer
```

Confirmed-profile content codes are:

```text
content.required_text_missing
content.audio_missing
content.image_missing
content.text_too_short
content.required_group_missing
```

Learning identity merges canonical attention and Signal evidence. Content
identity remains `profile:<profileId>:check:<checkId>`. Evidence stays bounded
and contains no raw note value, HTML, filename, template source, path, token or
exception.

Automatic order remains:

```text
priority → canonical reason order → evidence recency → card ID
```

Search workset preserves explicit first-seen order. Neutral workset items do not
receive invented reasons or priority.

## Candidate boundary

C1.5R.1 intentionally preserves the existing candidate-source behavior.
Period-independent current-content candidates belong to C1.5R.4 and are not
implemented here.

## Parser and compatibility

The TypeScript v3 parser requires exact top-level/item/nested keys and validates:

- schema v3 only;
- ID/count/finite-number bounds;
- reason/source/card-state enums;
- display text length up to 240;
- coherent display status/source/text/truncation;
- unavailable identity for missing items;
- absence of `primaryText` and future keys.

Search metadata v1, Search query/inspect v2, Safe Actions, Signals,
Notifications, token behavior and preview isolation remain separate contracts.

## Verification

Focused backend, HTTP, parser, hook and Cards tests are present but have not been
executed in the GitHub connector environment. C1.5R.1 remains **Implemented,
focused verification pending**. Fast CI, Docker and real-Anki E2E are outside
this stage.

## C1.5R.4 independent candidate sources

See `docs/triage-candidate-sources-v4.md`. Triage schema v4 separates bounded period learning candidates from bounded current-content candidates and keeps R5 UI work deferred.
