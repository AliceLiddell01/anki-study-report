# Gamification research documentation

## Current state

```text
G0: COMPLETE
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review XP research candidate: NONE

G2: COMPLETE
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended Learn XP research candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
selected candidate evidence status: CONFIRMATORY_INCONCLUSIVE

G3: DEFERRED / POST-MVP / NOT STARTED
G3 blocks G4/G5/G6: NO

G4: IN PROGRESS
G4.1: COMPLETE
G4.2: COMPLETE
G4.3: COMPLETE
candidate protocol: FROZEN_PRE_SCREENING
stage outcome: PROTOCOL_FROZEN
G4.4: NEXT / NOT STARTED
results: NOT_AVAILABLE
simulation: NOT_STARTED
production integration: PROHIBITED
```

The canonical `gamification` branch contains isolated research contracts, fixtures, simulator code, accepted synthetic evidence and bounded governance decisions. Research candidates and research outcomes are not production economies.

## Current G4 contracts

### G4.1 — core economy problem contract

- [Human core economy contract](core-economy-problem-contract.md)
- [Machine contract](../../research/gamification-sim/contracts/core-economy-problem-contract-v1.json)
- [Strict Draft 2020-12 schema](../../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json)
- [G4.1 closeout](../../roadmap/gamification/g4-core-economy-problem-contract.md)

G4.1 freezes the two-domain problem for `REVIEW_DOMAIN` and `LEARN_DOMAIN`, excludes `CREATE_DOMAIN`, preserves both Review candidates and the inconclusive Learn limitation, and selects no numeric economy policy.

### G4.2 — input normalization and uncertainty model

- [Human input/uncertainty model](core-economy-input-normalization-model.md)
- [Machine contract](../../research/gamification-sim/contracts/core-economy-input-normalization-v1.json)
- [Strict Draft 2020-12 schema](../../research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json)
- [G4.2 closeout](../../roadmap/gamification/g4-core-economy-input-normalization.md)

G4.2 freezes typed source and aggregation boundaries:

```text
REVIEW_DOMAIN_INPUT
LEARN_DOMAIN_INPUT
NORMALIZATION_INPUT
DOMAIN_CONTRIBUTION_RECORD
DAILY_AGGREGATION_INPUT
DAILY_AGGREGATION_RESULT_PLACEHOLDER
```

Review remains an explicit parallel uncertainty axis:

```text
axis: REVIEW_MODEL_AXIS_V1
members: P-STEP-ZERO; P-TAPER-ZERO-30D
selection: NONE
default: NONE
evaluation: PARALLEL_SEPARATE
averaging: PROHIBITED
```

Learn remains bounded by its source evidence:

```text
candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
status: CONFIRMATORY_INCONCLUSIVE
limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
confirmatory eligible: NO
production ready: NO
common economy XP: NO
```

Axes are explicitly separated as `SESSION`, `ANKI_DAY` and `CALENDAR_DAY`.

### G4.3 — candidate economy protocol and hypothesis design

- [Human candidate protocol](core-economy-candidate-protocol.md)
- [Machine candidate protocol](../../research/gamification-sim/contracts/core-economy-candidate-protocol-v1.json)
- [Candidate protocol schema](../../research/gamification-sim/schemas/core-economy-candidate-protocol-v1.schema.json)
- [Deterministic synthetic scenarios](../../research/gamification-sim/fixtures/core-economy-candidate-scenarios-v1.json)
- [Scenario schema](../../research/gamification-sim/schemas/core-economy-candidate-scenarios-v1.schema.json)
- [Dry screening matrix](../../research/gamification-sim/matrices/core-economy-screening-matrix-v1.json)
- [Matrix schema](../../research/gamification-sim/schemas/core-economy-screening-matrix-v1.schema.json)
- [G4.3 canonical closeout](../../roadmap/gamification/g4-core-economy-candidate-protocol.md)
- [G4.3 post-merge report](../../reports/research/g4-3-candidate-economy-protocol-closeout-2026-07-28.md)

Frozen state:

```text
owner principle: GRACEFUL_DEGRADATION_OVER_ABRUPT_CUTOFF
preferred research direction: TAPER / RECOVERY
abrupt uncertainty policy: RETAINED AS CONTROL
Review winner/default: NONE / NONE
Review averaging: PROHIBITED
Learn limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
primitive policies: 20
curated candidate bundles: 24
hypotheses: 24
non-compensable hard gates: 23
metrics: 19
deterministic scenarios: 40
matrix expected / unique: 762 / 762
matrix duplicates / missing / extra: 0 / 0 / 0
scenario digest: 9f53c8e6af181a0106a74f0bb52d1695a00e158a6ad15cb656c91bf6670881a3
matrix digest: 9f0ad95f8e99b3e25d19d859f88afa13a0b5b3b9efc99427facde336e146241c
```

The design rule is `CURATED_BOUNDED_FACTORIAL_DESIGN`; the full primitive Cartesian product is prohibited. A hard failure under one Review member cannot be hidden by averaging or by the other member.

G4.3 is prospective only:

```text
results: NOT_AVAILABLE
all matrix rows: NOT_RUN
screening executed: NO
simulation: NOT_STARTED
winner: NONE
production approved: NO
G4.4: NEXT / NOT STARTED
```

PR #166 merged the frozen protocol into `gamification` at merge commit `0d42e7bbee80b99de7e3369071c9a2dcdc6ba6bb`. This identity records publication, not a screening result.

## Current G2 contracts

### G2.1 — Learn XP problem contract

- [Learn XP problem contract](learn-xp-problem-contract.md)
- [Machine contract](../../research/gamification-sim/contracts/learn-xp-problem-contract-v1.json)
- [Schema](../../research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json)
- [G2.1 closeout](../../roadmap/gamification/g2-learn-xp-problem-contract.md)

### G2.2 — lifecycle and anti-farming model

- [Human lifecycle model](learn-xp-lifecycle-model.md)
- [Machine lifecycle model](../../research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json)
- [Lifecycle schema](../../research/gamification-sim/schemas/learn-xp-lifecycle-model-v1.schema.json)
- [Fixture schema](../../research/gamification-sim/schemas/learn-xp-lifecycle-fixture-v1.schema.json)
- [Fixture manifest](../../research/gamification-sim/fixtures/learn-xp-lifecycle-v1/manifest.json)
- [G2.2 closeout](../../roadmap/gamification/g2-learn-xp-lifecycle.md)

G2.2 defines seven states, 20 events, 12 transitions and a factorized `LearningEpisode<AchievementSubject>` identity model.

### G2.3–G2.6 — candidate evidence and decision

- [Human candidate protocol](learn-xp-candidate-protocol.md)
- [Machine candidate protocol](../../research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json)
- [Candidate schema](../../research/gamification-sim/schemas/learn-xp-candidate-protocol-v1.schema.json)
- [G2.3 closeout](../../roadmap/gamification/g2-learn-xp-candidate-protocol.md)
- [Bounded screening technical reference](learn-xp-bounded-screening.md)
- [G2.4 closeout](../../roadmap/gamification/g2-learn-xp-bounded-screening.md)
- [Confirmatory protocol](learn-xp-confirmatory-protocol.md)
- [G2.5 closeout](../../roadmap/gamification/g2-learn-xp-confirmatory-evidence.md)
- [G2.6 decision](../../roadmap/gamification/g2-learn-xp-decision.md)

G2 closes with `RECOMMEND_LEARN_XP_RESEARCH_MODEL`. The selected bounded input remains `CONFIRMATORY_INCONCLUSIVE`; recommendation does not mean scientific superiority, confirmatory eligibility or production approval.

## Current G1 contracts

- [Review XP cross-horizon cycling problem](review-xp-cycling-problem.md)
- [G1.1 problem and gate freeze](../../roadmap/gamification/g1-problem-gate-freeze.md)
- [G1.1 contract correction](../../roadmap/gamification/g1-contract-correction.md)
- [G1.2 root-cause attribution](../../roadmap/gamification/g1-root-cause-attribution.md)
- [G1.2a attribution correction](../../roadmap/gamification/g1-root-cause-attribution-correction.md)
- [Review candidate protocol](review-xp-candidate-protocol.md)
- [G1.3 closeout](../../roadmap/gamification/g1-candidate-protocol.md)
- [G1.4 bounded screening](../../roadmap/gamification/g1-bounded-screening.md)
- [Review confirmatory protocol](review-xp-confirmatory-protocol.md)
- [G1.5 confirmatory evidence](../../roadmap/gamification/g1-confirmatory-evidence.md)
- [G1.6 decision](../../roadmap/gamification/g1-review-xp-decision.md)

G1 closes with `DEFER_REVIEW_MODEL`. `P-STEP-ZERO` and `P-TAPER-ZERO-30D` remain confirmatory-eligible, not selected and not falsified.

## Review research references

- [Review event taxonomy](anki-review-event-taxonomy.md)
- [Review reward model](anki-review-reward-model.md)
- [Review abuse model](anki-review-abuse-model.md)
- [Review session and Anki-day aggregation](anki-review-session-and-day.md)
- [Review simulation specification](anki-review-simulation-spec.md)

These are references for terminology, research discipline and protected invariants. Their formulas, candidates and matrices do not determine G4 normalization automatically.

## Evidence and privacy boundary

G1 evidence is synthetic. G2 retains its prospective/evidence/governance chronology. G4.1 freezes the two-domain problem; G4.2 freezes typed input, uncertainty and axis boundaries; G4.3 freezes candidate families and deterministic dry screening inputs before any result access.

No real card text, note fields, media, profile paths, usernames, tokens, raw revlog or identifiable learning history enter G4 research artifacts.

## Production integration boundary

No production add-on, dashboard, payload, API, scheduler, FSRS, database, workflow, package, release or telemetry integration is approved. G4.3 is a research protocol freeze; G4.4, screening and simulation remain not started. Research assets remain outside Fast CI and `.ankiaddon` contents.

## G4.3 v2 corrective protocol

- [Human corrective protocol](core-economy-candidate-protocol-v2.md)
- [Machine protocol](../../research/gamification-sim/contracts/core-economy-candidate-protocol-v2.json)
- [Evaluation pipeline](../../research/gamification-sim/contracts/core-economy-evaluation-pipeline-v2.json)
- [Scenario registry](../../research/gamification-sim/fixtures/core-economy-candidate-scenarios-v2.json)
- [Dry matrix](../../research/gamification-sim/matrices/core-economy-screening-matrix-v2.json)
- [Focused validator/tests](../../research/gamification-sim/src/gamification_sim/core_economy_protocol_v2.py)

```text
G4.3 v1: SUPERSEDED_PRE_EXECUTION
G4.3 v2: FROZEN_PRE_SCREENING
scenarios / matrix rows: 41 / 864
results: NOT_AVAILABLE
G4.4: NEXT / NOT STARTED
production: PROHIBITED
```
