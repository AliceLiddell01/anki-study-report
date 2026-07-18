# Gamification simulator environment

## Status

- environment: `REPRODUCIBLE_ENVIRONMENT_ESTABLISHED`
- functional: `NOT_VERIFIED`
- evidence: `NOT_REPRODUCED`

## Scope

This directory records one canonical G0.5 reference environment for the isolated
Gamification research package. It does not claim cross-platform portability or
functional correctness.

## Canonical platform

- Windows AMD64
- CPython 3.11.9 on the Python 3.11 line
- profile: runtime + test + fsrs
- Rust host: `x86_64-pc-windows-msvc`
- exact stable Rust: `1.97.1`

## Python baseline

- lock: [`python-windows-amd64-py311.lock.txt`](python-windows-amd64-py311.lock.txt)
- normalized record: [`python-windows-amd64-py311.json`](python-windows-amd64-py311.json)
- resolver pip: `24.0`
- resolved distributions: 17
- artifact policy: wheel-only, exact versions, SHA-256 required

## Python replay procedure

The G0.5 operator helper creates disposable environments and a local wheelhouse
under `.git/g0_5_environment/`. The verified replay contour is:

```powershell
py -3.11 -m venv .git/g0_5_environment/python-replay
.git/g0_5_environment/python-replay/Scripts/python.exe -m pip --isolated install `
  --no-index `
  --find-links .git/g0_5_environment/wheelhouse `
  --only-binary=:all: `
  --require-hashes `
  --no-deps `
  -r research/gamification-sim/environment/python-windows-amd64-py311.lock.txt

.git/g0_5_environment/python-replay/Scripts/python.exe -m pip --isolated install `
  --no-index `
  --no-deps `
  --no-build-isolation `
  research/gamification-sim
```

The wheelhouse is intentionally not committed. Recreate it with the G0.5
resolution helper before replaying on a clean machine.

## Rust baseline

- toolchain: [`../rust-toolchain.toml`](../rust-toolchain.toml)
- normalized record: [`rust-windows-host.json`](rust-windows-host.json)
- exact toolchain identifier used by G0.5: `1.97.1-x86_64-pc-windows-msvc`
- recovered declarations: [`../rust-oracle/Cargo.toml`](../rust-oracle/Cargo.toml)
- preserved lock: [`../rust-oracle/Cargo.lock`](../rust-oracle/Cargo.lock)

## Rust replay procedure

```powershell
rustup run 1.97.1-x86_64-pc-windows-msvc cargo fetch `
  --locked `
  --manifest-path research/gamification-sim/rust-oracle/Cargo.toml

rustup run 1.97.1-x86_64-pc-windows-msvc cargo metadata `
  --locked `
  --offline `
  --format-version 1 `
  --manifest-path research/gamification-sim/rust-oracle/Cargo.toml
```

These commands read dependency metadata only. They do not compile or execute the
oracle.

## Source declaration immutability

G0.5 did not change `pyproject.toml`, `Cargo.toml` or `Cargo.lock`. Their Git blob
identities and SHA-256 values are recorded in the normalized environment files.

## What G0.5 verified

- clean CPython 3.11 resolver environment;
- complete wheel-only resolution for runtime, test and fsrs profiles;
- exact version and SHA-256 lock entries for all transitive distributions;
- second clean venv installed from lock and local wheelhouse without an index;
- `pip check` passed;
- regular, non-editable local project installation succeeded without dependency
  re-resolution;
- exact stable Rust toolchain pin;
- Cargo locked online metadata and locked offline metadata agreed;
- recovered Cargo lock remained unchanged.

## What G0.5 did not verify

- Python package imports;
- CLI behavior;
- pytest or Hypothesis behavior;
- schema, scenario, FSRS or longitudinal behavior;
- Rust build, check, tests or oracle execution;
- historical numerical results or evidence.

## Generated local artifacts

Resolver/replay venvs, the wheelhouse, raw local command outputs and the isolated
Cargo cache live under `.git/g0_5_environment/`. They are disposable and are not
committed.

## Security and privacy

The recorded files contain no credentials, usernames, home paths, proxy values,
private indexes, tokens or raw download URLs. Python resolution was restricted to
the official PyPI index. Cargo used an isolated local `CARGO_HOME` and crates.io
registry sources only.

## Cross-platform limitations

The Python lock is specific to Windows AMD64 and CPython 3.11. The Rust record
covers only the detected Windows host. Other operating systems, architectures and
Python minor lines require separate verification.

## G0.6 entry conditions

G0.6 may run only inside a replayed environment matching these records. G0.6 owns
imports, commands, tests, scenarios and oracle behavior. Environment verification
alone is not functional verification.
