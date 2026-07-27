# Gamification research simulator and contracts

## Status

```text
G0 current evidence: REPRODUCED
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

## G4.1 core economy problem contract

- [Machine contract](contracts/core-economy-problem-contract-v1.json)
- [Strict Draft 2020-12 schema](schemas/core-economy-problem-contract-v1.schema.json)
- [Human contract](../../docs/gamification/core-economy-problem-contract.md)
- [G4.1 closeout](../../roadmap/gamification/g4-core-economy-problem-contract.md)

Frozen state:

```text
contract_id: core-economy-problem-contract
version: 1
status: FROZEN_PRE_NORMALIZATION_ANALYSIS
initial domains: REVIEW_DOMAIN; LEARN_DOMAIN
Create XP: EXCLUDED / DEFERRED WITH G3
Review uncertainty: P-STEP-ZERO; P-TAPER-ZERO-30D
Review winner: NONE
Learn candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
terminology / personas / threats / invariants: 30 / 9 / 14 / 28
allowed final outcomes: 3
G4.2 requirements: 14
G4.2 started: false
production approved: false
```

G3 is deferred until after the first stable Gamification release, is outside the first-MVP critical path and does not block G4, G5 or G6. G4.1 adds no evaluator, CLI command, candidate registry, matrix, fixture trace or simulation. It selects no conversion ratio, normalized XP, productive-day threshold, level curve, streak, Momentum or recovery formula.

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
- [G2.4 closeout](../../roadmap/gamification/g2-learn-xp-bounded-screening.md)

The implementation consumes only the frozen `340/340` manifest generated by `learn_candidate_protocol.py`. The first canonical attempt on `ef7c638a…` is quarantined as `INVALID`; its results-viewed disclosure remains in the replacement evidence. The packaging-only `HARNESS` correction normalizes tar member mode to `0644` and was published as `548b27de6283b32fb27541db02ce6c8b65c29756` without changing families, delays, subjects, units, gates, metrics or selection rules. The replacement run completed `340/340` unique units, detached recomputation and byte-identical bundle reproduction.

## G2.5 Learn XP confirmatory artifacts

- [Machine confirmatory protocol](contracts/learn-xp-confirmatory-protocol-v1.json)
- [Protocol schema](schemas/learn-xp-confirmatory-protocol-v1.schema.json)
- [Evidence schema](schemas/learn-xp-confirmatory-evidence-v1.schema.json)
- [Human confirmatory protocol](../../docs/gamification/learn-xp-confirmatory-protocol.md)
- [Confirmatory harness and detached validator](src/gamification_sim/learn_confirmatory.py)
- [Focused tests](tests/test_learn_confirmatory.py)
- [Confirmatory closeout](../../roadmap/gamification/g2-learn-xp-confirmatory-evidence.md)

The prospectively published matrix completed `216/216/216` units with `0/0/0` missing/extra/duplicates, detached validation and byte-identical reproduction. Both survivors are `CONFIRMATORY_INCONCLUSIVE` because the disposable Anki identity probe was unavailable under `SYNTHETIC_CONTRACT_ONLY`; the zero-reward reference is `REFERENCE_ONLY`. No ranking, winner, recommendation, final model or production approval was produced by G2.5.

## G2.6 final Learn XP decision

- [Final decision and G2 closeout](../../roadmap/gamification/g2-learn-xp-decision.md)

G2.6 is docs-only and adds no command, protocol field, schema, simulation, matrix or evidence. It closes G2 with:

```text
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended research candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
decision basis: MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE
```

The selected model preserves the same frozen `1.0 LRU` confirmed total as the pending-split survivor, while creating no provisional reward exposure and requiring the smaller accounting/explanation surface. Both G2.5 outcomes remain `CONFIRMATORY_INCONCLUSIVE` because the disposable Anki identity probe was unavailable. The non-selected pending-split candidate remains non-falsified and is not rejected as invalid. The recommendation is not confirmatory eligibility, human-learning evidence, motivation evidence or production approval.

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
validate-learn-xp-confirmatory
run-learn-xp-confirmatory
validate-learn-xp-confirmatory-evidence
```

The G2.4 and G2.5 commands remain historical research-only surfaces. G4.1 adds no executable command and reruns no matrix.

## Evidence and production boundary

G0.7, G1.2a, G1.4 and G1.5 are synthetic evidence. G2.1 is a prospective contract freeze. G2.2 adds deterministic synthetic lifecycle fixtures and conformance evidence. G2.3 adds prospective candidate protocol and dry matrix identities. G2.4 records one invalid disclosed synthetic attempt and one valid full replacement run. G2.5 records a prospectively published, deterministic confirmatory run with two fail-closed inconclusive candidate outcomes. G2.6 records a bounded research/product governance recommendation without adding evidence or changing frozen outcomes. G4.1 prospectively freezes the two-domain core economy problem without adding evidence or changing G1/G2 outcomes. The valid external bundles remain owner-managed and are not part of Git; no production evidence or approval exists.

Research artifacts are not part of the add-on runtime, dashboard, `.ankiaddon`, Fast CI or release pipeline. Generated outputs, environments, caches, coverage, build/dist and `rust-oracle/target/` remain untracked.

## G2 canonical evidence identity retained for G4 input

```text
protocol publication SHA: 903604245aaa540674f650b998d32f497b018f49
expected / actual / unique: 216 / 216 / 216
missing / extra / duplicates: 0 / 0 / 0
manifest digest: 6224c9b363f18662328a89981dd2e8f303f14a10ac43771e74be220dc27d3f27
evidence digest: d2d5327e382ae85b1fea575f9efed5604ed11905aff56ec19a005546726badbe
canonical archive SHA-256: 4e96835f5517d8bd2e9ce350776b8e3bc24dc8878c74f1e5c0897d216506678e
canonical evidence.json SHA-256: cc275780dfc98eaa8e683188815606568a7aaca80720e3ddeb5584914da61a4a
detached validation: PASS
byte-identical reproduction: PASS
```

`C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` and `C-PENDING-SPLIT-D1-NOTE-SIBLING` remain `CONFIRMATORY_INCONCLUSIVE` with reason `DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE`. `R-NO-LEARN-XP-NOTE-SIBLING` remains `REFERENCE_ONLY`.
