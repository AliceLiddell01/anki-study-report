# Core Gamification Economy — модель входов и неопределённости G4.2

**Contract ID:** `core-economy-input-normalization`  
**Version:** `1`  
**Status:** `FROZEN_PRE_CANDIDATE_FAMILY_DESIGN`  
**Stage:** `G4.2 — Input normalization and uncertainty model`  
**Production integration:** `PROHIBITED`  
**G4.3:** `NEXT / NOT STARTED`

Нормативный machine-readable источник: [`core-economy-input-normalization-v1.json`](../../research/gamification-sim/contracts/core-economy-input-normalization-v1.json). Его проверяет строгая Draft 2020-12 schema [`core-economy-input-normalization-v1.schema.json`](../../research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json).

## 1. Назначение

G4.2 определяет не количество XP, а **normalization boundary** между frozen Review и Learn research sources:

```text
typed source input
→ explicit source identity and limitations
→ future-normalization eligibility disposition
→ decomposable contribution placeholder
→ explicit day/session axes
→ daily aggregation placeholder
```

G4.2 не вычисляет normalized value, не выбирает conversion ratio и не начинает candidate-family design.

Initial economy остаётся двухдоменной:

```text
REVIEW_DOMAIN
LEARN_DOMAIN
```

`CREATE_DOMAIN` запрещён и остаётся отложенным вместе с G3.

## 2. Source boundaries

### Review

```text
G1 final outcome: DEFER_REVIEW_MODEL
Review winner: NONE

P-STEP-ZERO:
CONFIRMATORY_ELIGIBLE
selected: false
falsified: false

P-TAPER-ZERO-30D:
CONFIRMATORY_ELIGIBLE
selected: false
falsified: false
```

Raw G1 bundles не объявляются freshly revalidated. Исторические `Review Unit` formulas и day policies являются source-specific research references и не становятся common economy policy.

### Learn

```text
source model:
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING

source status:
CONFIRMATORY_INCONCLUSIVE

limitation:
DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE

source unit:
LRU

frozen source total:
1.0 LRU

common economy XP:
false
```

`1.0 LRU` является source accounting value. Он не выбирает Review/Learn ratio и не создаёт common XP unit.

### G4.1 continuity

```text
core-economy-problem-contract:
FROZEN_PRE_NORMALIZATION_ANALYSIS

G4.1 schema correction chronology:
defective intermediate commit reachable from merged history: YES
defective schema present in final tree: NO
defective schema used as validated result: NO
```

G4.2 не изменяет G4.1 contract/schema.

## 3. Терминология G4.2

| Term | Значение |
|---|---|
| `DOMAIN_INPUT_ENVELOPE` | Общий strict envelope source record без implicit coercion и production semantics. |
| `REVIEW_DOMAIN_INPUT` | Typed Review record с обязательным candidate member `REVIEW_MODEL_AXIS_V1`. |
| `LEARN_DOMAIN_INPUT` | Typed confirmation-only Learn record с обязательной inconclusive limitation. |
| `NORMALIZATION_INPUT` | Common comparative interface, сохраняющий source value/unit/status без numeric mapping. |
| `DOMAIN_CONTRIBUTION_RECORD` | Decomposable placeholder будущей contribution с `NOT_SELECTED` normalized fields. |
| `SOURCE_DAY_AXES` | Одновременное typed представление `SESSION`, `ANKI_DAY`, `CALENDAR_DAY`. |
| `DAILY_AGGREGATION_INPUT` | Day-level grouping bounded inputs с duplicate rejection и neutral sessions. |
| `DAILY_AGGREGATION_RESULT_PLACEHOLDER` | Decomposable day result без normalized total и productive-day classification. |
| `ELIGIBILITY_DISPOSITION` | Typed решение о допустимости record для будущей normalization. |
| `FAIL_CLOSED_REASON` | Stable reason code, запрещающий silent default или coercion. |
| `PROVENANCE` | Source contract/model/status/evidence identity и transformation version. |
| `PERSONA_DESCRIPTOR` | Synthetic workload metadata без event trace, counts, duration, XP или seed. |
| `FIXTURE_REQUIREMENT` | Prospective requirement к future deterministic trace, не сам trace. |

Все 30 G4.1 terms сохраняются без изменения.

## 4. Common domain input envelope

Обязательные fields:

```text
record_id
record_type
domain
source_model_id
source_contract_id
source_contract_version
source_stage
source_status
evidence_class
eligibility_disposition
limitation_codes
achievement_subject
source_event_identity
source_day_axes
source_value
value_unit
decomposition
provenance
production_semantics
```

Rules:

- `record_id`, source/event/day/session identities — synthetic и immutable;
- domain/model/status/unit задаются явно;
- source values не приводятся к common unit;
- implicit coercion запрещён;
- `production_semantics` всегда `false`;
- real content и identifiable history запрещены;
- missing или conflicting identity fail closed.

## 5. Review domain input

`REVIEW_DOMAIN_INPUT` обязан содержать:

```text
review_candidate_id
candidate_status: CONFIRMATORY_ELIGIBLE
candidate_selected: false
candidate_falsified: false
uncertainty_axis_id: REVIEW_MODEL_AXIS_V1
uncertainty_member
source_event_identity
source_value
value_unit: REVIEW_UNIT
limitation_codes
provenance
```

Allowed members:

```text
P-STEP-ZERO
P-TAPER-ZERO-30D
```

`source_model_id`, `review_candidate_id` и `uncertainty_member` обязаны совпадать. Candidate нельзя пропустить, вывести из контекста, заменить default или отметить winner.

Для одного synthetic source scenario разрешены два parallel records:

```text
same source evidence
→ P-STEP-ZERO record
→ P-TAPER-ZERO-30D record
```

Повтор того же event внутри одного axis member является duplicate. Если matched source невозможно представить под обоими members, batch получает fail-closed disposition.

## 6. Review uncertainty model

```text
uncertainty_axis_id:
REVIEW_MODEL_AXIS_V1

members:
P-STEP-ZERO
P-TAPER-ZERO-30D

selection:
NONE

default:
NONE

aggregation:
PARALLEL_SEPARATE

averaging:
PROHIBITED

winner criterion:
NOT_DEFINED

cross-domain criterion:
NOT_DEFINED
```

G4.3 позднее может определить candidate economy families, прогнать обе Review variants и измерить sensitivity. G4.2 не может выбирать simpler/smoother/narratively preferable candidate и не может усреднять pair.

## 7. Learn domain input

`LEARN_DOMAIN_INPUT` обязан содержать:

```text
source_model_id:
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING

candidate_status:
CONFIRMATORY_INCONCLUSIVE

limitation_reason:
DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE

confirmatory_eligible:
false

production_ready:
false

production_approved:
false

achievement_subject:
NOTE_SIBLING

allocation_semantics:
CONFIRMATION_ONLY_NO_PROVISIONAL_STATE

source_value:
1.0

value_unit:
LRU

common_economy_xp:
false

identity_continuity_code:
EXPLICIT_SYNTHETIC_NOTE_SIBLING
```

Identity fields задаются явно. Card text, note fields и content fingerprint не могут использоваться как substitute identity. Missing, ambiguous или conflicting identity fail closed.

## 8. Learn limitation propagation

`CONFIRMATORY_INCONCLUSIVE` и `DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE` обязаны оставаться видимыми в:

```text
LEARN_DOMAIN_INPUT
DOMAIN_CONTRIBUTION_RECORD
DAILY_AGGREGATION_RESULT_PLACEHOLDER
future explanation
future candidate evaluation
final G4 claims
```

Разрешённая формулировка:

> G4 использует рекомендованный Learn research candidate как bounded input с сохранённым identity limitation.

Запрещены claims `confirmed`, `CONFIRMATORY_ELIGIBLE`, `production-ready` и `production-approved`.

## 9. Common normalization interface

`NORMALIZATION_INPUT` переносит:

```text
domain_input_id
domain
source_model_id
source_value
source_unit
source_status
eligibility_disposition
limitation_codes
uncertainty_group
day_axes
provenance
numeric_mapping: NOT_SELECTED
unit_coercion: false
```

Интерфейс позволяет G4.3 подключать будущие candidate policies, но сам не содержит mapping, weight, ratio, cap, threshold, formula или winner.

## 10. Contribution record boundary

`DOMAIN_CONTRIBUTION_RECORD` содержит:

```text
contribution_id
source_input_id
domain
source_model_id
axis_identity
disposition
normalized_value: NOT_SELECTED
normalized_unit: NOT_SELECTED
conversion_policy_id: NOT_SELECTED
reason_codes
limitation_codes
decomposition
version
```

Opaque aggregate score запрещён. Любая будущая contribution должна оставаться decomposable до source input, model, axes, limitations и reason codes.

## 11. Axes

### `SESSION`

```text
role: GROUPING_AND_OBSERVABILITY_ONLY
reward multiplier: PROHIBITED
completion bonus: PROHIBITED
session split gain: PROHIBITED
```

Разбиение одинаковой работы на большее число sessions не должно повышать future contribution.

### `ANKI_DAY`

```text
role: TYPED_SCHEDULER_DAY_AGGREGATION_AXIS
identifier: synthetic anki_day_id
due-date mutation: false
calendar equality by default: false
missing mapping: FAIL_CLOSED
```

### `CALENDAR_DAY`

```text
role: CIVIL_REPORTING_AXIS
identifier: synthetic calendar_day_id
timezone policy: NOT_SELECTED
host timezone fallback: PROHIBITED
clock/timezone gain: PROHIBITED
ambiguous mapping: FAIL_CLOSED
```

### Cross-axis relation

```text
SESSION = grouping context
source event → one ANKI_DAY mapping when available
source event → one CALENDAR_DAY mapping when available
ANKI_DAY != CALENDAR_DAY by default
missing ANKI_DAY cannot fall back to CALENDAR_DAY
missing CALENDAR_DAY cannot fall back to ANKI_DAY
```

G4.2 не определяет user-facing timezone, streak reset time или production storage.

## 12. Daily aggregation boundary

`DAILY_AGGREGATION_INPUT` использует только bounded eligible domain inputs и сохраняет:

```text
explicit axis identity
unique input IDs
source decomposition
separate Review candidate partitions
Learn limitation
neutral session grouping
```

Rejected:

```text
duplicate input IDs
raw event count as contribution
opaque total
implicit axis substitution
silent candidate collapse
```

`DAILY_AGGREGATION_RESULT_PLACEHOLDER` может содержать:

```text
status
included_input_ids
excluded_input_ids
invalid_input_ids
domain_partition
review_uncertainty_partition
limitation_codes
axis_identity
normalized_total: NOT_SELECTED
productive_day_status: NOT_SELECTED
decomposition
```

G4.2 не называет day productive.

## 13. Fail-closed taxonomy

| Reason | Detection | Disposition | Batch | Retry |
|---|---|---|---:|---:|
| `MISSING_REQUIRED_FIELD` | record validation | `MISSING_REQUIRED_DATA_FAIL_CLOSED` | no | yes |
| `UNKNOWN_DOMAIN` | envelope validation | `INVALIDATED` | no | yes |
| `UNKNOWN_SOURCE_MODEL` | source model validation | `INVALIDATED` | no | yes |
| `SOURCE_STATUS_MISMATCH` | source status validation | `CONFLICT_FAIL_CLOSED` | no | yes |
| `REVIEW_CANDIDATE_MISSING` | Review input validation | `MISSING_REQUIRED_DATA_FAIL_CLOSED` | yes | yes |
| `REVIEW_UNCERTAINTY_COLLAPSED` | Review batch validation | `CONFLICT_FAIL_CLOSED` | yes | yes |
| `LEARN_LIMITATION_MISSING` | Learn input validation | `MISSING_REQUIRED_DATA_FAIL_CLOSED` | yes | yes |
| `LEARN_IDENTITY_AMBIGUOUS` | Learn identity validation | `AMBIGUOUS_FAIL_CLOSED` | no | yes |
| `DAY_AXIS_MISSING` | axis validation | `MISSING_REQUIRED_DATA_FAIL_CLOSED` | no | yes |
| `DAY_AXIS_CONFLICT` | axis relation validation | `CONFLICT_FAIL_CLOSED` | yes | yes |
| `DUPLICATE_RECORD_ID` | batch identity validation | `INVALIDATED` | yes | yes |
| `DUPLICATE_SOURCE_EVENT` | source-event validation | `INVALIDATED` | yes | yes |
| `UNIT_MISMATCH` | unit validation | `CONFLICT_FAIL_CLOSED` | yes | yes |
| `PROVENANCE_MISSING` | provenance validation | `MISSING_REQUIRED_DATA_FAIL_CLOSED` | no | yes |
| `REAL_DATA_FIELD_PRESENT` | privacy validation | `INVALIDATED` | yes | no |
| `CREATE_DOMAIN_PRESENT` | domain validation | `INVALIDATED` | yes | no |
| `NUMERIC_POLICY_PRESELECTED` | policy boundary | `INVALIDATED` | yes | no |
| `SOURCE_IDENTITY_CONFLICT` | source identity validation | `CONFLICT_FAIL_CLOSED` | yes | yes |

Каждый reason имеет stable `EXPLAIN-*` code. Missing candidate/timezone/day/unit/limitation никогда не получает silent default.

## 14. Provenance

Required provenance:

```text
source_contract_id
source_contract_version
source_candidate_model_id
source_stage_outcome
source_evidence_class
source_limitation_codes
synthetic_source_identity
transformation_contract_id
transformation_version
```

Evidence classes:

```text
REPOSITORY_CONFIRMED
REPORT_CONFIRMED
OWNER_DECISION
NOT_REVALIDATED
NOT_AVAILABLE
INCONCLUSIVE
REFERENCE_ONLY
```

Aggregate summaries не маркируются raw evidence. G4.2 не утверждает fresh G1/G2 bundle revalidation.

## 15. Synthetic persona descriptors

Сохраняются девять G4.1 classes:

```text
BEGINNER_HEAVY
MATURE_DECK
BALANCED
BACKLOG_RETURNER
LOW_VOLUME_CONSISTENT
INTENSIVE_LEARNER
ALTERNATING_INTENSIVE_LIGHT
PLANNED_REST_SCHEDULE
IRREGULAR_LEGITIMATE
```

Descriptor fields:

```text
persona_id
domain_mix_class
volume_class
regularity_class
backlog_class
rest_pattern_class
session_shape_class
day_axis_pattern_class
expected_risk_tags
required_invariant_coverage
```

Не определяются exact event sequences, counts, durations, expected XP или seed. Descriptor является synthetic workload metadata, а не real-user profile.

## 16. Deterministic fixture requirements

Frozen requirement IDs:

```text
FIXTURE-REVIEW-UNCERTAINTY-PARALLEL
FIXTURE-REVIEW-CANDIDATE-MISSING
FIXTURE-LEARN-LIMITATION-PRESERVED
FIXTURE-LEARN-IDENTITY-AMBIGUOUS
FIXTURE-SESSION-SPLIT-EQUIVALENCE
FIXTURE-ANKI-CALENDAR-DAY-DIVERGENCE
FIXTURE-TIMEZONE-CLOCK-MANIPULATION
FIXTURE-DUPLICATE-INPUT
FIXTURE-MISSING-PROVENANCE
FIXTURE-UNIT-MISMATCH
FIXTURE-BACKLOG-NOT-SOURCE
FIXTURE-NEW-MATERIAL-FLOOD-NOT-SOURCE
FIXTURE-PLANNED-REST-NEUTRAL
FIXTURE-REAL-DATA-REJECTED
FIXTURE-CREATE-DOMAIN-REJECTED
```

Каждый requirement содержит covered threats, invariants, personas, required input categories, expected disposition и deterministic replay requirement.

```text
exact numeric output: NOT_DEFINED
exact trace: NOT_DEFINED
execution: G4.3_OR_LATER
```

G4.2 не создаёт fixture files или event traces.

## 17. Threat / invariant coverage

Все 14 G4.1 threats и 28 invariants сохранены. Machine contract связывает:

```text
threat → validation rules → fixture requirements
invariant → typed records → validation rules → fixture requirements
```

Hard-gate failure не compensable. Weighted score отсутствует.

## 18. Non-rewardable surfaces

Сохраняются все 26 G4.1 categories, включая button selection, exposure, time/speed, session split/open, backlog/object counts, configuration, timezone/clock changes, planned rest, streak/Momentum/level values, imports, reset, raw events и idle time.

Они могут быть metadata/evidence context, но не positive contribution source.

## 19. Privacy and security

Разрешены только synthetic IDs/descriptors/requirements. Запрещены real card text, note fields, media, profile paths, usernames, tokens, raw revlog, identifiable history, real-user personas, remote AI, cloud upload и content fingerprints.

Не меняются loopback, token validation, sanitizer, media validation, action allowlists и frontend collection-access boundary.

## 20. Claims boundary

После G4.2 разрешено утверждать:

- typed input model определён;
- Review uncertainty сохранена;
- Learn limitation propagated;
- normalization interface shape определена;
- axes разделены;
- fail-closed dispositions определены;
- persona descriptors и fixture requirements заморожены;
- contract/schema validated;
- G4.3 entry определён;
- production surfaces не изменены.

Запрещены claims balanced/optimal, candidate superiority, correct ratio/XP/threshold/curve/formula, motivation/retention improvement, all-gaming prevention и production readiness.

## 21. Unresolved selections

```text
Review winner: NONE
Review candidate default: NONE
Review candidate averaging: PROHIBITED
Review/Learn ratio: NONE
normalized unit: NONE
normalized XP amount: NONE
daily cap: NONE
soft cap: NONE
diminishing function: NONE
productive-day threshold: NONE
level curve: NONE
level count: NONE
streak formula: NONE
rest quota: NONE
Momentum formula: NONE
recovery formula: NONE
candidate families: NOT_DEFINED
exact fixture traces: NOT_DEFINED
screening matrix: NOT_DEFINED
simulation seed: NONE
simulation results: NOT_AVAILABLE
production storage/API/UI: NOT_DESIGNED
```

## 22. G4.3 entry contract

```text
G4.3 — Candidate economy protocol and hypothesis design
status: NEXT / NOT STARTED
```

G4.3 обязана:

1. использовать frozen G4.2 typed records;
2. сохранить оба Review candidates;
3. сохранить Learn limitation;
4. определить normalization candidate families prospectively;
5. определить candidate conversion policies prospectively;
6. определить productive-day candidate policies prospectively;
7. определить level/streak/rest/Momentum/recovery candidate families prospectively;
8. определить hard gates до results;
9. определить metrics до results;
10. определить exact synthetic traces и matrix до execution;
11. определить Review-axis sensitivity analysis;
12. не использовать real-user data;
13. не менять production code;
14. не запускать screening до protocol publication.

G4.2 не создаёт candidate families, traces, matrix, simulation или results.

## 23. Production boundary

```text
production approved: false
production integration: PROHIBITED
runtime/dashboard/API changed: false
scheduler/FSRS/due dates changed: false
database/ledger changed: false
package/workflows/release changed: false
G4.3 started: false
simulation executed: false
```
