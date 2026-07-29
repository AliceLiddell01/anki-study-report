# Core Gamification Economy — corrective candidate protocol G4.3 v2

**Contract ID:** `core-economy-candidate-protocol`
**Version:** `2`
**Stage:** `G4.3 — corrective republication before screening`
**Status:** `FROZEN_PRE_SCREENING`
**Results:** `NOT_AVAILABLE`
**G4.4:** `NEXT / NOT STARTED`
**Production integration:** `PROHIBITED`

```text
G4.3 v1: `SUPERSEDED_PRE_EXECUTION`
G4.3 v1 results: `NOT_AVAILABLE`
G4.3 v2: `FROZEN_PRE_SCREENING`
screening: `NOT_STARTED`
simulation: `NOT_STARTED`
```

Normative artifacts:

- [`core-economy-candidate-protocol-v2.json`](../../research/gamification-sim/contracts/core-economy-candidate-protocol-v2.json)
- [`core-economy-candidate-protocol-v2.schema.json`](../../research/gamification-sim/schemas/core-economy-candidate-protocol-v2.schema.json)
- [`core-economy-evaluation-pipeline-v2.json`](../../research/gamification-sim/contracts/core-economy-evaluation-pipeline-v2.json)
- [`core-economy-evaluation-pipeline-v2.schema.json`](../../research/gamification-sim/schemas/core-economy-evaluation-pipeline-v2.schema.json)
- [`core-economy-candidate-scenarios-v2.json`](../../research/gamification-sim/fixtures/core-economy-candidate-scenarios-v2.json)
- [`core-economy-candidate-scenarios-v2.schema.json`](../../research/gamification-sim/schemas/core-economy-candidate-scenarios-v2.schema.json)
- [`core-economy-screening-matrix-v2.json`](../../research/gamification-sim/matrices/core-economy-screening-matrix-v2.json)
- [`core-economy-screening-matrix-v2.schema.json`](../../research/gamification-sim/schemas/core-economy-screening-matrix-v2.schema.json)
- [`core_economy_protocol_v2.py`](../../research/gamification-sim/src/gamification_sim/core_economy_protocol_v2.py)
- [`test_core_economy_protocol_v2.py`](../../research/gamification-sim/tests/test_core_economy_protocol_v2.py)
- [negative corpus](../../research/gamification-sim/fixtures/core-economy-candidate-protocol-v2-negative/manifest.json)

## 1. Corrective boundary

G4.3 v1 remains an immutable historical publication. No v1 contract, schema,
scenario or matrix byte is rewritten. Because all v1 matrix rows remain `NOT_RUN`,
no result was accessed and G4.4 was not started, the logical defects are corrected
prospectively in version 2 without mixing evidence.

The republication preserves:

```text
initial domains: REVIEW_DOMAIN; LEARN_DOMAIN
excluded domain: CREATE_DOMAIN
Review axis: REVIEW_MODEL_AXIS_V1
Review members: P-STEP-ZERO; P-TAPER-ZERO-30D
Review selection/default/winner: NONE / NONE / NONE
Review evaluation: PARALLEL_SEPARATE
Review averaging: PROHIBITED
Learn candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
Learn limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
Learn source total: 1.0 LRU
production: PROHIBITED
```

The G4.2 chronology is classified as
`STALE_CLOSEOUT_IDENTITY_LEDGER_CORRECTION`; G4.2 machine semantics are unchanged.

## 2. False-positive correction

Frozen Review decomposition remains:

```text
VERIFIED_BASE = AttemptCredit + Pass * OutcomeCredit + Pass * NeutralContextCredit
POSITIVE_CONTEXT = max(ContextCredit - NeutralContextCredit, 0)
NEGATIVE_CONTEXT = min(ContextCredit - NeutralContextCredit, 0)

AttemptCredit = 0.25
OutcomeCredit = 0.65
NeutralContextCredit = 0.10
ordinary successful Review = 1.00 Review Unit
maximum successful Review ~= 1.32 Review Unit
```

The v1 total-denominator metric is superseded. v2 freezes two separate metrics:

```text
M-FALSE-POSITIVE-CONTEXT-LOSS
= lost_positive_context / max(matched_positive_context, 1e-12)

M-FALSE-POSITIVE-TOTAL-IMMEDIATE-LOSS
= lost_total_contribution / max(matched_total_contribution, 1e-12)
```

Primary hard gate:

```text
HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED
recommendation-eligible contextual loss ratio <= 0.25
```

The maximum-context trace fixes `verified_base=1.00`,
`matched_positive_context=0.32`, `matched_total=1.32`. Therefore:

```text
U-ABRUPT-CUTOFF-CONTROL: context loss = 1.00 -> CONTROL_EXPECTED_FAIL
U-FIXED-STEPPED-TAPER first step: context loss = 0.25 -> PASS boundary
```

The abrupt policy is `control_only=true` and
`recommendation_eligible=false`. The stepped policy is deliberately not named
`LINEAR`.

## 3. One expected-outcome source

Scenario artifacts contain only candidate-independent trace semantics:

```text
applicable_gate_ids
metric_ids
expected_validation_disposition
ordered synthetic inputs
replay directions
```

Candidate-specific expected gate outcomes exist only in matrix-selected gate
profiles. The semantic validator rejects conflicting expectations for the same
typed run identity.

## 4. Cross-domain conversion and fairness

The conversion axis contains three prospectively frozen contrasts:

| Candidate | Review weight | Learn weight | Eligibility |
|---|---:|---:|---|
| `X-EQUALIZED-1_0-1_0` | 1.0 | 1.0 | recommendation eligible |
| `X-LEARN-LEANING-0_8-1_2` | 0.8 | 1.2 | recommendation eligible sensitivity |
| `X-REVIEW-LEANING-1_2-0_8-CONTROL` | 1.2 | 0.8 | control only |

Every mapping emits separate `review_component`, `learn_component` and
`total_npu`. `NORMALIZED_PROGRESSION_UNIT` is a research comparison unit, not
production pricing or a claim of equal human value.

Non-compensable gates:

```text
HG-NO-CROSS-DOMAIN-CROWDOUT
HG-CROSS-DOMAIN-DECOMPOSITION-PRESERVED
HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED
```

Required metrics:

```text
M-REVIEW-MARGINAL-CONTRIBUTION
M-LEARN-MARGINAL-CONTRIBUTION
M-DOMAIN-CROWDOUT
M-DOMAIN-SHARE
M-CROSS-DOMAIN-SENSITIVITY
```

## 5. Exact evaluation pipeline

The machine pipeline contains exactly 17 typed steps:

1. source record validation;
2. source-model transition;
3. verified-base/context decomposition;
4. uncertainty-state read;
5. uncertainty multiplier application to positive context only;
6. component-wise domain normalization;
7. per-domain aggregation;
8. per-domain daily bounding;
9. cross-domain conversion;
10. optional final global envelope for explicit controls only;
11. productive-day classification;
12. streak/planned-rest transition;
13. Momentum transition;
14. recovery transition;
15. cumulative NPU progression;
16. level mapping;
17. explanation/decomposition emission.

Each step freezes input/output type, candidate dimension, decimal precision,
state read/write timing, missing-data behavior, fail-closed reason and reason
codes.

Nonlinear operator order is fixed as:

```text
NORMALIZE_COMPONENTS_SEPARATELY_AFTER_UNCERTAINTY

normalize(verified_base)
+ normalize(taper(positive_context))
+ normalize(negative_context)
```

The following aggregate-first behavior is prohibited:

```text
normalize(verified_base + positive_context)
then taper the normalized aggregate
```

## 6. Daily scope and scale

Recommendation-eligible daily policies use:

```text
PER_DOMAIN_THEN_COMBINE
```

Candidates:

- `D-PER-DOMAIN-PIECEWISE-MEDIUM` preserves the first 10 Review NPU and first 2 Learn NPU, then applies explicit diminishing bands while retaining a positive extreme-volume tail.
- `D-PER-DOMAIN-SQRT-HIGH` preserves the first 30 Review NPU and first 5 Learn NPU, then applies bounded square-root compression.
- `D-COMBINED-HARD-6-CONTROL` applies a proportional global cap only as a control and is expected to fail marginality/crowdout gates at saturation.

Synthetic workload scenarios cover:

```text
Reviews: 5 / 10 / 30 / 100 / 300
Learn confirmations: 1 / 5 / 10 / 30
```

Raw event count is not independently rewardable. The matrix also covers session
splitting, mixed-day cap boundaries and level interactions. Level candidates
consume `NORMALIZED_PROGRESSION_UNIT`; v1 absolute CRU level curves are not
silently reused.

## 7. Curated bounded factorial design

Primitive policies: **19**
Candidate bundles: **21**
Hypotheses: **20**
Hard gates: **29**
Metrics: **22**

The design includes isolated pair coverage for:

```text
NORMALIZATION_X_DAILY_BOUNDING
NORMALIZATION_X_PRODUCTIVE_DAY
NORMALIZATION_X_LEVEL_CURVE
DAILY_BOUNDING_X_CROSS_DOMAIN_CONVERSION
DAILY_BOUNDING_X_DOMAIN_CROWDOUT
```

All non-paired dimensions are held at the declared baseline. Integrated bundles
remain end-to-end checks and are not the sole basis for causal attribution. A
full Cartesian product and adaptive post-result rows are prohibited.

## 8. Scenario registry and dry matrix

Scenarios: **41**
Matrix rows: **864**

The scenario registry contains only synthetic records and includes maximum
contextual false positive, zero-context denominator, abrupt/stepped/confidence
recovery, cross-domain marginality, Review-heavy/Learn-heavy crowdout, per-domain
and combined-cap boundaries, required volume scales, normalization interactions,
operator-order distinction, rounding, planned rest, Momentum, recovery and
replay.

The matrix is generated by committed code. Every row contains:

```text
row_id
protocol_version = 2
pipeline_version = 2
candidate_bundle_id
scenario_id
Review member or NOT_APPLICABLE
replay direction
replica = 0
seed = null
gate_profile_id
metric_set
result_status = NOT_RUN
result = NOT_AVAILABLE
```

Expected / unique / missing / extra:

```text
864 / 864 / 0 / 0
```

## 9. Validation and reproducibility

Canonical serialization:

```text
UTF-8
no BOM
sorted object keys
compact separators
newline terminated
duplicate keys rejected
NaN/Infinity rejected
```

The committed validator performs Draft 2020-12 schema self-check, strict artifact
validation, semantic reference validation, exact row regeneration, row-ID and
digest recomputation, Review/Learn boundary checks, no-results enforcement,
v1/v2 separation, human/machine parity and execution of the 40-sample negative
corpus.

Frozen identities are stored in each machine artifact. G4.4 may execute only the
exact publication commit and matching protocol, pipeline, scenario and matrix
digests.

## 10. Claims and production boundary

This protocol does not run screening or simulation, select a winner, approve a
Review default, rank Review members, upgrade Learn evidence, choose production
pricing, claim learning benefit, change scheduler/FSRS/due dates, access real
user data or modify production code.

```text
results: NOT_AVAILABLE
G4.4: NEXT / NOT STARTED
simulation: NOT_STARTED
Review winner: NONE
production: PROHIBITED
```


## 11. Frozen source-contract continuity

The v2 registry reuses the exact frozen G4.1/G4.2 coverage identities rather than
introducing replacement persona, threat or invariant namespaces.

```text
personas: 9 / 9
threats: 14 / 14
invariants: 28 / 28
G4.1 contract blob: dda1336328df7e79bc5ba1978a102faf5ca40e14
G4.2 contract blob: 0cf1bbb6f3f088d48b4c78bcc37145dacc8cebc5
```

The committed 40-sample negative corpus refreshes all dependent artifact digests
and derived row identities for semantic mutations, then requires the prospectively
declared error code. Explicit digest and row-ID samples alone preserve their
corrupted identities. Therefore a negative sample cannot pass merely because an
unrelated stale digest or stale derived row ID fails first.

Cross-artifact protocol, pipeline, scenario, matrix and row digest references are
validated in addition to each artifact self-digest.
