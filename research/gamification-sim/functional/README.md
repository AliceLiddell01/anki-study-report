# Gamification simulator functional baseline

## Status

- environment: `REPRODUCIBLE_ENVIRONMENT_ESTABLISHED`
- functional: `FUNCTIONAL_BASELINE_VERIFIED`
- evidence: `NOT_REPRODUCED`
- production: `PROHIBITED`

## Scope

This directory records the G0.6 functional baseline for the isolated Review XP
research simulator on Windows AMD64, CPython 3.11.9 and Rust 1.97.1.
It verifies executable behavior, not the effectiveness or production suitability
of the reward model.

## Source and environment

- input commit: `13bc3f3c616459ab0ba7a2ec3be53e7dd3158e64`
- Python environment: [`../environment/README.md`](../environment/README.md)
- normalized record: [`windows-amd64-py311-rust-1.97.1.json`](windows-amd64-py311-rust-1.97.1.json)
- Python: CPython `3.11.9`, `cpython-311`
- Rust: `1.97.1-x86_64-pc-windows-msvc`

## Package and CLI

The regular, non-editable `gamification-sim 0.1.0` installation imported from
replay `site-packages`. Distribution metadata, console-script entry point,
console help, module help and the expected argparse usage error passed.

## Python tests

- collected: 819
- passed: 817
- failed: 0
- errors: 0
- skipped: 2 expected Windows symlink capability skips
- xfail/xpass: 0
- JUnit SHA-256: `e5a71c0d30f2fee5242b3e9087e88db179b97e9667cb070df2f1dd98cf789060`

## Golden cases and scenario corpus

- golden cases: 31/31 PASS
- scenarios: 26/26 PASS
- category distribution: ordinary 6, edge 7, controls 6, abuse 6, regression 1
- failed assertions: 0
- bounded JSON outputs reproduced identically on a second run

## Config validation

The 16-persona catalog, bounded sweep config and bounded longitudinal config
validated. Sweep, sensitivity, population and longitudinal simulations were not
executed.

## Rust build and tests

- `cargo check --locked --offline`: PASS
- `cargo build --locked --offline`: PASS
- `cargo test --locked --offline`: PASS
- Rust tests passed: 2
- `Cargo.lock` changed: no

## Python/Rust parity

Every recovered parameter candidate completed the committed differential corpus
twice with zero semantic mismatches and stable canonical output.

## FSRS reference

The committed Python/Rust FSRS trajectory contract passed twice with stable
output and no state mismatches. This is a functional reference check, not
historical calibration evidence.

## Determinism replay

`verify-examples`, `list-parameter-sets`, `validate-scenarios`,
`run-scenarios`, per-candidate Rust parity and the FSRS reference produced
stable replay digests.

## Repository isolation

All logs, JUnit, temporary files, Hypothesis storage and Cargo targets remained
under `.git/g0_6_functional/`. Source, tests, fixtures, declarations and lock
files were unchanged.

## Verified

G0.6 verifies the installed package, CLI surface, recovered Python suite,
bounded deterministic corpus, exact Rust build/test contour, cross-runtime
parity and FSRS reference behavior in the G0.5 environment.

## Not verified

G0.6 does not run parameter sweeps, sensitivity, populations, longitudinal
calibration, historical evidence reproduction, production tests, Fast CI,
Docker or real-Anki E2E.

## Known cycling gap

The 90→365-day retention-cycling gap remains open. Passing G0.6 does not select
or approve a production reward candidate.

## G0.7 entry conditions

G0.7 may use this exact functional baseline to reproduce evidence and compare
current results with historical reports. It must not reinterpret functional PASS
as proof of learning effectiveness.
