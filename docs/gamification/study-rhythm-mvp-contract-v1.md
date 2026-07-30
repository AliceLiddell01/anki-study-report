# Study Rhythm MVP contract v1

**Status:** `G5.2 CONTRACT CANDIDATE / REVIEW PENDING`

**Implementation status:** contract only. Runtime store, service, endpoint handlers,
dashboard payload integration, frontend route and UI are **NOT IMPLEMENTED** by G5.2.
G5.3 is **NOT STARTED**.

This document is the normative human-readable contract for the minimal Study
Rhythm vertical slice. The four JSON Schemas in [`schemas/`](../../schemas/) are
the machine-readable contract. Where prose and schema differ, the stricter
interpretation applies and the mismatch blocks review.

## 1. Product boundary

Study Rhythm answers one bounded question: whether the user has accumulated a
chosen number of active study days in the current Monday–Sunday week while
allowing explicitly planned rest days to remain neutral.

In scope for v1:

- opt-in Study Rhythm settings;
- a weekly target from one through seven active days;
- planned rest weekdays;
- deterministic current-day and current-week progress;
- up to four fully covered completed weeks as factual history;
- the existing Profile streak as clearly labelled, non-rest-aware context;
- bounded explanations, limitations and typed errors.

Explicitly out of scope:

- XP, levels, skill mastery, achievements, quests, currencies, rewards,
  leaderboards or social competition;
- retrospective scoring of old weeks against the current plan;
- a new collection scan, direct revlog access or a second aggregation path;
- selected-deck Study Rhythm;
- notifications, rewards or adaptive target changes;
- runtime/API/UI implementation in G5.2.

No unresolved product decision remains in this v1 candidate.

## 2. Versions, time and source authority

| Contract item | Frozen value |
| --- | --- |
| settings schema | `1` |
| mutation request schema | `1` |
| model schema | `1` |
| error schema | `1` |
| calculation version | `study-rhythm-v1` |
| ActivityHub input | `schemaVersion: 1` |
| Profile input | current `ProfileModel` |
| calendar date | `YYYY-MM-DD` |
| generated timestamp | UTC RFC 3339 ending in `Z` |
| weekday | ISO `1..7`, Monday through Sunday |
| week | Monday through Sunday |
| today | exactly `activityHub.today` |

Study Rhythm consumes the already-published report snapshot. It does not read
the Anki collection. A trustworthy activity source requires:

```text
activityHub.schemaVersion == 1
activityHub.scope.kind == "all"
```

The public coverage value for that source is `scope: "all_collection"`. If the
ActivityHub is missing, has an unsupported schema, or has selected-deck scope,
Study Rhythm is unavailable and records the corresponding limitation. It never
falls back to raw revlog or another live scan.

ActivityHub day meanings remain authoritative:

| ActivityHub availability | Study Rhythm activity | Meaning |
| --- | --- | --- |
| `active` | `active` | known day with at least one review |
| `inactive` | `inactive` | known day with no reviews |
| `unavailable` | `unavailable` | activity cannot be classified |
| future date | `future` | not elapsed and not evaluated |

## 3. Persisted settings and recovery

The persisted document is
[`gamification-settings-v1.schema.json`](../../schemas/gamification-settings-v1.schema.json).
Every object is closed; unknown fields are invalid.

| Field | Type | Rule |
| --- | --- | --- |
| `schemaVersion` | integer | exactly `1` |
| `revision` | safe integer | `0..9007199254740991` |
| `enabled` | boolean | opt-in state |
| `weeklyTargetDays` | integer | `1..7` |
| `plannedRestWeekdays` | unique ISO weekday array | stored ascending |
| `feedbackEnabled` | boolean | reserved minimal feedback toggle |

The plan is feasible only when:

```text
weeklyTargetDays + count(plannedRestWeekdays) <= 7
```

Defaults are product defaults, not an owner selection:

<!-- contract-example:settings-default-disabled.json -->
```json
{
  "schemaVersion": 1,
  "revision": 0,
  "enabled": false,
  "weeklyTargetDays": 1,
  "plannedRestWeekdays": [],
  "feedbackEnabled": true
}
```

Public settings add one non-persisted field:

| `source` | Meaning |
| --- | --- |
| `default` | no stored document; virtual defaults at revision `0` |
| `stored` | valid stored document |
| `recovered_default` | corrupt supported-version document was quarantined and defaults were recovered |

Recovery is fail-closed and deterministic:

- missing file: virtual defaults, revision `0`, source `default`;
- valid v1 file: normalized stored values, source `stored`;
- corrupt supported-version file: quarantine original, expose defaults at
  revision `0`, source `recovered_default`, add
  `settings_corrupt_recovered`;
- future schema version: preserve the document unchanged and fail with HTTP
  `503` / `gamification_store_unavailable`; do not quarantine or overwrite it.

## 4. Settings mutation contract

[`gamification-settings-request-v1.schema.json`](../../schemas/gamification-settings-request-v1.schema.json)
freezes the request for the future local, token-protected
`POST /api/gamification/settings`. The endpoint is **NOT IMPLEMENTED** in G5.2.

The request is a strict discriminated union:

```text
replace = schemaVersion + expectedRevision + operation + complete settings
reset   = schemaVersion + expectedRevision + operation
```

`replace` is a full replacement, never a patch. Arbitrary input weekday order
is accepted only when values are unique and the plan is feasible; successful
storage and public responses normalize weekdays ascending. Disabling uses
`replace` with `enabled: false`. `reset` is distinct and restores defaults.

<!-- contract-example:settings-replace-enabled.json -->
```json
{
  "schemaVersion": 1,
  "expectedRevision": 0,
  "operation": "replace",
  "settings": {
    "enabled": true,
    "weeklyTargetDays": 4,
    "plannedRestWeekdays": [
      6,
      7
    ],
    "feedbackEnabled": true
  }
}
```

Concurrency and atomicity:

- `expectedRevision` must equal the current public revision;
- success writes atomically and increments revision exactly once;
- revision conflict performs no write;
- validation, serialization, fsync or replacement failure leaves the previous
  document unchanged;
- reset success also increments exactly once from the matched revision.

## 5. Public model

[`gamification-model-v1.schema.json`](../../schemas/gamification-model-v1.schema.json)
requires exactly these top-level fields:

```text
schemaVersion
calculationVersion
generatedAt
availability
settings
coverage
today
week
historySummary
existingStreakContext
explanations
limitations
```

`availability` is `available`, `partial` or `unavailable`. When settings are
disabled, `today` and `week` are `null`; factual history and existing streak
context may still be available. When the ActivityHub source is unavailable,
`today` and `week` are also `null`.

### 5.1 Coverage

Coverage fields are:

| Field | Frozen rule |
| --- | --- |
| `source` | `activity_hub_v1` |
| `scope` | `all_collection` |
| `today` | ActivityHub today |
| `weekStart` / `weekEnd` | Monday / Sunday containing today |
| `availableFrom` | first trustworthy all-collection day or `null` |
| `status` | `full`, `partial` or `unavailable` |
| `knownElapsedDays` | known days from Monday through today |
| `unavailableElapsedDates` | ascending unavailable dates from Monday through today |

Elapsed means Monday through today inclusive. Coverage is:

- `full` when every elapsed day is known;
- `partial` when at least one elapsed day is known and at least one is
  unavailable;
- `unavailable` when no current-week elapsed day is trustworthy.

Unknown days are not converted to inactivity and are never called missed days.

### 5.2 Today

When enabled and derivable, `today` contains:

| Field | Values |
| --- | --- |
| `date` | coverage today |
| `isoWeekday` | `1..7` |
| `plan` | `open`, `rest` |
| `activity` | `active`, `inactive`, `unavailable` |
| `countsTowardTarget` | `true`, `false`, `null` |

Count mapping is exact: `active → true`, `inactive → false`,
`unavailable → null`. Activity on a planned rest day still counts. Inactivity
on a planned rest day remains neutral; it does not create a penalty.

### 5.3 Week and completion

An enabled derivable week contains exactly seven ordered day objects, Monday
through Sunday. Each day has:

```text
date, isoWeekday, relation, plan, activity, countsTowardTarget
```

`relation` is `past`, `today` or `future`; future days use
`activity: "future"` and `countsTowardTarget: null`.

Progress calculations are:

```text
completedDays = count(days where countsTowardTarget == true)
targetDays = settings.weeklyTargetDays
remainingDays = max(targetDays - completedDays, 0)
isLowerBound = any elapsed day has activity == unavailable
```

Known activity counts even on a rest day. `remainingOpenDays` is the ascending
list of current/future non-rest dates not already active. `completionState`
uses this decision order:

1. `complete` when `completedDays >= targetDays`;
2. otherwise `unknown` when coverage is partial or unavailable;
3. otherwise `possible` when remaining open opportunities are at least
   `remainingDays`;
4. otherwise `not_possible_without_plan_change`.

<!-- contract-example:model-active-on-rest-day.json -->
```json
{
  "schemaVersion": 1,
  "calculationVersion": "study-rhythm-v1",
  "generatedAt": "2026-07-31T12:00:00Z",
  "availability": "available",
  "settings": {
    "schemaVersion": 1,
    "revision": 6,
    "enabled": true,
    "weeklyTargetDays": 3,
    "plannedRestWeekdays": [
      5,
      7
    ],
    "feedbackEnabled": true,
    "source": "stored"
  },
  "coverage": {
    "source": "activity_hub_v1",
    "scope": "all_collection",
    "today": "2026-07-31",
    "weekStart": "2026-07-27",
    "weekEnd": "2026-08-02",
    "availableFrom": "2026-07-01",
    "status": "full",
    "knownElapsedDays": 5,
    "unavailableElapsedDates": []
  },
  "today": {
    "date": "2026-07-31",
    "isoWeekday": 5,
    "plan": "rest",
    "activity": "active",
    "countsTowardTarget": true
  },
  "week": {
    "weekStart": "2026-07-27",
    "weekEnd": "2026-08-02",
    "progress": {
      "completedDays": 3,
      "targetDays": 3,
      "remainingDays": 0,
      "isLowerBound": false
    },
    "remainingOpenDays": [
      "2026-08-01"
    ],
    "completionState": "complete",
    "days": [
      {
        "date": "2026-07-27",
        "isoWeekday": 1,
        "relation": "past",
        "plan": "open",
        "activity": "active",
        "countsTowardTarget": true
      },
      {
        "date": "2026-07-28",
        "isoWeekday": 2,
        "relation": "past",
        "plan": "open",
        "activity": "active",
        "countsTowardTarget": true
      },
      {
        "date": "2026-07-29",
        "isoWeekday": 3,
        "relation": "past",
        "plan": "open",
        "activity": "inactive",
        "countsTowardTarget": false
      },
      {
        "date": "2026-07-30",
        "isoWeekday": 4,
        "relation": "past",
        "plan": "open",
        "activity": "inactive",
        "countsTowardTarget": false
      },
      {
        "date": "2026-07-31",
        "isoWeekday": 5,
        "relation": "today",
        "plan": "rest",
        "activity": "active",
        "countsTowardTarget": true
      },
      {
        "date": "2026-08-01",
        "isoWeekday": 6,
        "relation": "future",
        "plan": "open",
        "activity": "future",
        "countsTowardTarget": null
      },
      {
        "date": "2026-08-02",
        "isoWeekday": 7,
        "relation": "future",
        "plan": "rest",
        "activity": "future",
        "countsTowardTarget": null
      }
    ]
  },
  "historySummary": {
    "limit": 4,
    "completedWeeks": [
      {
        "weekStart": "2026-07-20",
        "weekEnd": "2026-07-26",
        "activeDays": 4
      }
    ]
  },
  "existingStreakContext": {
    "available": true,
    "currentStreak": 1,
    "bestStreak": 14,
    "source": "profile_study_history",
    "restAware": false
  },
  "explanations": [
    "planned_rest_is_neutral",
    "activity_on_rest_day_counts",
    "existing_streak_is_not_rest_aware",
    "current_plan_is_not_applied_retroactively"
  ],
  "limitations": []
}
```

### 5.4 History and existing streak

`historySummary.limit` is exactly `4`. `completedWeeks` contains at most the
four newest fully covered completed Monday–Sunday weeks with only
`weekStart`, `weekEnd` and factual `activeDays`. The current target and rest
plan are not applied retroactively.

`existingStreakContext` uses current Profile `studyHistory.currentStreak` and
`bestStreak`:

```text
source = profile_study_history
restAware = false
```

When Profile is unavailable, both streak values are `null`, `available` is
`false`, and `profile_missing_for_streak_context` is present. Study Rhythm does
not rename or redefine the existing streak.

## 6. Explanation and limitation codes

Arrays are unique, bounded, deterministic and contain only codes relevant to
the returned model.

Explanation allowlist:

```text
planned_rest_is_neutral
activity_on_rest_day_counts
unavailable_days_are_not_missed
existing_streak_is_not_rest_aware
current_plan_is_not_applied_retroactively
```

Limitation allowlist:

```text
activity_hub_missing
activity_hub_schema_unsupported
activity_scope_not_all_collection
current_week_partial_coverage
profile_missing_for_streak_context
settings_corrupt_recovered
```

## 7. Error envelope and HTTP mapping

[`gamification-error-v1.schema.json`](../../schemas/gamification-error-v1.schema.json)
is a closed union.

| HTTP | `error` | Additional contract |
| --- | --- | --- |
| `400` | `invalid_gamification_request` | optional bounded `fieldErrors` |
| `403` | `forbidden` | no token or internal detail |
| `409` | `gamification_revision_conflict` | `currentRevision` and `currentSettings` required |
| `503` | `gamification_unavailable` | derivation/runtime source unavailable |
| `503` | `gamification_store_unavailable` | settings store or future schema unavailable |

`fieldErrors` keys are limited to:

```text
schemaVersion
expectedRevision
operation
enabled
weeklyTargetDays
plannedRestWeekdays
feedbackEnabled
```

<!-- contract-example:error-revision-conflict.json -->
```json
{
  "schemaVersion": 1,
  "ok": false,
  "error": "gamification_revision_conflict",
  "message": "Study Rhythm settings changed in another request.",
  "currentRevision": 4,
  "currentSettings": {
    "schemaVersion": 1,
    "revision": 4,
    "enabled": true,
    "weeklyTargetDays": 4,
    "plannedRestWeekdays": [
      6,
      7
    ],
    "feedbackEnabled": true,
    "source": "stored"
  }
}
```

<!-- contract-example:error-store-unavailable.json -->
```json
{
  "schemaVersion": 1,
  "ok": false,
  "error": "gamification_store_unavailable",
  "message": "Study Rhythm settings are temporarily unavailable."
}
```

Responses never expose filesystem paths, tracebacks, tokens, token-bearing
URLs, raw collection rows, raw revlog data or profile-private data.

## 8. Schema and language mapping

All schemas use JSON Schema Draft 2020-12, stable
`https://anki-study-report.local/schemas/...` identifiers,
`additionalProperties: false` at every payload object boundary, explicit
required fields, bounded arrays/strings/integers, strict enums and only local
`#/$defs/...` references. There are no extension bags, remote contract refs,
compatibility aliases or placeholders.

Exact value mapping:

| JSON | Python | TypeScript |
| --- | --- | --- |
| `null` | `None` | `null` |
| `boolean` | `bool` | `boolean` |
| safe integer | `int` | `number` |
| string | `str` | `string` |
| array | `list` | `Array` |
| object | `dict` | object/interface |

JSON property names remain camelCase in Python and TypeScript boundary
documents. Python implementation types may use internal snake_case only behind
explicit serialization. TypeScript must not replace required `null` with
`undefined`.

## 9. Security and privacy boundary

Any future endpoint remains on the existing `127.0.0.1` dashboard server and
requires the existing dashboard token before parsing or mutating settings.
G5.2 does not change the host, token validation, CSP, logging or body-size
policy.

The future implementation must:

- use the existing report snapshot, never direct collection access from the
  frontend;
- parse only bounded JSON objects;
- reject unknown fields;
- write settings atomically inside the profile-scoped add-on data directory;
- quarantine corrupt supported-version settings without logging their raw
  content;
- preserve future-schema documents;
- avoid paths, secrets, tokens and raw study rows in logs and errors.

## 10. Executable evidence

Canonical valid fixtures live in
[`tests/fixtures/gamification-contract-v1/`](../../tests/fixtures/gamification-contract-v1/)
and include disabled, enabled, rest-day, active-on-rest-day, completed,
partial-coverage, unavailable-source, mutation and error cases.

[`tests/test_gamification_contract_v1.py`](../../tests/test_gamification_contract_v1.py)
checks:

- duplicate-key-safe JSON parsing and schema self-validation;
- every valid fixture against schema and semantic invariants;
- unknown fields, wrong versions, unsafe revisions, invalid/duplicate
  weekdays, impossible plans, invalid dates/timestamps, wrong week order/length,
  invalid completion state and incomplete conflict errors;
- exact parity between named human examples and fixtures;
- absence of post-MVP machine fields;
- absence of runtime, frontend, package, CI and live API changes in the G5.2
  candidate diff.

This evidence validates the contract candidate. It does not prove an
implementation, real-Anki behavior, visual acceptance, merge or release.
