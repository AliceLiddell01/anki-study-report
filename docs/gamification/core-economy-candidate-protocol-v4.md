# G4.3 v4 — replacement-протокол core economy

**Stage:** `G4.3`
**Status:** `FROZEN_PRE_SCREENING`
**Scope:** только deterministic synthetic research
**Production integration:** `PROHIBITED`

```text
G4.3 v1: `SUPERSEDED_PRE_EXECUTION`
G4.3 v1 results: `NOT_AVAILABLE`
G4.3 v2: `SUPERSEDED_PRE_EXECUTION`
G4.3 v2 results: `NOT_AVAILABLE`
G4.3 v3: `INVALIDATED_AFTER_SUBSTANTIVE_DEFECT`
G4.3 v3 results: `INVALIDATED_NOT_DECISION_EVIDENCE`
G4.3 v4: `FROZEN_PRE_SCREENING`
results accessed before republication: true
G4.4: NOT STARTED
```

v4 является replacement republication после invalidated v3 run. Исторические v1/v2/v3 machine artifacts, generator, validator и tests остаются неизменными и проверяются по SHA-256. Result set v3 `7501d5f3248b468dec6d8c338ca019d0543400b7696eb77b24dbb042d2448612` не является decision evidence. Этот документ не содержит v4 screening results и не выбирает winner.

## Источники

G4 использует только замороженные research contracts:

- G4.1 `core-economy-problem-contract` v1;
- G4.2 `core-economy-input-normalization` v1;
- G1 `review-xp-candidate-protocol` v1 и `review_candidate_mechanisms.py`;
- G2 `learn-xp-candidate-protocol` v1, `learn-xp-confirmatory-protocol` v1 и `learn_reward_allocation.py`.

Review axis:

```text
axis: REVIEW_MODEL_AXIS_V1
members: P-STEP-ZERO; P-TAPER-ZERO-30D
selection: NONE
default: NONE
winner: NONE
evaluation: PARALLEL_SEPARATE
averaging: PROHIBITED
```

Learn input:

```text
candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
status: CONFIRMATORY_INCONCLUSIVE
limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
source unit: LRU
frozen source total: 1.0
common economy XP: false
```

`CREATE_DOMAIN` исключён. G3, G5 и G6 не начаты.

## Frozen inventory

```text
Primitive policies: **19**
Candidate bundles: **21**
Hypotheses: **20**
Hard gates: **30**
Metrics: **22**
Pipeline steps: **17**
Scenarios: **52**
Matrix rows: **1275**
Negative samples: **18**
Personas: **9**
Threats: **14**
Invariants: **28**
```

Matrix остаётся dry artifact:

```text
result_status: NOT_RUN
results: NOT_AVAILABLE
screening_executed: false
simulation_started: false
g4_4_started: false
production_approved: false
```

## Исправления v4

v4 устраняет три дефекта, обнаруженные только после первого полного v3 result access:

- каждый applicable gate теперь имеет все `required_metric_ids` в той же row;
- expected abrupt-control outcomes вычисляются из фактической потери на uncertainty-bearing events, а не из одного наличия positive context;
- marginal probes выполняются ниже combined-cap boundary, если scenario сам не насыщает control.

### Uncertainty state machine

`U-CONFIDENCE-TAPER-RECOVERY` содержит machine-readable states:

```text
NORMAL
WATCH
RESTRICTED
RECOVERING
```

и signals:

```text
NORMAL
ISOLATED_ANOMALY
CONFLICT
MISSING
```

Каждое правило фиксирует:

```text
current_state
signal
recent_evidence_window
predicate
next_state
applied_multiplier
state_read_timing
multiplier_apply_timing
state_write_timing
reason_code
missing_evidence_behavior
```

State читается до текущего event, multiplier применяется только к `POSITIVE_CONTEXT`, state записывается после contribution. `VERIFIED_BASE` и `NEGATIVE_CONTEXT` не меняются. Missing signal удерживает state и использует multiplier текущего state. Unknown state/signal, NaN, infinity и отрицательные contributions отклоняются.

Нет retroactive progression mutation, XP debt, user guilt state или recovery bonus.

### Исполняемый Review source

G4 вызывает точную G1 semantics через `memory_gain_multiplier()`:

```text
P-STEP-ZERO:
day < 60  -> 1.0
day >= 60 -> 0.0

P-TAPER-ZERO-30D:
day <= 60     -> 1.0
60 < day < 90 -> linear 1.0 .. 0.0
day >= 90     -> 0.0
```

Frozen boundary grid:

```text
59
60
61
75
89
90
91
```

Обе модели получают один raw source event. Matrix row содержит member-specific `review_source_trace`; скрытый default и averaging отсутствуют.

### Expected outcomes

Matrix является единственным source of truth. Каждое ожидание вычисляется из:

```text
candidate_bundle_id
scenario_id
review_member
replay_direction
gate_id
```

Rule: `EXPECTED-OUTCOME-CANDIDATE-SCENARIO-GATE-V1`.

```text
abrupt + contextual loss ratio > 0.25 -> CONTROL_EXPECTED_FAIL
abrupt + cumulative loss ratio > 0.20 -> CONTROL_EXPECTED_FAIL
abrupt without a predicate violation -> PASS
combined cap + both positive domains + pre-cap total > 6 -> exact crowdout/marginality CONTROL_EXPECTED_FAIL
combined cap + non-differentiable normal/intensive probe -> CONTROL_EXPECTED_FAIL
combined cap without per-domain finite output caps -> CONTROL_EXPECTED_FAIL
otherwise -> PASS
```

Ожидание содержит typed predicate AST и reason code. Post-result mutation запрещена.

### Cumulative false-positive loss

`M-FALSE-POSITIVE-CUMULATIVE-LOSS` выполняется на:

- recovery trace;
- repeated-conflict trace;
- matched multi-day legitimate trace.

Non-compensable gate:

```text
HG-FALSE-POSITIVE-CUMULATIVE-HARM-BOUNDED
threshold: <= 0.20
missing behavior: FAIL_CLOSED
```

Однодневный PASS не компенсирует чрезмерную cumulative legitimate loss.

### Daily bounded semantics

`D-PER-DOMAIN-BOUNDED-MEDIUM` использует конечные per-domain caps:

```text
Review input cap: 100
Review output cap: 34
Learn input cap: 30
Learn output cap: 10
tail multiplier: 0
```

Stress traces `1_000`, `10_000` и `1_000_000` обязаны давать те же конечные caps. Это prospective research bound, а не production pricing claim.

### Marginality

`HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED` требует обе metrics:

```text
M-REVIEW-MARGINAL-CONTRIBUTION
M-LEARN-MARGINAL-CONTRIBUTION
```

Combined-cap control ожидаемо показывает crowdout только на exact saturation predicate. Failed hard gate не компенсируется другим metric.

### Exact coverage

Semantic validator проверяет exact set equality и referential integrity для:

- candidates;
- bundles;
- hypotheses;
- hard gates;
- metrics;
- scenarios;
- Review members;
- personas;
- threats;
- invariants;
- replay directions;
- required interactions;
- reason codes.

Counts без identity coverage недостаточны.

## Typed pipeline

Operator order:

```text
NORMALIZE_COMPONENTS_SEPARATELY_AFTER_UNCERTAINTY
```

Запрещённый порядок:

```text
normalize(verified_base + positive_context) then taper normalized aggregate
```

`VERIFIED_BASE`, tapered `POSITIVE_CONTEXT` и `NEGATIVE_CONTEXT` нормализуются отдельно. Rounding — `ROUND_HALF_EVEN`, 12 decimal places, на output каждого pipeline step.

## Metrics и gates

`M-FALSE-POSITIVE-CONTEXT-LOSS` использует denominator positive context:

```text
lost_positive_context / max(matched_positive_context, epsilon)
```

`M-FALSE-POSITIVE-CUMULATIVE-LOSS`:

```text
sum(normal_path - candidate_path) / max(sum(normal_path), epsilon)
```

Каждый hard gate:

- `non_compensable: true`;
- имеет `required_metric_ids`;
- имеет typed `predicate_ast`;
- использует `FAIL_CLOSED` при missing evidence.

Weighted overall score отсутствует.

## Generated artifacts

```text
research/gamification-sim/contracts/core-economy-candidate-protocol-v4.json
research/gamification-sim/contracts/core-economy-evaluation-pipeline-v4.json
research/gamification-sim/fixtures/core-economy-candidate-scenarios-v4.json
research/gamification-sim/matrices/core-economy-screening-matrix-v4.json
research/gamification-sim/schemas/core-economy-candidate-protocol-v4.schema.json
research/gamification-sim/schemas/core-economy-evaluation-pipeline-v4.schema.json
research/gamification-sim/schemas/core-economy-candidate-scenarios-v4.schema.json
research/gamification-sim/schemas/core-economy-screening-matrix-v4.schema.json
research/gamification-sim/fixtures/core-economy-candidate-protocol-v4-negative/manifest.json
```

Generator:

```text
core-economy-protocol-v4-generator-1
```

Validator:

```text
core-economy-protocol-v4-validator-1
```

Generated JSON и schemas не редактируются вручную.

## Frozen digests

```text
protocol: a6f8faf819e7d4a7c3d5ffd73ad82775642020faa019584b823e20ad3f2b18cd
pipeline: f49169b3e91e04e781819bea33b5c86778b981e17a27c954b0ed7295b387af62
scenarios: fabd2cb9934953987cf6b64a6e34d070c3c1d26ef2d4f21641cfe5649cf6443d
matrix: 6c640a17643ac83c09fe56276072930152baa07f46147ab76c36b7f2b8160f67
```

Publication commit SHA фиксируется после создания отдельного Git checkpoint и затем используется G4.4 result manifest. До этого commit comparative screening и result access запрещены.

## Validation

Обязательный pre-screening command:

```powershell
$env:PYTHONPATH = "research/gamification-sim/src"
node scripts/run_python.mjs -m gamification_sim.core_economy_protocol_v4 --research-root research/gamification-sim --repository-root . --regenerate --validate --check-byte-identical
node scripts/run_python.mjs -m pytest research/gamification-sim/tests/test_core_economy_protocol_v4.py -q
```

Validation включает strict duplicate-key-safe parse, Draft 2020-12 schema self-check, artifact validation, semantic validation, negative corpus, byte-identical regeneration, exact inventory coverage, gate-to-metric row linkage, source continuity, historical v1/v2/v3 immutability и no-results enforcement.

## Production boundary

```text
real user data: prohibited
add-on runtime imports: prohibited
scheduler / FSRS / due dates: unchanged
dashboard / API / database: unchanged
Fast CI / package inclusion: absent
production approval: false
production integration: false
```
