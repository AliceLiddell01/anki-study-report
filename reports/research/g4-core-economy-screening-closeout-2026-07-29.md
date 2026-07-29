# G4 core economy — screening closeout

**Дата:** 2026-07-29

**Scope:** research contracts, deterministic evaluator, synthetic results, decision и documentation

**Final outcome:** `REJECT`

## Repository identities

```text
repository: AliceLiddell01/anki-study-report
branch: chatGPT/G4
base branch: gamification
starting HEAD: 0842a0b1f57c5f4711cccab206c4a116cfc0666d
origin/gamification observed at start: 0842a0b1f57c5f4711cccab206c4a116cfc0666d
v3 publication SHA: aa8d119ad5896267f46d9eb644392de11c0e32a2
v4 publication SHA: 78ce71d82d72577f8283707a85b8e6b226330c94
v4 evaluator SHA: 6174c5deae40b339b7e738ae08c1060b3f0158fa
```

## Corrective chronology

V2 оставался immutable и был superseded до execution. V3 устранил известные protocol gaps и был опубликован до evaluator/results. Первый v3 run обнаружил три contract/evaluator defects:

- required gate metrics не были row-local для части matrix;
- expected-control rule был шире фактического predicate;
- marginal probe попадал на combined boundary вместо измерения below-cap marginality.

Результаты v3 invalidated и не использованы. V4 был опубликован как full replacement до нового screening. История v3 сохранена в [invalidation report](g4-core-economy-v3-screening-invalidation.md).

## Accepted v4 evidence

```text
protocol digest: a6f8faf819e7d4a7c3d5ffd73ad82775642020faa019584b823e20ad3f2b18cd
pipeline digest: f49169b3e91e04e781819bea33b5c86778b981e17a27c954b0ed7295b387af62
scenario digest: fabd2cb9934953987cf6b64a6e34d070c3c1d26ef2d4f21641cfe5649cf6443d
matrix digest: 6c640a17643ac83c09fe56276072930152baa07f46147ab76c36b7f2b8160f67
manifest digest: 585fe8ffd480db71feecd1d188eb3eb4ee4efe464ec2329bf26df56e96656dcf
result artifact digest: ad000099135574d285561d8e9bcc624ff430d25c42dd5b2d89a35476f3fad5db
result-set digest: bbbacf3880378409a740c26d85dbc589178ec2480f471107639e4c7ed8198d90
```

```text
expected / actual / unique rows: 1275 / 1275 / 1275
missing / extra / duplicates: 0 / 0 / 0
gate results: 3952
metric results: 3710
control expected failures: 186
unexpected control passes: 50
unexpected failures: 33
detached validation: PASS
byte-identical reproduction: PASS
synthetic only: YES
real-user data: NO
production imports: NO
```

## Result analysis

Unexpected failures:

```text
HG-EXTREME-VOLUME-BOUNDED: 21
HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED: 12
```

Recommendation-eligible integrated bundles:

```text
B-INTEGRATED-GRACEFUL-MEDIUM: 4 unexpected failures
B-INTEGRATED-STEPPED: 4 unexpected failures
B-INTEGRATED-GRACEFUL-HIGH: 11 unexpected failures
```

`B-INTEGRATED-ABRUPT-CONTROL` имел `62` expected control failures и не был recommendation-eligible. Hard gates non-compensable, weighted score отсутствует. Итог: `REJECT`.

## Final research choices

```text
Review winner: P-TAPER-ZERO-30D
Learn winner: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
CROSS_DOMAIN_CONVERSION: X-EQUALIZED-1_0-1_0
UNCERTAINTY_RESPONSE: NONE
DAILY_BOUNDING: D-PER-DOMAIN-BOUNDED-MEDIUM
PRODUCTIVE_DAY: P-DAY-DOMAIN-EVIDENCE
LEVEL_CURVE: L-NPU-POWER-1_6
STREAK_PLANNED_REST: S-ONE-GRACE-14D
MOMENTUM: M-ROLLING-7-NONREST
RECOVERY: R-STEPWISE-2-NORMAL-DAYS
```

Review tie-break prioritizes lower legitimate-context harm over lower policy complexity. Learn selection minimizes unvalidated reward-state surface. Neither choice removes the frozen evidence limitations or permits production integration.

## Verification boundary

Focused v4 protocol/evaluator tests, schema checks, negative corpus, exact coverage, detached result validation and byte-identical reproduction passed. Full research suite retained two pre-existing frozen-identity failures outside the G4 changed paths; exact commands and final status are recorded in the task/PR report.

Not run:

```text
Fast CI: NOT REQUIRED — research/docs-only diff
package validation: NOT REQUIRED — package boundary unchanged
Docker real-Anki E2E: NOT REQUIRED — production/runtime boundary unchanged
frontend build: NOT REQUIRED — frontend unchanged
```

## Production boundary

No add-on runtime, dashboard, API, payload, persistence, scheduler, FSRS, workflow, package or release path changed. G5/G6 remain conditional and not started.
