# G0.6 Functional baseline verification

## Status

`COMPLETE` for the bounded functional baseline.

This status verifies current executable behavior in the exact G0.5 environment.
It does not reproduce historical calibration evidence, close the retention-cycling
gap or approve production integration.

## Recorded refs

- Gamification input: `13bc3f3c616459ab0ba7a2ec3be53e7dd3158e64`;
- canonical branch: `gamification`;
- G0.5 environment: Windows AMD64, CPython `3.11.9`, Rust `1.97.1`;
- final G0.6 commit: recorded by operator state and push verification.

## Scope

G0.6 verified installed package import and metadata, CLI surfaces, the recovered
Python suite, bounded deterministic corpus commands, exact-toolchain Rust
check/build/tests, Python/Rust differential parity and the FSRS reference
contract. No research semantics were edited.

## Canonical environment

The verification reused the G0.5 replay environment: CPython `3.11.9`
with 17 exact distributions and Rust `1.97.1-x86_64-pc-windows-msvc`.

## Package import and metadata

`gamification-sim 0.1.0` imported from replay `site-packages`. The regular,
non-editable distribution and `gamification_sim.cli:main` console script were
present.

## CLI surface

Console-script and module help passed with all 17 recovered subcommands.
A no-argument invocation produced the expected argparse usage error, not an
internal exception. Evidence-producing commands remained unexecuted.

## Pytest collection/result

- collected: 819;
- passed: 817;
- failed: 0;
- errors: 0;
- skipped: 2 expected Windows symlink capability skips
- xfail/xpass: 0;
- JUnit SHA-256: `e5a71c0d30f2fee5242b3e9087e88db179b97e9667cb070df2f1dd98cf789060`.

## Golden examples

31/31 bundled golden cases passed twice with identical canonical JSON.

## Scenario corpus

26 unique scenarios validated and executed with the expected category
distribution. Failed scenarios: 0. Failed assertions: 0.
Scenario run digest: `d6325c8fba8c3c20e68f8c724f736883f269892c6a2aba532d7ea1221f125de5`.

## Personas and configs

16 personas validated. The bounded sweep and longitudinal configs parsed
successfully. No sweep, population or longitudinal simulation ran.

## Determinism

All bounded Python command outputs, every candidate Rust parity result and the
FSRS reference output were identical on replay.

## Rust compilation/tests

- cargo check locked/offline: PASS;
- cargo build locked/offline: PASS;
- cargo test locked/offline: PASS;
- Rust tests passed: 2;
- Cargo.lock changed: no.

## Rust oracle parity

All 17 recovered parameter IDs passed the full
differential corpus twice with zero semantic mismatches.

## FSRS reference

The committed FSRS trajectory contract passed twice with stable output and no
state mismatch. This check is functional and does not reproduce Stage 5
calibration evidence.

## Repository isolation

Runtime artifacts remained under `.git/g0_6_functional/`. No production,
workflow, package/release, Core or root dependency path changed.

## Source/declaration immutability

`pyproject.toml`, `Cargo.toml`, `Cargo.lock`, Python source, tests, fixtures,
scenarios, personas, configs, contracts and schemas remained unchanged.

## Not executed

Fast CI, Docker/real-Anki E2E, production tests, sweeps, sensitivity,
population, longitudinal/calibration runs and historical evidence reproduction
were intentionally not executed.

## Known open gap

The 90→365-day retention-cycling growth issue remains open. `R-CURRENT` remains
a regression reference, not a production recommendation.

## Limitations

The recorded baseline covers one Windows AMD64 / CPython 3.11.9 / Rust 1.97.1
environment. Functional PASS does not establish cross-platform portability,
learning effectiveness or production readiness.

## Recorded guarantees

- exact G0.5 environment reused;
- installed package and CLI surfaces passed;
- recovered Python suite passed without semantic changes;
- deterministic corpus, Rust parity and FSRS reference passed;
- Rust check/build/tests used exact locked/offline inputs;
- repository isolation and declaration immutability held;
- evidence remains `NOT_REPRODUCED`;
- production remains prohibited.

## Entry conditions for G0.7

G0.7 may reproduce the bounded current evidence only from this exact environment
and functional baseline. Historical reports remain provenance until independently
reproduced.

## Next step

`G0.7 — Evidence reproduction`
