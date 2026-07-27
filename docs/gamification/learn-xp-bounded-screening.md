# Learn XP bounded screening — техническая справка G2.4

**Stage:** `G2.4 — Bounded Learn XP screening implementation`  
**Status:** `IN PROGRESS — PRE-RESULTS IMPLEMENTATION`  
**Protocol:** `FROZEN_PRE_SCREENING_IMPLEMENTATION`  
**Protocol publication SHA:** `41313c9369c76d331d489a9aa4b44da2497b3132`  
**Starting gamification SHA:** `933325f8d2647d52cbc0d6859ff44ded0b6686c4`  
**Screening executed:** `NO`  
**Production integration:** `PROHIBITED`

Документ фиксирует исполнимое толкование frozen G2.3 protocol до просмотра результатов. Он не содержит candidate outcomes, survivor, family result или финального Learn XP решения.

## Назначение и границы

Harness выполняет только synthetic research matrix G2.4:

```text
10 candidate/reference identities
30 frozen scenarios
34 conditions per identity
replica 0
seed null / ABSENT_DETERMINISTIC
340 expected units
340 unique unit IDs
adaptive units 0
```

Реализация не импортирует production add-on, не читает Anki collection, не меняет scheduler/FSRS/due dates, не пишет production XP и не использует real-user data.

## Нормативные источники

1. текущий research code и tests;
2. `contracts/learn-xp-candidate-protocol-v1.json`;
3. `schemas/learn-xp-candidate-protocol-v1.schema.json`;
4. G2.1/G2.2 contracts, schemas и frozen fixtures;
5. `docs/gamification/learn-xp-candidate-protocol.md`;
6. эта pre-results execution reference.

Review XP G1.4/G1.5 используется только как pattern для manifest, publication barrier, evidence и detached validation. Его formulas, matrix и metrics в Learn XP не переносятся.

## Реализованные компоненты

```text
src/gamification_sim/learn_reward_allocation.py
src/gamification_sim/learn_bounded_screening.py
schemas/learn-xp-bounded-screening-evidence-v1.schema.json
tests/test_learn_bounded_screening.py
```

Harness:

- валидирует frozen protocol/schema и Git blob identities;
- проверяет G2.1/G2.2 continuity и protocol publication ancestry;
- строит manifest только через `generate_dry_units(protocol)`;
- исполняет 23 unmodified lifecycle fixtures и 7 explicit accounting mappings;
- отделяет lifecycle result от Learn allocation result;
- вычисляет 14 frozen metrics и 23 non-compensable gates;
- присваивает exact statuses и применяет family lexicographic policy;
- формирует strict evidence и пересчитывает его detached validator;
- записывает external evidence bundle вне repository path.

## Pre-results execution mapping

### Frozen lifecycle fixtures

Для `FROZEN_LIFECYCLE_FIXTURE` загружается exact committed fixture. Event trace, case role, expected state и expected transition trace не изменяются. Candidate/reference accounting применяется поверх полученного lifecycle result.

Configuration/time axes остаются frozen condition labels. Они не переписывают fixture trace и не создают дополнительный Cartesian product.

### Candidate-accounting scenarios

До publication barrier зафиксирован mapping `EXPLICIT_PRE_RESULTS_ACCOUNTING_TRACE_V1`:

| Scenario | Проверяемая операция |
|---|---|
| `SCN-ACCOUNT-PENDING-ALLOCATION` | создание pending и provisional accounting |
| `SCN-ACCOUNT-CONFIRM-SETTLEMENT` | source-linked independent confirmation и settlement |
| `SCN-ACCOUNT-EXPIRE-VOID` | expiry void |
| `SCN-ACCOUNT-CANCEL-VOID` | cancellation void |
| `SCN-ACCOUNT-INVALIDATE-VOID` | invalidation void |
| `SCN-ACCOUNT-SUBJECT-COLLISION` | CARD fragmentation против NOTE-SIBLING grouping |
| `SCN-ACCOUNT-REFERENCE-ZERO` | нулевая reference allocation |

После просмотра результатов mapping нельзя менять без invalidation, нового implementation commit и полного rerun всех 340 units.

## Allocation semantics

### Reference

```text
pending = 0
confirmed = 0
total = 0
status = REFERENCE_ONLY
survivor eligible = false
```

### Confirmation-only

```text
before confirmation = 0
CONFIRMED = 1.0 LRU
terminal non-confirmed = 0
```

### Pending/confirmed split

```text
PENDING = 0.25 provisional LRU
CONFIRMED settlement = 0.75 LRU
total after confirmation = 1.0 LRU
EXPIRED/CANCELLED/INVALIDATED = 0 LRU
```

Negative allocation, total выше `1.0`, повторное создание pending и retained terminal value запрещены fail-closed.

## Delay semantics

D1/D2 применяются к source-linked synthetic events. Confirmation требует одновременно:

- processed source event;
- source transition, создавший или уже представляющий pending;
- тот же synthetic achievement subject и episode;
- independent-success signal, не same-chain;
- valid provenance/continuity;
- minimum elapsed и minimum Anki-day delta;
- отсутствие elapsed/day expiry.

Boundary interpretation, зафиксированная до результатов:

```text
minimum elapsed/day: inclusive (>=)
expiry elapsed/day: exclusive upper bound (<)
minimum conditions: conjunction
expiry: достижение любой frozen expiry boundary закрывает окно
```

Следовательно:

```text
D1: 1439 fail / 1440 pass; day 0 fail / day 1 pass;
    10079 inside / 10080 expired; day 6 inside / day 7 expired
D2: 4319 fail / 4320 pass; day 2 fail / day 3 pass;
    20159 inside / 20160 expired; day 13 inside / day 14 expired
```

Displayed interval, scheduler `Review` state и wall clock не используются как confirmation timer.

## Subject strategies

`S-CARD` использует namespaced synthetic card identity. `S-NOTE-SIBLING` использует synthetic note-derived sibling-group identity. Reverse/cloze/template proliferation одной synthetic note не создаёт новый group achievement.

Private card/note content не читается. Отсутствующая или противоречивая identity continuity приводит к fail-closed ambiguity/fragmentation evidence.

## Manifest accounting

Manifest включает repository/base/implementation identities, protocol/schema blobs и digests, G2.1/G2.2 continuity, fixture manifest identity, dry-generator blob, axes, scenario registry и полный unit list.

Обязательные равенства:

```text
units == generate_dry_units(protocol)
expected = 340
actual = 340
unique = 340
missing = 0
extra = 0
duplicates = 0
seed = null
replica = 0
```

`unit_id` не пересчитывается альтернативной схемой.

## Metric aggregation

Pre-results aggregation `METRIC_AGGREGATION_V1` фиксируется так:

- allocation/exposure/attack-gain/retained-LRU/collision contributions суммируются по frozen cells;
- `M-CONFIRMATION-RATE` — confirmed case count / all case count;
- `M-TERMINAL-RATE` — terminal case count / all case count;
- `M-TIME-TO-CONFIRMATION` — arithmetic mean elapsed minutes по confirmed cases;
- `M-ACTIVE-PENDING-PEAK` — maximum simultaneous synthetic pending indicator среди cells;
- `M-EXPLANATION-COMPLEXITY-FIELDS` — frozen structural field count evaluator;
- `DESCRIPTIVE` metrics не участвуют в selection;
- selection использует только exact protocol `lexicographic_metric_ids` order и не использует weighted score.

Matrix multiplicity не удаляется и не перевзвешивается post hoc. D1/D2 advantage по delay/exposure metrics трактуется только как следствие frozen policy.

## Evidence и detached validation

Schema: `schemas/learn-xp-bounded-screening-evidence-v1.schema.json`, Draft 2020-12, `additionalProperties: false`.

Detached validator заново вычисляет:

- current Git/base/publication identity и manifest;
- exact unit definitions и unit evidence;
- reverse-order deterministic replay;
- repository/research/privacy shared gate evidence;
- 23 gates, 14 metric aggregates и lexicographic vectors;
- candidate/reference statuses и family outcomes;
- manifest/evidence digests.

Stored `PASS`, candidate status, survivor или family outcome не считаются доверенными данными.

## CLI

Из `research/gamification-sim/`:

```bash
PYTHONPATH=src python -m gamification_sim --research-root . validate-learn-xp-screening
```

Canonical run разрешён только после non-force push implementation commit и подтверждения remote SHA equality. Для canonical provenance используется installed console entry point; launcher path нормализуется до публичного `gamification-sim`, а private workspace/output roots передаются только через environment:

```bash
export GAMIFICATION_SIM_RESEARCH_ROOT="$(pwd)"
export GAMIFICATION_SIM_OUTPUT_DIR="<external-output-root>"
gamification-sim run-learn-xp-screening \
  --implementation-sha <published-implementation-sha> \
  --base-sha 933325f8d2647d52cbc0d6859ff44ded0b6686c4
```

`--output-dir` поддерживается для обычных запусков, но canonical run не передаёт private absolute paths в argv. `--no-write` выполняет in-memory run без bundle.

Detached evidence:

```bash
PYTHONPATH=src python -m gamification_sim --research-root . \
  validate-learn-xp-screening-evidence <external-bundle>/evidence.json
```

## External bundle

Writer создаёт вне repository path:

```text
learn-xp-g2-4-evidence-<implementation-short-sha>/
  manifest.json
  evidence.json
  summary.md
  environment.json
  command.txt
  FILES.sha256
learn-xp-g2-4-evidence-<implementation-short-sha>.tar.gz
```

Raw evidence не коммитится. Original bundle сохраняется до G2.5/G2.6 либо отдельного archive decision.

## Publication и continuation policy

До canonical results remote implementation commit обязан содержать harness, allocation/delay/subject evaluators, schema, detached validator, CLI, tests и эту reference — без outcomes/evidence/result summary.

Interrupted run можно продолжать только на том же implementation SHA и manifest digest. Final evidence обязано содержать ровно 340 unique units без selective rerun или дополнительных scenarios.

После result access substantive bug fix требует disclosure, invalidation предыдущего run, нового implementation commit и полного rerun 340/340.

## Claims boundary

Допустимо утверждать только, что candidate:

- прошёл или не прошёл frozen synthetic gates;
- сохранил или нарушил frozen accounting/safety invariants;
- был выбран внутри family frozen lexicographic policy.

Нельзя утверждать human-learning benefit, motivation benefit, optimal delay, optimal pending ratio, final Learn XP model или production readiness.

## Canonical replacement result

```text
screened implementation SHA: 548b27de6283b32fb27541db02ce6c8b65c29756
base SHA: 933325f8d2647d52cbc0d6859ff44ded0b6686c4
protocol publication SHA: 41313c9369c76d331d489a9aa4b44da2497b3132
expected / actual / unique: 340 / 340 / 340
missing / extra / duplicates: 0 / 0 / 0
manifest digest: fafff6ac14b00e268d25a9a7b3553aad94b0e6594b64b40722fd44eba4a91e1a
evidence digest: 5144665ad75110cfd5817b6d76c9791274bf206ee25d01d34ed05e72f45d3da6
evidence.json SHA-256: d0d79802f8512fa40730aac5c377d75021ff39100330483a784c43ce20b09462
external bundle SHA-256: a2578fd2f7540cff10fdde0adc389afeaf8267dbf34185d2378467e6552ffa78
detached validation: PASS
deterministic replay: PASS
byte-identical bundle reproduction: PASS
production approved: false
production integration: false
G2.5 started: false
```

Family-local outcomes:

```text
F-CONFIRMATION-ONLY
→ C-CONFIRMATION-ONLY-D1-NOTE-SIBLING

F-PENDING-CONFIRMED-SPLIT
→ C-PENDING-SPLIT-D1-NOTE-SIBLING
```

Все восемь candidates получили `SCREENING_ELIGIBLE`; обе reference variants остались `REFERENCE_ONLY`. Cross-family ranking не выполнялся, final Learn XP model не выбирался.

## Disclosed invalid attempt

Первый canonical attempt на `ef7c638a70b7bbb7883f512309a1e248118a9203` выполнил frozen matrix и открыл результаты, но был целиком признан `INVALID`, поскольку byte-identical archive reproduction зависела от filesystem-derived `TarInfo.mode`.

```text
classification: HARNESS
prior evidence digest: 51ef8d8caa55a2579795a72f5af1576da69da224a5023190d5fde6c145aac726
prior archive SHA-256: 58989ea862be86e2edb0c71b19aec520214af7bb0abe08791d7f72396d66b2c3
results viewed: true
screening design changed: false
required rerun: FULL_340_UNIT_MATRIX
old/new evidence mixed: false
```

Correction sets every regular tar member mode to `0644`; families, ratios, delays, subject strategies, scenarios, unit IDs, gates, metrics, lexicographic ordering, statuses, tie policy and missing-data behavior did not change. Replacement evidence includes the required post-results amendment and preserves the invalid bundle only as quarantined external evidence.

## Continuation boundary

G2.4 is complete. The external canonical bundle remains owner-managed and is not committed to Git. Any G2.5 work requires a separate activation and must start from the two family-local survivors, exact evidence identities, known limitations and unresolved confirmatory questions. G2.4 does not authorize a cross-family winner, final model or production integration.
