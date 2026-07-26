# Gamification Review simulator

## Status

```text
G0 current evidence: Reproduced
G1.1: Complete
G1.2/G1.2a: Complete
G1.3 protocol: Frozen / Complete
G1.4 bounded screening: Complete
G1.4 survivors: P-STEP-ZERO; P-TAPER-ZERO-30D
G1.5: Complete; both survivors CONFIRMATORY_ELIGIBLE
G1.6: Complete
G1 final outcome: DEFER_REVIEW_MODEL
recommended research candidate: NONE
production integration: PROHIBITED
G2: PLANNED / NOT STARTED
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
- [G1.4 technical reference](../../docs/gamification/review-xp-bounded-screening.md)
- [G1.4 full report](../../roadmap/gamification/g1-bounded-screening.md)
- [G1.5 machine protocol](contracts/review-xp-confirmatory-protocol-v1.json)
- [G1.5 strict schema](schemas/review-xp-confirmatory-protocol-v1.schema.json)
- [G1.5 human protocol](../../docs/gamification/review-xp-confirmatory-protocol.md)
- [G1.5 closeout](../../roadmap/gamification/g1-confirmatory-evidence.md)
- [G1.6 decision and G1 closeout](../../roadmap/gamification/g1-review-xp-decision.md)

G1.4 added an isolated typed mechanism registry, execution context and deterministic bounded-screening harness without changing production code, scheduler/FSRS semantics or the default `R-CURRENT` result.

The exact matrix completed with 160 unique units and no missing, extra or duplicate units. `P-STEP-ZERO` and `P-TAPER-ZERO-30D` survive at family level. The two neutral-ratio variants failed only `GATE-NO-CYCLING-GROWTH`.

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

G1.5 executed the prospectively published 840-unit confirmatory matrix on implementation `7ae7a26cf0591dfc7f004f3b378eb3bff8b7d2c8`. Both `P-STEP-ZERO` and `P-TAPER-ZERO-30D` received `CONFIRMATORY_ELIGIBLE`; no ranking or final selection occurred.

```text
manifest digest:
eea4e2ed6da087f7ac45eb56d9390b23e44ce52837b5f1d015afb3276049c728

evidence digest:
9b4d6aa41bf2392aac273784b45b28ff88210e05ea04533bf440d6522ad75afa

external evidence bundle SHA-256:
90b2132cbe46edeb2a28e6f9ae81de311807353dd5e0826cbe8d3a6af41a85fb
```

G1.6 closed G1 with `DEFER_REVIEW_MODEL` and recommended no research candidate. The raw G1.4/G1.5 bundles were unavailable for the required continuity revalidation, while accepted aggregate evidence left STEP and TAPER tied under the frozen non-compensable criteria. Both candidates remain `CONFIRMATORY_ELIGIBLE`, not selected and not falsified. No research code, protocol, matrix or simulation changed.

## Available command surface

The research package includes:

```text
validate-bounded-screening
run-bounded-screening
validate-confirmatory-protocol
validate-confirmatory-evidence
run-confirmatory
```

The G1.4 runner validates the frozen 160-unit screening contract. The G1.5 runner validates the frozen 840-unit confirmatory contract, requires exact published implementation/base provenance, recomputes non-compensable gates and writes deterministic external evidence. Neither runner ranks families, chooses a final candidate or integrates with production.

See the [technical reference](../../docs/gamification/review-xp-bounded-screening.md) for command syntax, mechanism semantics, output layout, fail-closed validation and G1.5 handoff constraints.

## Evidence and production boundary

G0.7, G1.2a, G1.4 and G1.5 are current synthetic evidence. The raw G1.4 bundle remains external to Git with SHA-256 `bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be`; its semantic evidence digest is `836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694`. The raw G1.5 bundle remains external with SHA-256 `90b2132cbe46edeb2a28e6f9ae81de311807353dd5e0826cbe8d3a6af41a85fb`; its semantic evidence digest is `9b4d6aa41bf2392aac273784b45b28ff88210e05ea04533bf440d6522ad75afa`.

Those raw bundles were not available in the G1.6 ChatGPT execution environment, so G1.6 did not claim a fresh hash/inventory/detached-validator continuity PASS. Historical reports remain non-authoritative where they conflict. The package is research-only and is not part of the add-on runtime, dashboard, `.ankiaddon`, Fast CI or release pipeline. Generated outputs, environments, caches, coverage, build/dist and `rust-oracle/target/` remain untracked.
