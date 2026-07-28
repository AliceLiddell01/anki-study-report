# Gamification research documentation

## Current state

```text
G0: COMPLETE
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review XP research candidate: NONE
G2: COMPLETE
G2.1: COMPLETE
G2.2: COMPLETE
G2.3: COMPLETE
G2.4: COMPLETE
G2.5: COMPLETE — CONFIRMATORY INCONCLUSIVE
G2.6: COMPLETE
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended Learn XP research candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
G3: DEFERRED / POST-MVP / NOT STARTED
G3 blocks G4/G5/G6: NO
G4: IN PROGRESS
G4.1: COMPLETE
core economy contract: FROZEN_PRE_NORMALIZATION_ANALYSIS
G4.2: COMPLETE
input/uncertainty model: FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
G4.3: NEXT / NOT STARTED
production integration: PROHIBITED
```

The canonical `gamification` branch contains isolated research contracts, fixtures, simulator code, accepted synthetic evidence and bounded governance decisions. Research candidates and research outcomes are not production economies.

## Current G4 contracts

### G4.1 core economy problem contract

- [Human core economy contract](core-economy-problem-contract.md)
- [Machine contract](../../research/gamification-sim/contracts/core-economy-problem-contract-v1.json)
- [Strict Draft 2020-12 schema](../../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json)
- [G4.1 closeout](../../roadmap/gamification/g4-core-economy-problem-contract.md)

G4.1 freezes the two-domain problem for `REVIEW_DOMAIN` and `LEARN_DOMAIN`, excludes `CREATE_DOMAIN`, preserves both Review candidates and the inconclusive Learn limitation, and selects no numeric economy policy.

### G4.2 input normalization and uncertainty model

- [Human input/uncertainty model](core-economy-input-normalization-model.md)
- [Machine contract](../../research/gamification-sim/contracts/core-economy-input-normalization-v1.json)
- [Strict Draft 2020-12 schema](../../research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json)
- [G4.2 closeout](../../roadmap/gamification/g4-core-economy-input-normalization.md)

G4.2 freezes:

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

Axes are explicitly separated:

```text
SESSION
ANKI_DAY
CALENDAR_DAY
```

The contract contains 7 dispositions, 18 fail-closed reasons, 9 persona descriptors, 15 future fixture requirements, 14 threats, 28 invariants and 14 G4.3 entry requirements.

No conversion ratio, normalized unit/value, cap, productive-day threshold, level curve, streak, Momentum or recovery formula was selected. No candidate family, exact trace, matrix, simulation or production implementation was started.

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

### G2.4 bounded screening and disclosed harness correction

- [Technical reference](learn-xp-bounded-screening.md)
- [G2.4 closeout](../../roadmap/gamification/g2-learn-xp-bounded-screening.md)
- [Evidence schema](../../research/gamification-sim/schemas/learn-xp-bounded-screening-evidence-v1.schema.json)
- [Screening harness](../../research/gamification-sim/src/gamification_sim/learn_bounded_screening.py)
- [Allocation evaluator](../../research/gamification-sim/src/gamification_sim/learn_reward_allocation.py)
- [Focused tests](../../research/gamification-sim/tests/test_learn_bounded_screening.py)

The first canonical attempt on `ef7c638a…` remains quarantined as `INVALID`. The disclosed packaging-only `HARNESS` correction was published as `548b27de6283b32fb27541db02ce6c8b65c29756` and changed no frozen screening-design field. The replacement matrix completed `340/340` unique units with detached validation and byte-identical bundle reproduction. Family survivors are `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` and `C-PENDING-SPLIT-D1-NOTE-SIBLING`; no cross-family ranking or final model selection was performed.

### G2.5 confirmatory evidence

- [Human confirmatory protocol](learn-xp-confirmatory-protocol.md)
- [Machine confirmatory protocol](../../research/gamification-sim/contracts/learn-xp-confirmatory-protocol-v1.json)
- [Protocol schema](../../research/gamification-sim/schemas/learn-xp-confirmatory-protocol-v1.schema.json)
- [Evidence schema](../../research/gamification-sim/schemas/learn-xp-confirmatory-evidence-v1.schema.json)
- [Confirmatory harness](../../research/gamification-sim/src/gamification_sim/learn_confirmatory.py)
- [Focused tests](../../research/gamification-sim/tests/test_learn_confirmatory.py)
- [Confirmatory closeout](../../roadmap/gamification/g2-learn-xp-confirmatory-evidence.md)

G2.5 prospectively froze exactly two G2.4 survivors, one subject-matched zero-reward reference, 36 conditions per identity and `FORWARD`/`REVERSE` replay for exact `216` units. The canonical run completed `216/216/216` units with `0/0/0` missing/extra/duplicates, detached validation and byte-identical reproduction. Both survivors are `CONFIRMATORY_INCONCLUSIVE` because the disposable Anki identity probe was unavailable under `SYNTHETIC_CONTRACT_ONLY`; the zero-reward reference is `REFERENCE_ONLY`. No cross-family ranking, winner, recommendation, final model selection or production approval was produced.

### G2.6 final Learn XP decision

- [Final decision and G2 closeout](../../roadmap/gamification/g2-learn-xp-decision.md)

G2.6 closes G2 with `RECOMMEND_LEARN_XP_RESEARCH_MODEL` and recommends `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` for bounded future design/research use. The explicit decision principle is `MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE`: both survivor families preserve the same bounded confirmed total and frozen safety properties, while confirmation-only adds no provisional reward exposure and has the smaller accounting/explanation surface. This governance decision preserves both G2.5 outcomes as `CONFIRMATORY_INCONCLUSIVE`, does not falsify the non-selected pending-split candidate and does not approve production.

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

These are references for terminology, research discipline and protected invariants. Their Review XP formulas, candidates and matrices do not determine G4 normalization automatically.

## Evidence and privacy boundary

G1 evidence is synthetic. G2.1–G2.6 retain their prospective/evidence/governance chronology. G4.1 freezes the two-domain problem. G4.2 freezes typed input/uncertainty/axis/fail-closed boundaries without adding exact traces, simulation or real-user evidence. No real card text, note fields, media, profile paths, usernames, tokens, raw revlog or identifiable learning history enter G4 research artifacts.

## Production integration boundary

No production add-on, dashboard, payload, API, scheduler, FSRS, database, workflow, package, release or telemetry integration is approved. G4.2 is a research contract freeze; G4.3 remains not started. Research assets remain outside Fast CI and `.ankiaddon` contents.

### G4.2 final state

```text
G3: DEFERRED / POST-MVP / NOT STARTED
G4: IN PROGRESS
G4.1: COMPLETE
G4.2: COMPLETE
model: FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
Review inputs: P-STEP-ZERO; P-TAPER-ZERO-30D
Review winner/default: NONE / NONE
Learn input: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
axes: SESSION; ANKI_DAY; CALENDAR_DAY
numeric policy: NOT SELECTED
G4.3: NEXT / NOT STARTED
simulation: NOT STARTED
production approved: NO
production integration: PROHIBITED
```
