# Gamification Review simulator

## Status

```text
G0 current evidence: Reproduced
G1.1: Complete
G1.2/G1.2a: Complete
G1.3 protocol: Frozen / Complete
G1.4 protocol readiness: Ready
G1.4 execution readiness: Blocked on implementation
G1.4 started: No
```

The package is isolated under `research/gamification-sim/`. It has no production imports, root dependency changes, Fast CI/package/release integration, real Anki profile data, collection data or tokens.

## Structure

```text
configs/       bounded current inputs
contracts/     versioned research contracts
fixtures/      deterministic synthetic corpus
personas/      synthetic workload personas
scenarios/     ordinary, edge, control, abuse and regression cases
schemas/       active strict schemas
src/           Python research package
tests/         Python research tests
rust-oracle/   isolated Rust implementation
```

## Current G1 artifacts

- [G1.1 diagnostic contract](contracts/review-cycling-diagnostic-v1.json)
- [G1.1 schema](schemas/review-cycling-diagnostic-v1.schema.json)
- [G1.2a evidence](evidence/g1.2-root-cause-attribution-v1.json)
- [G1.3 candidate protocol](contracts/review-xp-candidate-protocol-v1.json)
- [G1.3 protocol schema](schemas/review-xp-candidate-protocol-v1.schema.json)
- [Human protocol](../../docs/gamification/review-xp-candidate-protocol.md)
- [G1.3 report](../../roadmap/gamification/g1-candidate-protocol.md)

G1.3 designed but did not execute the bounded screening matrix. The current static `RewardParameterSet` and `evaluate_episode()` interface cannot apply post-transition-only MemoryGain scaling/tapering, and the four frozen parameterizations are not registered. G1.4 must implement exactly that frozen capability before running evidence; it may not change bounds, thresholds or matrix after seeing results.

## Available command surface

The installed package retains its existing compare/evaluate/longitudinal/population/scenario/sensitivity/sweep/verification commands. G1.3 added no command, dependency, config, source or test change.

## Evidence and production boundary

G0.7 and G1.2a are current synthetic evidence. Historical reports remain non-authoritative where they conflict. The package is research-only and is not part of the add-on runtime, dashboard, `.ankiaddon`, Fast CI or release pipeline. Generated outputs, environments, caches, coverage, build/dist and `rust-oracle/target/` remain untracked.
