# Канонический API Cards v2 Triage

## Текущие schemas

```text
POST /api/triage/query    schemaVersion 4
POST /api/triage/recheck  schemaVersion 1
```

Оба endpoints:

- доступны только на loopback;
- защищены dashboard token;
- принимают `POST application/json`;
- ограничены body 8 KiB;
- сериализованы через Anki `QueryOp`.

Requests принимают только strict bounded IDs, scope и schema fields. Query language, SQL, HTML, значения note и arbitrary action input запрещены.

## Query v4

### Automatic queue

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

### Search workset

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

Automatic result объединяет независимые bounded sources:

- period-bound learning candidates;
- current-content candidates;
- active Signals;
- Search identity.

Pagination current-content является явной и bounded. Client никогда не запускает автоматический cursor loop. Search workset сохраняет explicit first-seen order карточек.

Response публикует:

- typed aggregate/source/content-check status;
- counts;
- cursor coherence;
- до четырёх стабильных reasons на item.

Queue identity использует ту же Search-owned compact projection, что Search rows и Inspectors. Full preview HTML/media не входит в Triage; Search inspect вызывается только для active card.

Стабильные reason IDs:

```text
learning:<code>
profile:<profileId>:check:<checkId>
```

Evidence bounded и исключает raw note values, HTML, filenames, template source, filesystem paths, tokens и exceptions.

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

`reasonIds` содержит `1..4` уникальных bounded canonical IDs текущего item. Это позволяет server работать fail closed, когда прежний authoritative profile reason больше нельзя проверить. Это не список reasons, которые нужно скрыть.

Сокращённая shape response:

```json
{
  "schemaVersion": 1,
  "cardId": "123",
  "expectedNoteId": "456",
  "status": "available",
  "entityStatus": "available",
  "generatedAtMs": 1721000000000,
  "sourceStatus": {
    "learningCandidates": {
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
    "status": "no_confirmed_profiles"
  },
  "item": {}
}
```

Реальный response содержит полный strict `contentChecks` object и либо полный Triage item, либо `null`.

`entityStatus`:

```text
available | missing | changed | unavailable
```

Top-level `status`:

```text
available | partial | unavailable
```

Resolution допустим только тогда, когда:

- entity status authoritative;
- все required sources authoritative;
- возвращённый available item содержит ноль reasons.

Partial/unavailable/error source status, изменение authority profile, mismatch identity и collection failure не могут дать resolved result.

## Parser и HTTP behavior

TypeScript parsers требуют:

- exact top-level и nested keys;
- finite bounded numbers;
- decimal ID strings;
- допустимые enum values;
- coherent item identity;
- отсутствие future fields.

Automatic items Query v4 должны иметь хотя бы один reason. Только Recheck v1 может вернуть available exact item с нулём reasons как authoritative proof.

HTTP behavior:

```text
GET                                      → 405
missing/invalid token                    → 403
wrong content type                       → 415
invalid JSON/schema/fields               → 400
runtime unavailable/failure              → 503
timeout                                  → 504
```

Public errors остаются generic и не раскрывают collection values, queries, paths или exceptions.

## UI contract

Lifecycle C1.6 и reconciliation reasons описаны в:

- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md).

Automatic queue cap 100 — только bounded presentation. Он никогда не доказывает, что issue resolved.