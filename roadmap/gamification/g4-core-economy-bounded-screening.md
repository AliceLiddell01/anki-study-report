# G4.4 — bounded screening и финальное закрытие G4

## Статус

```text
G4: COMPLETE
G4.4: COMPLETE
G4 final outcome: REJECT
recommended integrated bundle: NONE
Review winner: P-TAPER-ZERO-30D
Learn winner: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
production integration: PROHIBITED
G5: CONDITIONAL / NOT STARTED
G6: CONDITIONAL / NOT STARTED
```

## Closure decision

Replacement protocol v4 был опубликован до replacement screening и затем исполнен без post-result изменения semantics. Matrix завершена `1275/1275/1275`, missing/extra/duplicates равны `0/0/0`, detached validation и byte-identical reproduction прошли.

Ни один recommendation-eligible integrated bundle не прошёл все non-compensable gates. Medium и stepped bundles получили по четыре unexpected failures `HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED`; high bundle дополнительно получил семь failures `HG-EXTREME-VOLUME-BOUNDED`. По frozen decision discipline итог — `REJECT`, а не recommendation или скрытая компенсация score.

Технические evidence и dimension decisions: [G4.4 bounded screening](../../docs/gamification/core-economy-bounded-screening.md).

Run identities:

```text
v4 publication SHA: 78ce71d82d72577f8283707a85b8e6b226330c94
v4 evaluator SHA: 6174c5deae40b339b7e738ae08c1060b3f0158fa
rows: 1275 / 1275 / 1275
gate results: 3952
metric results: 3710
unexpected failures: 33
result artifact digest: ad000099135574d285561d8e9bcc624ff430d25c42dd5b2d89a35476f3fad5db
result-set digest: bbbacf3880378409a740c26d85dbc589178ec2480f471107639e4c7ed8198d90
```

## Publication chronology

```text
G4.3 v1: SUPERSEDED_PRE_EXECUTION
G4.3 v2: SUPERSEDED_PRE_EXECUTION
G4.3 v3: INVALIDATED_AFTER_SCREENING
G4.3 v3 decision use: PROHIBITED
G4.3 v4: FROZEN_AND_EXECUTED
```

V3 остается immutable historical checkpoint. Его первые results выявили evaluator-contract defects; они не были закоммичены как accepted evidence. V4 исправил defects до нового result access и является единственным источником финального решения.

## G1/G2 decisions carried into closure

- Review winner: `P-TAPER-ZERO-30D`. При равных G4 aggregates он лучше выполняет owner-authorized tie-breaker «минимальный вред легитимному контексту»; STEP остаётся non-falsified alternative.
- Learn winner: `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING`. Он сохраняет `1.0 LRU` без неподтверждённой provisional state surface.
- Learn status остаётся `CONFIRMATORY_INCONCLUSIVE`.
- Learn limitation остаётся `DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE`.
- Review averaging остаётся `PROHIBITED`.

## Dimension ledger

```text
CROSS_DOMAIN_CONVERSION: X-EQUALIZED-1_0-1_0
UNCERTAINTY_RESPONSE: NONE
DAILY_BOUNDING: D-PER-DOMAIN-BOUNDED-MEDIUM
PRODUCTIVE_DAY: P-DAY-DOMAIN-EVIDENCE
LEVEL_CURVE: L-NPU-POWER-1_6
STREAK_PLANNED_REST: S-ONE-GRACE-14D
MOMENTUM: M-ROLLING-7-NONREST
RECOVERY: R-STEPWISE-2-NORMAL-DAYS
```

Dimension selections не образуют recommendation: обязательная uncertainty dimension не имеет passing eligible candidate.

## Production boundary

G4 closure не меняет add-on runtime, dashboard, payload, API, persistence, scheduler, FSRS, package, CI workflow или release. G5/G6 не активированы автоматически. Любая новая calibration должна быть отдельной prospective version и не может переписывать v4 outcomes.
