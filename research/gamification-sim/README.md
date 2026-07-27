# Gamification research simulator and contracts

## Status

```text
G0 current evidence: REPRODUCED
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review XP research candidate: NONE
G2: IN PROGRESS
G2.1: COMPLETE
G2.2: COMPLETE
G2.3: COMPLETE
G2.4: IN PROGRESS — POST-RESULTS HARNESS CORRECTION BEFORE VALID RERUN
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

## G2.1 Learn XP artifacts

- [Machine problem contract](contracts/learn-xp-problem-contract-v1.json)
- [Strict Draft 2020-12 schema](schemas/learn-xp-problem-contract-v1.schema.json)
- [Human problem contract](../../docs/gamification/learn-xp-problem-contract.md)
- [G2.1 closeout](../../roadmap/gamification/g2-learn-xp-problem-contract.md)

G2.1 freezes:

```text
problem statement and terminology
Anki scheduler-state / Learn XP research-state boundary
identity candidates: CARD, NOTE, SIBLING_GROUP, LEARNING_EPISODE
pending and confirmation minimum requirements
rewardable/non-rewardable category boundary
six anti-farming threat families
19 protected invariants
privacy and claims boundaries
G2.2 entry contract
three allowed final G2 outcomes
```

G2.1 adds no executable command and runs no simulation. It does not select an identity winner, lifecycle, reward amount, pending ratio, confirmation delay, candidate family or matrix.

The contract reuses existing `strict_json.py`, `canonical_json.py` and bounded workspace conventions as validation references. No generic validator framework or production code was added.

## G2.2 Learn XP lifecycle artifacts

- [Machine lifecycle model](contracts/learn-xp-lifecycle-model-v1.json)
- [Lifecycle model schema](schemas/learn-xp-lifecycle-model-v1.schema.json)
- [Lifecycle fixture schema](schemas/learn-xp-lifecycle-fixture-v1.schema.json)
- [Human lifecycle model](../../docs/gamification/learn-xp-lifecycle-model.md)
- [Fixture manifest](fixtures/learn-xp-lifecycle-v1/manifest.json)
- [Research-only evaluator](src/gamification_sim/learn_lifecycle.py)
- [Focused tests](tests/test_learn_lifecycle.py)
- [G2.2 closeout](../../roadmap/gamification/g2-learn-xp-lifecycle.md)

Frozen G2.2 state:

```text
model status: FROZEN_PRE_CANDIDATE_DESIGN
states: 7
events: 20
transitions: 12
identity architecture: FACTORIZED
generic form: LearningEpisode<AchievementSubject>
subject candidates: CARD; NOTE; SIBLING_GROUP
subject winner: NONE
fixtures: 23
threat families: 6
protected invariants: 19
manifest digest: 4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
```

The pre-conformance model was published at `63741bcc4d757cd131ab94d9e262042679460d6f`. Focused validation and one bounded full-suite retry after a concrete Cargo cache repair passed. No lifecycle semantics changed after conformance.

G2.2 selects no XP amount, pending ratio, numeric confirmation delay, achievement-subject winner, candidate family or screening matrix.

## G2.3 Learn XP candidate protocol artifacts

- [Machine candidate protocol](contracts/learn-xp-candidate-protocol-v1.json)
- [Strict Draft 2020-12 schema](schemas/learn-xp-candidate-protocol-v1.schema.json)
- [Human candidate protocol](../../docs/gamification/learn-xp-candidate-protocol.md)
- [Dry matrix generator](src/gamification_sim/learn_candidate_protocol.py)
- [Focused protocol tests](tests/test_learn_candidate_protocol.py)
- [G2.3 closeout](../../roadmap/gamification/g2-learn-xp-candidate-protocol.md)

Frozen G2.3 state:

```text
protocol status: FROZEN_PRE_SCREENING_IMPLEMENTATION
protocol publication SHA: 41313c9369c76d331d489a9aa4b44da2497b3132
families: 2
parameterizations: 4
subject strategies: 2
delay policies: 2
candidates: 8
reference variants: 2
hypotheses: 5
hard gates: 23
descriptive metrics: 14
expected units: 340
unique unit IDs: 340
seed axis: ABSENT_DETERMINISTIC
full research suite: 982 passed
```

G2.3 also consolidates lifecycle digest serialization into the shared helper and enforces exact direct-event types without changing the 31 frozen lifecycle results or fixture manifest digest.

The protocol contains no screening results, candidate outcomes or survivors.

## G2.4 Learn XP bounded-screening artifacts

- [Allocation evaluator](src/gamification_sim/learn_reward_allocation.py)
- [Bounded screening harness and detached validator](src/gamification_sim/learn_bounded_screening.py)
- [Strict evidence schema](schemas/learn-xp-bounded-screening-evidence-v1.schema.json)
- [Focused tests](tests/test_learn_bounded_screening.py)
- [Technical reference](../../docs/gamification/learn-xp-bounded-screening.md)

The implementation consumes only the frozen `340/340` manifest generated by `learn_candidate_protocol.py`. The first published canonical attempt is invalid after a byte-identical archive reproduction failure caused by inherited filesystem modes. Its results were viewed and are explicitly disclosed but quarantined. The packaging-only `HARNESS` correction normalizes tar member mode to `0644`; a new published implementation and complete `340`-unit rerun are required.

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

G1.4 executed exact 160-unit bounded screening and retained `P-STEP-ZERO` and `P-TAPER-ZERO-30D`.

```text
screened implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

canonical G1.4 merge SHA:
d855baf7355bba3f4014370cafba3fdc6d0c0e3c

manifest digest:
40297310ef11318f940ddee8a6f5e1d1b20df93d914c4d7442eb4681f60da57c

evidence digest:
836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694
```

G1.5 executed the prospectively published 840-unit confirmatory matrix on implementation `7ae7a26cf0591dfc7f004f3b378eb3bff8b7d2c8`. Both survivors received `CONFIRMATORY_ELIGIBLE`.

```text
manifest digest:
eea4e2ed6da087f7ac45eb56d9390b23e44ce52837b5f1d015afb3276049c728

evidence digest:
9b4d6aa41bf2392aac273784b45b28ff88210e05ea04533bf440d6522ad75afa

external evidence bundle SHA-256:
90b2132cbe46edeb2a28e6f9ae81de311807353dd5e0826cbe8d3a6af41a85fb
```

G1.6 closed G1 with `DEFER_REVIEW_MODEL` and recommended no research candidate. Both candidates remain eligible, not selected and not falsified.

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
```

The G2.4 commands remain research-only surfaces. After the invalid disclosed attempt, `run-learn-xp-screening` may be used again only for the required complete rerun on the newly published corrected implementation SHA.

## Evidence and production boundary

G0.7, G1.2a, G1.4 and G1.5 are synthetic evidence. G2.1 is a prospective contract freeze. G2.2 adds deterministic synthetic lifecycle fixtures and conformance evidence. G2.3 adds prospective candidate protocol and dry matrix identities. G2.4 records one invalid disclosed synthetic attempt and a packaging-only correction before the required valid rerun; no production evidence or approval exists.

Research artifacts are not part of the add-on runtime, dashboard, `.ankiaddon`, Fast CI or release pipeline. Generated outputs, environments, caches, coverage, build/dist and `rust-oracle/target/` remain untracked.
