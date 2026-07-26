# G1.5 — Confirmatory protocol Review XP

## Статус

```text
stage: G1.5
protocol: FROZEN_PRE_RESULTS
results accessed: NO
ranking: PROHIBITED
final candidate selection: PROHIBITED
production approval: PROHIBITED
G1.6: NOT STARTED
```

Этот protocol фиксирует confirmatory-проверку двух survivors G1.4:

```text
P-STEP-ZERO
P-TAPER-ZERO-30D
```

`R-CURRENT` используется только как reference. Rejected variants
`P-STEP-NEUTRAL-RATIO` и `P-TAPER-NEUTRAL-RATIO-30D` не входят в matrix.

## Основание

G1.4 завершил bounded screening на frozen matrix из 160 units и зарегистрировал
по одному survivor в каждом семействе. G1.5 не повторяет screening и не выполняет
новый parameter search. Его задача — проверить устойчивость survivors на fresh
seeds, exact replay, дополнительных model conditions, persona safety и
candidate-aware invariant/abuse probes.

Authoritative machine protocol:

```text
research/gamification-sim/contracts/review-xp-confirmatory-protocol-v1.json
```

Strict schema:

```text
research/gamification-sim/schemas/review-xp-confirmatory-protocol-v1.schema.json
```

## Frozen variants

```text
reference:
R-CURRENT

confirmatory candidates:
P-STEP-ZERO
P-TAPER-ZERO-30D
```

Новые endpoints, taper shapes, transition days и reward parameter overrides
запрещены.

## Fresh seeds

Seeds детерминированно выведены до просмотра результатов из labels protocol:

```text
primary:
5978107021558220631

secondary:
5509807251554775963
```

Они не совпадают с G1.4 seeds.

## Core longitudinal matrix

Оси:

```text
3 variants
× 4 matched policy pairs
× 2 horizons
× 2 replicas
× 2 fresh seeds
× 2 replay identities
× 3 model conditions
= 576 units
```

Policy pairs:

```text
retention-high-cycle
retention-low-cycle
intentional-backlog
honest-backlog-return
```

Horizons:

```text
90
365
```

Model conditions используют только committed cohort sizes:

```text
MODEL-NATIVE-COHORT:
90 → 24
365 → 20

MODEL-COHORT-20:
90 → 20
365 → 20

MODEL-COHORT-24:
90 → 24
365 → 24
```

Это sensitivity model condition, а не mutation candidate parameters.

## Persona safety matrix

Используются все 16 committed personas и 30 independent synthetic
post-transition days с simulation day `60..89`.

```text
3 variants
× 16 personas
× 2 fresh seeds
× 2 replay identities
= 192 units
```

Persona evidence проверяет:

- baseline preservation;
- отсутствие suppression;
- отсутствие negative totals и cap/breakdown violations;
- exact same-input replay;
- finite deterministic output.

Persona matrix не является longitudinal card-history evidence и не заменяет core
longitudinal matrix.

## Invariant и abuse probes

```text
3 variants
× 12 probes
× 2 replay identities
= 72 units
```

Probes:

```text
INV-ORDINARY-UNIT
INV-AGAIN-CREDIT
INV-BUTTON-NEUTRAL
INV-SESSION-INVARIANT
INV-NO-RESPONSE-TIME
INV-RESPONSE-VALIDITY
ABUSE-DUPLICATE-REPLAY
ABUSE-RELEARNING-LOOP
ABUSE-PREVIEW-FARM
ABUSE-FORCED-DUE
ABUSE-MICRO-SCOPE-COMPLETION
INV-RESEARCH-ONLY
```

## Exact accounting

```text
core: 576
persona safety: 192
probes: 72
total: 840
```

Manifest обязан содержать 840 units, 840 unique IDs и нулевые
missing/extra/duplicates.

## Gates

Frozen thresholds:

```text
absolute tolerance: 1e-9
365-day endpoint cap: <= 0.03
cross-horizon growth: <= 1e-9
baseline delta vs R-CURRENT: abs <= 1e-9
honest backlog differential vs R-CURRENT: >= -1e-9
intentional backlog advantage delta vs R-CURRENT: <= 1e-9
ordinary successful review: 1.00 RU
Again AttemptCredit: 0.25 RU
```

Все gates non-compensable. Model-condition, seed, replica или persona failures
нельзя компенсировать aggregate score.

## Outcome semantics

Для каждого survivor отдельно допускаются только:

```text
CONFIRMATORY_ELIGIBLE
CONFIRMATORY_NOT_ELIGIBLE
CONFIRMATORY_INCONCLUSIVE
```

`CONFIRMATORY_ELIGIBLE` означает, что evidence complete и все required gates
прошли.

`CONFIRMATORY_NOT_ELIGIBLE` означает, что evidence complete, но один или более
required gates не прошли.

`CONFIRMATORY_INCONCLUSIVE` означает, что evidence incomplete, invalid или не
может быть интерпретирован по frozen protocol.

G1.5 не ранжирует STEP и TAPER. Допустимы одновременно два eligible outcomes,
один eligible outcome либо отсутствие eligible outcomes.

## Publication barrier

До canonical run должны быть committed и pushed:

- human protocol;
- machine protocol;
- strict schema;
- executable manifest/harness;
- evidence validator;
- CLI;
- focused tests.

После push должны быть подтверждены local/remote SHA equality и отсутствие
result files в published commit.

Только после этого разрешён canonical run exact published SHA.

## Amendment policy

До результатов substantive amendment требует новой версии protocol и нового
publication barrier.

После просмотра результатов substantive defect требует:

1. disclosure;
2. invalidation затронутого result;
3. новую версию protocol;
4. полный rerun exact matrix.

Typo/link correction может сохранить version только при неизменных scientific
semantics и executable manifest.

## Production boundary

G1.5 не меняет:

- add-on runtime;
- dashboard;
- API/payload;
- Anki collection access;
- local server/token handling;
- sanitizer/preview;
- package/release workflows;
- telemetry/remote services.

Все inputs synthetic и research-only.
