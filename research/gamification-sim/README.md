# Gamification Review simulator

## Status

```text
G0 current evidence: Reproduced
G1.1: Complete
G1.2/G1.2a: Complete
G1.3 protocol: Frozen / Complete
G1.4 bounded screening: Complete
G1.4 survivors: P-STEP-ZERO; P-TAPER-ZERO-30D
G1.5: Next / Ready; not started
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
- [G1.4 bounded screening closeout](../../roadmap/gamification/g1-bounded-screening.md)

G1.4 added an isolated typed mechanism registry, execution context and deterministic bounded-screening harness without changing production code, scheduler/FSRS semantics or the default `R-CURRENT` result.

The exact matrix completed with 160 unique units and no missing, extra or duplicate units. `P-STEP-ZERO` and `P-TAPER-ZERO-30D` survive at family level. The two neutral-ratio variants failed only `GATE-NO-CYCLING-GROWTH`.

## Available command surface

The research package now includes:

```text
validate-bounded-screening
run-bounded-screening
```

The runner validates the frozen protocol/schema and exact 160-unit manifest, requires exact base/implementation SHA provenance, evaluates non-compensable hard gates and writes deterministic external evidence. It does not choose a final candidate or integrate with production.

## Evidence and production boundary

G0.7, G1.2a and the recorded G1.4 identities are current synthetic evidence. The raw G1.4 bundle remains external to Git with SHA-256 `bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be`; its semantic evidence digest is `836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694`.

Historical reports remain non-authoritative where they conflict. The package is research-only and is not part of the add-on runtime, dashboard, `.ankiaddon`, Fast CI or release pipeline. Generated outputs, environments, caches, coverage, build/dist and `rust-oracle/target/` remain untracked.
