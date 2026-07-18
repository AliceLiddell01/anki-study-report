# G0.5 Reproducible environment

## Status

`COMPLETE` for environment and dependency reproducibility.

This status does not imply functional verification, test PASS, oracle parity,
simulation validity, evidence reproduction or production readiness.

## Recorded refs

- Gamification input and environment source: `c7f7bd964825a5277cc9dc886dc7775f5f9eaac6`;
- `origin/gamification` at preflight: `c7f7bd964825a5277cc9dc886dc7775f5f9eaac6`;
- master observation: `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e`;
- core observation: `219fe515ef58e55bc3b8866b4ec4832148126df3`;
- frozen historical source: `48298d02c6871df0ffa112d862d9b2af629c523f`.

The final G0.5 commit SHA is recorded by the operator state and push verification
because a commit cannot contain its own resulting SHA.

## Scope

G0.5 established one local reference environment for the isolated research
package. It changed only allowed environment records, the exact Rust toolchain
pin and current Gamification documentation.

## Canonical environment decision

- OS family: Windows;
- architecture: AMD64;
- Python: CPython `3.11.9` on the 3.11 line;
- Python profile: runtime + test + fsrs;
- Rust host: `x86_64-pc-windows-msvc`;
- exact stable Rust channel: `1.97.1`.

This is one reference baseline, not a cross-platform support claim.

## Python declaration audit

Recovered declarations remained unchanged:

- `setuptools>=77.0.3`;
- `jsonschema>=4.26,<5`;
- `pytest>=8,<10`;
- `hypothesis>=6.156.6,<7`;
- `fsrs==6.3.1`;
- `requires-python >=3.11`.

`pyproject.toml` blob: `1bf09169f1dd8b2c298474a862cac23783ef4eb6`.
SHA-256: `6ebf649657263df846eb924af3004b4e67c753f96713e1a987900e0a3707d39c`.

## Python resolver result

A clean CPython 3.11 venv resolved 17 exact distributions from the
official PyPI index using wheel-only selection. Every selected artifact had a
SHA-256 digest; no yanked, VCS, local or editable dependency was accepted.

Resolver pip: `24.0`.

## Python hash-locked baseline

The platform-specific lock is
[`../../research/gamification-sim/environment/python-windows-amd64-py311.lock.txt`](../../research/gamification-sim/environment/python-windows-amd64-py311.lock.txt).

It contains exact versions and the selected wheel SHA-256 for pip, setuptools,
all direct requirements and every transitive dependency. Lock SHA-256:
`7bb12909719c745e5844cc906a7137a0ea47bceeb034baafccfbc7fe5804c3ad`.

## Python clean replay

A second venv was created independently. It installed only from the local
wheelhouse with `--no-index`, `--require-hashes` and `--no-deps`. Resolver and
replay name/version sets matched, and the verified wheelhouse hashes matched the
lock.

## Python package installation metadata

The local package was installed regularly, not editable, with `--no-deps` and
`--no-build-isolation`. `pip check` passed. Package imports and commands were not
executed.

Normalized record:
[`../../research/gamification-sim/environment/python-windows-amd64-py311.json`](../../research/gamification-sim/environment/python-windows-amd64-py311.json).

## Rust declaration audit

Recovered direct dependencies and edition remained unchanged. `Cargo.toml` blob:
`2d579b19be54073cef44288084a138e32a1557c2`, SHA-256 `83be93249db480bc5c23d022904ca4ce546a8bf9e0c3b5947839b89ffd3e1956`.
`Cargo.lock` blob: `bd020e5a3b0dddb8202d567fcbeb87e9103e7cca`, SHA-256
`73d610449ec39eba62cabdb4dbc0ad9e6f2f97afed4f83d2e60539c69536aaa1`.

## Rust exact toolchain

[`../../research/gamification-sim/rust-toolchain.toml`](../../research/gamification-sim/rust-toolchain.toml)
pins exact stable Rust `1.97.1` with the minimal profile. The detected
host is `x86_64-pc-windows-msvc`. Rust 2024 edition's minimum release requirement is
satisfied.

## Cargo locked/offline replay

- `cargo fetch --locked`: PASS;
- `cargo metadata --locked`: PASS;
- `cargo metadata --locked --offline`: PASS;
- registry packages in the graph: 48;
- online/offline graphs equal: yes;
- `Cargo.lock` changed: no;
- path/git dependencies: none except the local root package.

Normalized record:
[`../../research/gamification-sim/environment/rust-windows-host.json`](../../research/gamification-sim/environment/rust-windows-host.json).

## Source declaration immutability

`pyproject.toml`, `Cargo.toml` and `Cargo.lock` retained their original Git blobs
and SHA-256 values. G0.5 did not widen, narrow or upgrade declarations.

## Isolation audit

No production runtime, dashboard, API, workflow, package, release, Core or root
dependency path changed. Venvs, wheelhouse, raw reports and Cargo cache stayed
under `.git/g0_5_environment/`.

## Security and sanitization

Tracked records contain no credentials, usernames, home paths, proxy values,
tokens, private index URLs or raw artifact URLs. Python was restricted to
official PyPI. Cargo used an isolated `CARGO_HOME` and crates.io registry sources.

## What was not executed

- Python package imports;
- CLI commands;
- pytest or Hypothesis tests;
- scenario/schema/FSRS/sweep/population/longitudinal behavior;
- Cargo build, check, test or run;
- Rust oracle execution;
- historical evidence reproduction;
- Fast CI or Docker/real-Anki E2E.

## Limitations

- Python lock: Windows AMD64 and CPython 3.11 only;
- Rust record: detected Windows host only;
- artifact availability outside the local wheelhouse was not vendored;
- functional and numerical correctness remain unknown.

## Recorded guarantees

- clean Python resolver and independent replay environments;
- all Python distributions exact-pinned and SHA-256 locked;
- offline wheelhouse replay and `pip check` PASS;
- regular local installation metadata verified without imports;
- exact stable Rust toolchain pinned;
- locked online/offline Cargo metadata agreed;
- recovered declarations and lock files unchanged;
- production integration remains prohibited.

## Entry conditions for G0.6

G0.6 must use an environment replayed from the recorded baseline. It may then
perform focused imports, command probes, Python tests, corpus checks and Rust
oracle verification. It must not reinterpret G0.5 as functional evidence.

## Next step

`G0.6 — Functional baseline verification`
