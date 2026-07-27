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
G3: DEFERRED / POST-MVP / NOT STARTED
G3 blocks G4/G5/G6: NO
G4: IN PROGRESS
G4.1: COMPLETE
core economy contract: FROZEN_PRE_NORMALIZATION_ANALYSIS
G4.2: NEXT / NOT STARTED
production integration: PROHIBITED
```

The canonical `gamification` branch contains isolated research contracts, fixtures, simulator code, accepted synthetic evidence and bounded governance decisions. Research candidates and research outcomes are not production economies.

## Current G4 contracts

### G4.1 core economy problem contract

- [Human core economy contract](core-economy-problem-contract.md)
- [Machine contract](../../research/gamification-sim/contracts/core-economy-problem-contract-v1.json)
- [Strict Draft 2020-12 schema](../../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json)
- [G4.1 closeout](../../roadmap/gamification/g4-core-economy-problem-contract.md)

G4.1 freezes the problem and boundaries for a two-domain core economy:

```text
REVIEW_DOMAIN
LEARN_DOMAIN
```

`CREATE_DOMAIN` is excluded. G3 is deferred until after the first stable Gamification release, is not on the first-MVP critical path and does not block G4, G5 or G6. Reactivation requires a separate owner decision and a concrete evidence-backed trigger.

The Review input remains an explicit uncertainty axis:

```text
P-STEP-ZERO: CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D: CONFIRMATORY_ELIGIBLE; not selected; not falsified
Review winner: NONE
```

The Learn input remains bounded by its source evidence:

```text
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
G2.5 status: CONFIRMATORY_INCONCLUSIVE
reason: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
confirmatory eligible: NO
production ready: NO
```

Contract inventory:

```text
terminology: 30
personas: 9
threat families: 14
protected invariants: 28
allowed final outcomes: 3
G4.2 requirements: 14
```

No conversion ratio, normalized XP, daily cap, productive-day threshold, level curve, streak, Momentum or recovery formula was selected. No candidate registry, matrix, simulation or production implementation was started.

## Current G2 contracts

### G2.1 problem contract

- [Learn XP problem contract](learn-xp-problem-contract.md)
- [G2.1 closeout](../../roadmap/gamification/g2-learn-xp-problem-contract.md)
- [Machine-readable Learn XP problem contract](../../research/gamification-sim/contracts/learn-xp-problem-contract-v1.json)
- [Learn XP problem schema](../../research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json)

G2.1 freezes Learn XP terminology, scheduler/reward boundaries, four identity candidates, pending/confirmation minimum requirements, six anti-farming threat families, 19 protected invariants, privacy/claims boundaries and the G2.2 entry contract.

### G2.2 lifecycle model

- [Human lifecycle and anti-farming model](learn-xp-lifecycle-model.md)
- [Machine lifecycle model](../../research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json)
- [Lifecycle model schema](../../research/gamification-sim/schemas/learn-xp-lifecycle-model-v1.schema.json)
- [Lifecycle fixture schema](../../research/gamification-sim/schemas/learn-xp-lifecycle-fixture-v1.schema.json)
- [Fixture manifest](../../research/gamification-sim/fixtures/learn-xp-lifecycle-v1/manifest.json)
- [G2.2 closeout](../../roadmap/gamification/g2-learn-xp-lifecycle.md)

G2.2 defines seven lifecycle states, 20 events and 12 deterministic transitions. Identity is factorized as `LearningEpisode<AchievementSubject>`.

### G2.3 candidate protocol

- [Human candidate protocol](learn-xp-candidate-protocol.md)
- [Machine candidate protocol](../../research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json)
- [Candidate protocol schema](../../research/gamification-sim/schemas/learn-xp-candidate-protocol-v1.schema.json)
- [Dry matrix generator](../../research/gamification-sim/src/gamification_sim/learn_candidate_protocol.py)
- [Focused tests](../../research/gamification-sim/tests/test_learn_candidate_protocol.py)
- [G2.3 closeout](../../roadmap/gamification/g2-learn-xp-candidate-protocol.md)

G2.3 freezes two families, four parameterizations, two subject strategies, two delay policies, eight candidates, two zero-reward reference variants, five hypotheses, 23 hard gates, 14 metrics and exact `340/340` dry matrix identities.

### G2.4 bounded screening

- [Technical reference](learn-xp-bounded-screening.md)
- [G2.4 closeout](../../roadmap/gamification/g2-learn-xp-bounded-screening.md)
- [Evidence schema](../../research/gamification-sim/schemas/learn-xp-bounded-screening-evidence-v1.schema.json)
- [Screening harness](../../research/gamification-sim/src/gamification_sim/learn_bounded_screening.py)
- [Allocation evaluator](../../research/gamification-sim/src/gamification_sim/learn_reward_allocation.py)
- [Focused tests](../../research/gamification-sim/tests/test_learn_bounded_screening.py)

The valid replacement run completed `340/340` units. Family survivors are `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` and `C-PENDING-SPLIT-D1-NOTE-SIBLING`.

### G2.5 confirmatory evidence

- [Human confirmatory protocol](learn-xp-confirmatory-protocol.md)
- [Machine confirmatory protocol](../../research/gamification-sim/contracts/learn-xp-confirmatory-protocol-v1.json)
- [Protocol schema](../../research/gamification-sim/schemas/learn-xp-confirmatory-protocol-v1.schema.json)
- [Evidence schema](../../research/gamification-sim/schemas/learn-xp-confirmatory-evidence-v1.schema.json)
- [Confirmatory harness](../../research/gamification-sim/src/gamification_sim/learn_confirmatory.py)
- [Focused tests](../../research/gamification-sim/tests/test_learn_confirmatory.py)
- [Confirmatory closeout](../../roadmap/gamification/g2-learn-xp-confirmatory-evidence.md)

Both survivors are `CONFIRMATORY_INCONCLUSIVE` because the disposable Anki identity probe was unavailable under `SYNTHETIC_CONTRACT_ONLY`; reference is `REFERENCE_ONLY`.

### G2.6 final Learn XP decision

- [Final decision and G2 closeout](../../roadmap/gamification/g2-learn-xp-decision.md)

G2.6 recommends `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` under `MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE`. This does not change the G2.5 outcome or approve production.

## Current G1 contracts

- [Review XP cross-horizon cycling problem](review-xp-cycling-problem.md)
- [G1.1 problem and gate freeze](../../roadmap/gamification/g1-problem-gate-freeze.md)
- [G1.1 contract correction](../../roadmap/gamification/g1-contract-correction.md)
- [G1.2 root-cause attribution](../../roadmap/gamification/g1-root-cause-attribution.md)
- [G1.2a attribution correction](../../roadmap/gamification/g1-root-cause-attribution-correction.md)
- [G1.3 candidate protocol](review-xp-candidate-protocol.md)
- [G1.3 stage report](../../roadmap/gamification/g1-candidate-protocol.md)
- [G1.4 bounded screening](../../roadmap/gamification/g1-bounded-screening.md)
- [G1.5 confirmatory protocol](review-xp-confirmatory-protocol.md)
- [G1.5 confirmatory evidence](../../roadmap/gamification/g1-confirmatory-evidence.md)
- [G1.6 decision and G1 closeout](../../roadmap/gamification/g1-review-xp-decision.md)
- [Machine-readable candidate protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json)
- [Candidate protocol schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json)

G1 closed with `DEFER_REVIEW_MODEL`. Both zero-endpoint candidates remain confirmatory-eligible, not selected and not falsified.

## Review research references

- [Review event taxonomy](anki-review-event-taxonomy.md)
- [Review reward model](anki-review-reward-model.md)
- [Review abuse model](anki-review-abuse-model.md)
- [Review session and Anki-day aggregation](anki-review-session-and-day.md)
- [Review simulation specification](anki-review-simulation-spec.md)

These are references for terminology, research discipline and protected invariants. Historical candidate numbers do not define the G4 economy automatically.

## Evidence and privacy boundary

G1/G2 evidence is synthetic. G4.1 is a prospective contract freeze and adds no new simulation or real-user evidence. No real card text, note fields, media, profile paths, usernames, tokens, raw revlog or identifiable learning history enter G4 artifacts.

## Production integration boundary

No production add-on, dashboard, payload, API, scheduler, FSRS, database, workflow, package, release or telemetry integration is approved. G4.2 remains not started, and research assets remain outside Fast CI and `.ankiaddon` contents.
