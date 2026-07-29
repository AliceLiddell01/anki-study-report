# G4.3 v2 — Corrective candidate economy protocol closeout

**Status:** `COMPLETE`
**Publication state:** `FROZEN_PRE_SCREENING`
**Target branch:** `gamification`
**Corrective PR:** `#168`
**Merge SHA:** `9a13cc40a2bae9ece4377a3781452beab46116f2`
**Post-merge report:** [`reports/research/g4-3-candidate-economy-protocol-v2-closeout-2026-07-29.md`](../../reports/research/g4-3-candidate-economy-protocol-v2-closeout-2026-07-29.md)

```text
G4.3: COMPLETE
G4.3 v1: SUPERSEDED_PRE_EXECUTION
G4.3 v1 results: NOT_AVAILABLE
G4.3 v2: FROZEN_PRE_SCREENING
G4.4: NEXT / NOT STARTED
screening: NOT STARTED
simulation: NOT STARTED
Review winner: NONE
production: PROHIBITED
```

## Corrected defects

- false-positive primary denominator is positive context, not total contribution;
- candidate-specific outcomes exist only in matrix gate profiles;
- Review/Learn conversion, marginality, decomposition and crowdout gates are explicit;
- exact 17-step typed evaluation pipeline and nonlinear order are frozen;
- recommendation candidates use per-domain bounding before combination;
- daily scale covers 5/10/30/100/300 Reviews and 1/5/10/30 Learn confirmations;
- exact G4.1/G4.2 persona, threat and invariant identities are preserved;
- negative samples refresh dependent digests and must fail with declared error codes;
- cross-artifact and row digest references are validated;
- v1 bytes remain immutable and no result was accessed.

## Frozen inventories

```text
candidates: 19
bundles: 21
hypotheses: 20
hard gates: 29
metrics: 22
pipeline steps: 17
scenarios: 41
matrix expected / unique / missing / extra: 864 / 864 / 0 / 0
negative samples: 40
personas / threats / invariants: 9 / 14 / 28
```

## Frozen digests

```text
protocol: f13f85e627297d328bcd30481924ff139f43c78d84b72f57a2ce6543cdcddd8b
pipeline: 6fe8d3f1b8b830dc258b7ca096428bc2ef53f5354ad2aa4aed2d35a76f04f6d2
scenarios: 83c89cd3667fe866a423f8a2cf9d58ce344030c4e2f65316559d8391de21edb7
matrix: 27a511b0601b259de6a75d62b6900193ead6fe38deea04e9d20230980af9ff0f
validator: core-economy-protocol-v2-validator-3
generator: core-economy-protocol-v2-generator-2
```

## Validation contract

Required local checkpoint:

```powershell
$env:PYTHONPATH = "research/gamification-sim/src"
node scripts/run_python.mjs -m gamification_sim.core_economy_protocol_v2 --research-root research/gamification-sim --repository-root . --regenerate --validate --check-byte-identical
node scripts/run_python.mjs -m pytest research/gamification-sim/tests/test_core_economy_protocol_v2.py -q
```

Full research suite is not required because shared helpers are unchanged. G4.4 screening, economy simulation, frontend/package checks and Docker E2E are explicitly not run.

## G4.4 entry contract

G4.4 remains blocked until a separate stage is explicitly opened. Execution must use exact merged G4.3 v2 publication merge SHA `9a13cc40a2bae9ece4377a3781452beab46116f2` and the four digests above. Any substantive protocol change after result access requires a new version and a full replacement run.
