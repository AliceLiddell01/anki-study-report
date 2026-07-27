# Gamification research simulator and contracts

## Status

```text
G0 current evidence: REPRODUCED
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review XP research candidate: NONE
G2: COMPLETE
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended Learn XP research candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
G3: DEFERRED / POST-MVP / NOT STARTED
G4: IN PROGRESS
G4.1: COMPLETE
core economy contract: FROZEN_PRE_NORMALIZATION_ANALYSIS
G4.2: NEXT / NOT STARTED
production integration: PROHIBITED
```

The package is isolated under `research/gamification-sim/`. It has no production imports, root dependency changes, Fast CI/package/release integration, real Anki profile data, collection data or tokens.

## Structure

```text
configs/       bounded current inputs
contracts/     versioned research contracts
evidence/      bounded committed evidence where allowed
fixtures/      deterministic synthetic corpus
personas/      synthetic workload personas
scenarios/     ordinary, edge, control, abuse and regression cases
schemas/       active strict schemas
src/           Python research package
tests/         Python research tests
rust-oracle/   isolated Rust implementation
```

## G4.1 core economy contract artifacts

- [Machine contract](contracts/core-economy-problem-contract-v1.json)
- [Strict Draft 2020-12 schema](schemas/core-economy-problem-contract-v1.schema.json)
- [Human contract](../../docs/gamification/core-economy-problem-contract.md)
- [G4.1 closeout](../../roadmap/gamification/g4-core-economy-problem-contract.md)

Frozen G4.1 state:

```text
contract_id: core-economy-problem-contract
version: 1
status: FROZEN_PRE_NORMALIZATION_ANALYSIS
G3: DEFERRED_POST_MVP_NOT_STARTED
G3 blocks G4/G5/G6: false
initial domains: REVIEW_DOMAIN; LEARN_DOMAIN
excluded domain: CREATE_DOMAIN
Review winner: NONE
Learn candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
terminology: 30
personas: 9
threats: 14
invariants: 28
allowed outcomes: 3
G4.2 requirements: 14
G4.2 started: false
production approved: false
```

The machine contract preserves `P-STEP-ZERO` and `P-TAPER-ZERO-30D` as an explicit Review uncertainty axis. It preserves the Learn identity limitation `DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE`. It selects no conversion ratio, normalized XP, productive-day threshold, level curve, streak, Momentum or recovery formula.

G4.1 adds no evaluator, CLI command, candidate registry, matrix, fixture trace or simulation. Its strict schema freezes the exact registries and rejects selected numeric/production state.

## G2.1 Learn XP artifacts

- [Machine problem contract](contracts/learn-xp-problem-contract-v1.json)
- [Strict Draft 2020-12 schema](schemas/learn-xp-problem-contract-v1.schema.json)
- [Human problem contract](../../docs/gamification/learn-xp-problem-contract.md)
- [G2.1 closeout](../../roadmap/gamification/g2-learn-xp-problem-contract.md)

G2.1 freezes problem/terminology, scheduler/reward boundary, four identity candidates, pending/confirmation minimum requirements, six anti-farming threat families, 19 invariants, privacy/claims boundaries and three final outcomes.

## G2.2 Learn XP lifecycle artifacts

- [Machine lifecycle model](contracts/learn-xp-lifecycle-model-v1.json)
- [Lifecycle model schema](schemas/learn-xp-lifecycle-model-v1.schema.json)
- [Lifecycle fixture schema](schemas/learn-xp-lifecycle-fixture-v1.schema.json)
- [Human lifecycle model](../../docs/gamification/learn-xp-lifecycle-model.md)
- [Fixture manifest](fixtures/learn-xp-lifecycle-v1/manifest.json)
- [Research-only evaluator](src/gamification_sim/learn_lifecycle.py)
- [Focused tests](tests/test_learn_lifecycle.py)
- [G2.2 closeout](../../roadmap/gamification/g2-learn-xp-lifecycle.md)

```text
model status: FROZEN_PRE_CANDIDATE_DESIGN
states / events / transitions: 7 / 20 / 12
identity architecture: LearningEpisode<AchievementSubject>
fixtures / threats / invariants: 23 / 6 / 19
```

## G2.3 Learn XP candidate protocol artifacts

- [Machine candidate protocol](contracts/learn-xp-candidate-protocol-v1.json)
- [Strict Draft 2020-12 schema](schemas/learn-xp-candidate-protocol-v1.schema.json)
- [Human candidate protocol](../../docs/gamification/learn-xp-candidate-protocol.md)
- [Dry matrix generator](src/gamification_sim/learn_candidate_protocol.py)
- [Focused protocol tests](tests/test_learn_candidate_protocol.py)
- [G2.3 closeout](../../roadmap/gamification/g2-learn-xp-candidate-protocol.md)

```text
protocol status: FROZEN_PRE_SCREENING_IMPLEMENTATION
families / parameterizations: 2 / 4
subject strategies / delay policies: 2 / 2
candidates / references: 8 / 2
hypotheses / gates / metrics: 5 / 23 / 14
expected units: 340
```

## G2.4 Learn XP bounded-screening artifacts

- [Allocation evaluator](src/gamification_sim/learn_reward_allocation.py)
- [Bounded screening harness and detached validator](src/gamification_sim/learn_bounded_screening.py)
- [Strict evidence schema](schemas/learn-xp-bounded-screening-evidence-v1.schema.json)
- [Focused tests](tests/test_learn_bounded_screening.py)
- [Technical reference](../../docs/gamification/learn-xp-bounded-screening.md)
- [G2.4 closeout](../../roadmap/gamification/g2-learn-xp-bounded-screening.md)

The valid replacement run completed `340/340` unique units with detached validation and byte-identical reproduction. Family survivors are `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` and `C-PENDING-SPLIT-D1-NOTE-SIBLING`.

## G2.5 Learn XP confirmatory artifacts

- [Machine confirmatory protocol](contracts/learn-xp-confirmatory-protocol-v1.json)
- [Protocol schema](schemas/learn-xp-confirmatory-protocol-v1.schema.json)
- [Evidence schema](schemas/learn-xp-confirmatory-evidence-v1.schema.json)
- [Human confirmatory protocol](../../docs/gamification/learn-xp-confirmatory-protocol.md)
- [Confirmatory harness and detached validator](src/gamification_sim/learn_confirmatory.py)
- [Focused tests](tests/test_learn_confirmatory.py)
- [Confirmatory closeout](../../roadmap/gamification/g2-learn-xp-confirmatory-evidence.md)

The matrix completed `216/216/216`. Both survivors remain `CONFIRMATORY_INCONCLUSIVE` because the disposable Anki identity probe was unavailable; reference is `REFERENCE_ONLY`.

## G2.6 final Learn XP decision

- [Final decision and G2 closeout](../../roadmap/gamification/g2-learn-xp-decision.md)

```text
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
decision basis: MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE
```

The recommendation is not confirmatory eligibility, human-learning evidence or production approval.

## Current G1 artifacts

- [G1.1 diagnostic contract](contracts/review-cycling-diagnostic-v1.json)
- [G1.1 schema](schemas/review-cycling-diagnostic-v1.schema.json)
- [G1.2a evidence](evidence/g1.2-root-cause-attribution-v1.json)
- [G1.3 candidate protocol](contracts/review-xp-candidate-protocol-v1.json)
- [G1.3 protocol schema](schemas/review-xp-candidate-protocol-v1.schema.json)
- [Human protocol](../../docs/gamification/review-xp-candidate-protocol.md)
- [G1.3 report](../../roadmap/gamification/g1-candidate-protocol.md)
- [G1.4 technical reference](../../docs/gamification/review-xp-bounded-screening.md)
- [G1.4 full report](../../roadmap/gamification/g1-bounded-screening.md)
- [G1.5 machine protocol](contracts/review-xp-confirmatory-protocol-v1.json)
- [G1.5 strict schema](schemas/review-xp-confirmatory-protocol-v1.schema.json)
- [G1.5 human protocol](../../docs/gamification/review-xp-confirmatory-protocol.md)
- [G1.5 closeout](../../roadmap/gamification/g1-confirmatory-evidence.md)
- [G1.6 decision and G1 closeout](../../roadmap/gamification/g1-review-xp-decision.md)

G1.4 retained `P-STEP-ZERO` and `P-TAPER-ZERO-30D`. G1.5 marked both `CONFIRMATORY_ELIGIBLE`; G1.6 selected no winner and closed G1 with `DEFER_REVIEW_MODEL`.

## Available command surface

```text
validate-bounded-screening
run-bounded-screening
validate-confirmatory-protocol
validate-confirmatory-evidence
run-confirmatory
validate-learn-xp-screening
run-learn-xp-screening
validate-learn-xp-screening-evidence
validate-learn-xp-confirmatory
run-learn-xp-confirmatory
validate-learn-xp-confirmatory-evidence
```

G4.1 adds no executable command. Existing G1/G2 commands remain historical research-only surfaces.

## Evidence and production boundary

G0.7, G1.2a, G1.4/G1.5 and G2.4/G2.5 are synthetic evidence. G4.1 records a prospective problem contract and owner decision without adding evidence or changing frozen G1/G2 outcomes.

Research artifacts are not part of the add-on runtime, dashboard, `.ankiaddon`, Fast CI or release pipeline. Generated outputs, environments, caches, coverage, build/dist and `rust-oracle/target/` remain untracked.

```text
G4.2: NEXT / NOT STARTED
production approved: NO
production integration: PROHIBITED
```
