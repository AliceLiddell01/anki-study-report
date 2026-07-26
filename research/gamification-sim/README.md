# Gamification research simulator and contracts

## Status

```text
G0 current evidence: REPRODUCED
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review XP research candidate: NONE
G2: IN PROGRESS
G2.1: COMPLETE
G2.2: NEXT / NOT STARTED
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
```

No G2 command exists after G2.1.

## Evidence and production boundary

G0.7, G1.2a, G1.4 and G1.5 are synthetic evidence. G2.1 is a prospective contract freeze and creates no new simulation evidence.

Research artifacts are not part of the add-on runtime, dashboard, `.ankiaddon`, Fast CI or release pipeline. Generated outputs, environments, caches, coverage, build/dist and `rust-oracle/target/` remain untracked.
