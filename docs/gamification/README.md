# Gamification research documentation

## Current state

```text
G0: COMPLETE
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review XP research candidate: NONE
G2: IN PROGRESS
G2.1: COMPLETE
G2.2: COMPLETE
G2.3: COMPLETE
G2.4: IN PROGRESS — PRE-RESULTS IMPLEMENTATION
production integration: PROHIBITED
```

The canonical `gamification` branch contains isolated research contracts, fixtures, simulator code and accepted synthetic evidence. Research candidates and research outcomes are not production economies.

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

G2.2 defines seven lifecycle states, 20 events and 12 deterministic transitions. Identity is factorized as `LearningEpisode<AchievementSubject>`; `CARD`, `NOTE` and `SIBLING_GROUP` remain unresolved subject candidates.

The frozen fixture manifest contains 23 deterministic fixtures, covers six threat families and maps all 19 protected invariants. Focused validation and the full research suite passed.

G2.2 does not select an achievement-subject winner, reward amount, pending ratio, numeric confirmation delay, candidate family or screening matrix.

### G2.3 candidate protocol

- [Human candidate protocol](learn-xp-candidate-protocol.md)
- [Machine candidate protocol](../../research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json)
- [Candidate protocol schema](../../research/gamification-sim/schemas/learn-xp-candidate-protocol-v1.schema.json)
- [Dry matrix generator](../../research/gamification-sim/src/gamification_sim/learn_candidate_protocol.py)
- [Focused tests](../../research/gamification-sim/tests/test_learn_candidate_protocol.py)
- [G2.3 closeout](../../roadmap/gamification/g2-learn-xp-candidate-protocol.md)

G2.3 freezes two families, four parameterizations, two subject strategies, two delay policies, eight candidates, two zero-reward reference variants, five hypotheses, 23 hard gates, 14 metrics and an exact deterministic `340/340` G2.4 dry matrix.

Protocol status is `FROZEN_PRE_SCREENING_IMPLEMENTATION`; publication SHA is `41313c9369c76d331d489a9aa4b44da2497b3132`. Full G2.3 research validation passed with `982` tests.

### G2.4 pre-results implementation

- [Technical reference](learn-xp-bounded-screening.md)
- [Evidence schema](../../research/gamification-sim/schemas/learn-xp-bounded-screening-evidence-v1.schema.json)
- [Screening harness](../../research/gamification-sim/src/gamification_sim/learn_bounded_screening.py)
- [Allocation evaluator](../../research/gamification-sim/src/gamification_sim/learn_reward_allocation.py)
- [Focused tests](../../research/gamification-sim/tests/test_learn_bounded_screening.py)

G2.4 implementation is being prepared under the publication barrier. No canonical screening evidence, candidate outcomes or family survivors are present in this state.

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

G1 closed with `DEFER_REVIEW_MODEL`. `P-STEP-ZERO` and `P-TAPER-ZERO-30D` remain confirmatory-eligible, not selected and not falsified. Production remains prohibited.

## Review research references

- [Review event taxonomy](anki-review-event-taxonomy.md)
- [Review reward model](anki-review-reward-model.md)
- [Review abuse model](anki-review-abuse-model.md)
- [Review session and Anki-day aggregation](anki-review-session-and-day.md)
- [Review simulation specification](anki-review-simulation-spec.md)

These are references for terminology, research discipline and protected invariants. Their Review XP formulas, candidates and matrices do not define Learn XP automatically.

## Evidence and privacy boundary

G1 evidence is synthetic. G2.1 is a prospective contract freeze; G2.2 adds deterministic synthetic lifecycle fixtures and a research-only evaluator; G2.3 adds prospective protocol and dry matrix identities; the G2.4 pre-results implementation adds only synthetic harness/schema/tests and no results. No real card text, note fields, media, profile paths, usernames, tokens, raw revlog or identifiable learning history enter G2 research artifacts.

## Production integration boundary

No production add-on, dashboard, payload, API, scheduler, FSRS, database, workflow, package, release or telemetry integration is approved. G2.3 remains frozen; G2.4 is in pre-results implementation and production integration remains prohibited. Research assets remain outside Fast CI and `.ankiaddon` contents.
