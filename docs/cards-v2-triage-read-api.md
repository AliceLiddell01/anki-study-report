# Cards v2 canonical Triage API

## Current schemas

```text
POST /api/triage/query   schemaVersion 4
POST /api/triage/recheck schemaVersion 1
```

Both endpoints are loopback-only, token-protected, `POST application/json`,
capped at 8 KiB and serialized through Anki `QueryOp`. Requests accept only
strict bounded IDs, scope and schema fields; they accept no query language,
SQL, HTML, note values or arbitrary action input.

## Query v4

Automatic queue request:

```json
{
  "schemaVersion": 4,
  "dataset": "automatic",
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": []
  },
  "limit": 100,
  "contentCursor": null
}
```

Search workset request:

```json
{
  "schemaVersion": 4,
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

Automatic results combine independent bounded period-learning, current-content,
active Signal and Search identity sources. Current-content pagination is
explicit and bounded; the client never loops cursors automatically. Search
worksets preserve explicit first-seen card order.

The response exposes typed aggregate/source/content-check status, counts,
cursor coherence and up to four stable reasons per item. Queue identity is the
same Search-owned compact projection used by Search rows and Inspectors. Full
preview HTML/media remains outside Triage; only the active card uses Search
inspect.

Reason IDs are stable canonical strings:

```text
learning:<code>
profile:<profileId>:check:<checkId>
```

Evidence is bounded and excludes raw note values, HTML, filenames, template
source, filesystem paths, tokens and exceptions.

## Exact-card recheck v1

Request:

```json
{
  "schemaVersion": 1,
  "cardId": "123",
  "expectedNoteId": "456",
  "reasonIds": ["learning:learning.repeated_again"],
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": []
  }
}
```

`reasonIds` contains 1..4 unique bounded canonical IDs from the current item.
It lets the server fail closed when a previously authoritative profile reason
can no longer be evaluated. It is not a list of reasons to suppress.

Abbreviated response shape (the wire response contains the complete strict
`contentChecks` object and complete item):

```json
{
  "schemaVersion": 1,
  "cardId": "123",
  "expectedNoteId": "456",
  "status": "available",
  "entityStatus": "available",
  "generatedAtMs": 1721000000000,
  "sourceStatus": {
    "learningCandidates": { "status": "available", "itemCount": 1, "skippedCount": 0, "truncated": false, "errorCode": null },
    "signals": { "status": "empty", "itemCount": 0, "skippedCount": 0, "truncated": false, "errorCode": null },
    "searchResolver": { "status": "available", "itemCount": 1, "skippedCount": 0, "truncated": false, "errorCode": null },
    "profileChecks": { "status": "empty", "itemCount": 0, "skippedCount": 0, "truncated": false, "errorCode": null }
  },
  "contentChecks": { "status": "no_confirmed_profiles" },
  "item": {}
}
```

The real response contains the complete strict `contentChecks` counters and
either the complete Triage item or `null`. Entity status is one of:

```text
available | missing | changed | unavailable
```

Top-level status is `available | partial | unavailable`. Resolution is allowed
only when entity status and all required source coverage are authoritative and
the returned available item has zero reasons. Partial/unavailable/error source
status, profile authority change, identity mismatch or collection failure cannot
produce a resolved result.

## Parser and HTTP behavior

The TypeScript parsers require exact top-level and nested keys, finite bounded
numbers, decimal ID strings, enum values, coherent item identity and no future
fields. Query v4 automatic items require at least one reason. Recheck v1 alone
may return an available exact item with zero reasons as authoritative proof.

`GET` receives 405. Missing/invalid tokens receive 403. Wrong content type gets
415. Invalid JSON/schema/fields get 400. Runtime unavailable/failure gets 503;
timeout gets 504. Public errors are generic and never expose collection values,
queries, paths or exceptions.

## UI contract

The C1.6 lifecycle and reason reconciliation rules are defined in
[`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md). The automatic
100-item queue cap is presentation boundedness, never proof that an issue was
resolved.
