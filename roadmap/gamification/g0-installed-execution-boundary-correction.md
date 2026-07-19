# G0.6a — Installed execution boundary correction

## Status

`CORRECTIVE_COMPLETE_G0_6_RERUN_REQUIRED`

This corrective task fixes the installed-package execution boundary that blocked
G0.6 pytest collection. It does not complete G0.6 and does not verify the full
functional baseline or historical evidence.

## Triggering G0.6 failure

The first G0.6 run passed preflight, environment reuse, installed import and CLI
surface checks, then failed during pytest collection.

Two test modules imported the regular installed package from `site-packages`,
but the package resolved the longitudinal schema as:

```text
<venv>/Lib/schemas/review-longitudinal-v0.1.schema.json
```

The expected schema remained a repository research asset under
`research/gamification-sim/schemas/`.

Failure classification:

```text
PARTIAL_TEST_COLLECTION_FAILED
```

## Recorded refs

```text
branch: gamification
corrective base: 0cbd8a69a53b6c176593f91d76ed899bbcc51d81
G0.5 environment commit: 0cbd8a69a53b6c176593f91d76ed899bbcc51d81
G0.4 recovery commit: c7f7bd964825a5277cc9dc886dc7775f5f9eaac6
master observed by G0.6 preflight: 359c26f82a9ee78c8e27603f9ded5ca9bef2c71e
core observed by G0.6 preflight: 52c03c340c7a98b72d869ea42d6a9a46d56233e7
```

## Root-cause analysis

Recovered source code used source-layout-relative assumptions such as:

```python
Path(__file__).resolve().parents[2]
```

and a global `PACKAGE_ROOT` derived from installed module ancestry.

Those assumptions resolve correctly only in the checkout layout:

```text
research/gamification-sim/
├── src/gamification_sim/
├── schemas/
├── fixtures/
├── scenarios/
├── personas/
├── configs/
├── contracts/
└── rust-oracle/
```

After regular installation, `__file__` is under
`<venv>/Lib/site-packages/gamification_sim/`, so the inferred root becomes
`<venv>/Lib`.

The audit found 40 path/toolchain findings across 9 modules:

- 26 workspace-asset literals;
- 20 `PACKAGE_ROOT` references;
- 6 installed-module ancestry references;
- 2 hard-coded GNU stable toolchain references;
- 2 home-directory Cargo lookup references.

The Rust boundary also hard-coded:

```text
+stable-x86_64-pc-windows-gnu
```

which conflicted with the G0.5 canonical toolchain:

```text
1.97.1-x86_64-pc-windows-msvc
```

## Audited path assumptions

Corrected modules:

```text
src/gamification_sim/cli.py
src/gamification_sim/fsrs_reference.py
src/gamification_sim/longitudinal_config.py
src/gamification_sim/longitudinal_runner.py
src/gamification_sim/population.py
src/gamification_sim/rust_oracle.py
src/gamification_sim/scenario_schema.py
src/gamification_sim/sweep.py
```

New central boundary:

```text
src/gamification_sim/workspace.py
```

`matched_analysis.py` retains explicit caller-provided package roots and no
longer receives a root inferred from installed module ancestry.

## Chosen execution-boundary model

The correction separates:

```text
A. installed Python package code
B. validated external research workspace assets
C. generated execution artifacts
```

No canonical corpus, schema or Rust-oracle copies were added to the wheel.

## Import-package resources

The installed distribution contains Python package code only. Schemas, fixtures,
scenarios, personas, configs, contracts and the Rust oracle remain canonical
repository workspace assets.

A minimal build copy used for verification contained only:

```text
pyproject.toml
README.md
src/gamification_sim/
```

This prevented regular installation from accidentally finding external research
assets beside the build source.

## External research workspace

`ResearchWorkspace` validates a bounded root using required marker files.

Resolution priority:

1. explicit `ResearchWorkspace` or path;
2. `GAMIFICATION_SIM_RESEARCH_ROOT`;
3. bounded discovery from explicit anchors and the current working directory.

The CLI exposes:

```text
--research-root PATH
```

Invalid explicit roots fail instead of silently falling back to an unrelated
checkout. Parent traversal and symlink traversal are rejected by the workspace
path boundary.

## Generated artifact boundary

Generated output no longer defaults to the research source tree or
`site-packages`.

Default output root:

```text
<system temp>/anki-study-report/gamification-sim/outputs
```

Explicit override:

```text
GAMIFICATION_SIM_OUTPUT_DIR
```

Verification used:

```text
.git/g0_6a_corrective/verify/
```

including isolated temp, Hypothesis, Cargo target, output, venv and build-source
directories.

No generated artifact remained under `research/gamification-sim/` after the
successful focused verification.

## CLI contract

All 17 existing subcommands remain present for both:

```text
gamification-sim --help
python -m gamification_sim --help
```

Invocation without a subcommand returns the expected argparse usage exit code
`2`.

Out-of-scope commands remained present but were not executed:

```text
run-sweep
run-sensitivity
run-population
run-longitudinal
```

## Schema/config resolution

The central workspace boundary now resolves:

```text
review-scenario-v0.2.schema.json
review-persona-v0.1.schema.json
review-sweep-v0.1.schema.json
review-longitudinal-v0.1.schema.json
fixtures/golden_cases.json
scenarios/
personas/
configs/
contracts/
rust-oracle/Cargo.toml
```

Focused installed CLI probes passed:

```text
golden examples: 31
scenarios: 26
personas: 16
sweep config: PASS
longitudinal config: PASS
```

No reward formula, expected value, fixture, persona, scenario, config, contract
or schema semantic content changed.

## Rust toolchain and Cargo contract

Python code no longer hard-codes the GNU stable toolchain or a user-home Cargo
path.

Cargo is resolved through the active rustup proxy. The tracked
`rust-toolchain.toml` selected:

```text
1.97.1-x86_64-pc-windows-msvc
```

Deterministic commands use:

```text
--locked
--offline
```

Caller-provided `CARGO_TARGET_DIR` remains authoritative.

Focused Cargo metadata verification passed:

```text
registry dependency packages: 48
local workspace packages: 1
total packages: 49
workspace package: gamification-rust-oracle 0.1.0
Cargo.lock changed: false
build executed: false
oracle executed: false
```

The 48 registry package name/version pairs exactly matched the committed G0.5
Rust environment record.

## Regular-install verification

A fresh CPython 3.11.9 venv was created under the isolated verification root.

Dependencies were installed offline from the G0.5 wheelhouse using the exact
hash-checked lock. The local project was installed regularly with:

```text
--no-index
--no-deps
--no-build-isolation
```

Verified installed state:

```text
gamification-sim: 0.1.0
editable: false
locked dependencies: 17
total distributions: 18
pip check: PASS
module origin: fresh venv site-packages
PYTHONPATH/source injection: false
```

## Focused tests

Eight execution-boundary tests passed:

```text
explicit workspace validation
bounded checkout fallback
invalid explicit workspace rejection
parent traversal rejection
external default output root
explicit output override
locked/offline Cargo command construction
CARGO_TARGET_DIR preservation
```

Verification invocation used:

```text
-B
-I
--assert=plain
--import-mode=importlib
-p no:cacheprovider
```

Result:

```text
selected: 8
passed: 8
pytest exit code: 0
```

## Pytest collection regression

The full research test directory was collected against the regular installed
package without `PYTHONPATH`, editable installation or source injection.

```text
tracked tests/ files: 27
tracked test_*.py modules: 26
support files: tests/conftest.py
collected items: 816
collection: PASS
production tests collected: false
```

The complete Python test suite was not executed by this corrective task.

## Repository isolation

Postconditions after focused verification:

```text
corrective source digest unchanged: true
changed path allowlist unchanged: true
git diff --check: PASS
generated research-tree pollution: none
```

Temporary environments, logs and quarantine data remain only below:

```text
.git/g0_6a_corrective/
```

## Source/declaration immutability

The immutable snapshot remained unchanged:

```text
files: 57
digest: 19319689121ad986d1350a1afe7305152d0a29feee8da6c1512914f36905a8b5
```

Unchanged declarations:

```text
pyproject.toml
rust-oracle/Cargo.toml
rust-oracle/Cargo.lock
```

No dependency version or lock resolution was changed.

## Not executed

```text
full Python test suite
run-sweep
run-sensitivity
run-population
run-longitudinal
Rust build
Rust check
Rust tests
Rust oracle
FSRS parity
historical evidence reproduction
Fast CI
Docker
real-Anki E2E
production integration
```

## Limitations

- The corrective verification covers Windows AMD64, CPython 3.11.9 and
  `x86_64-pc-windows-msvc`.
- It proves the installed execution boundary and collection regression, not
  full simulator correctness.
- G0.6 PASS states observed before the correction cannot be carried forward
  without rerunning every G0.6 checkpoint on the corrective commit.
- G0.7 and G1 remain blocked.

## Entry conditions for G0.6 rerun

After this corrective commit is pushed:

1. record the corrective commit SHA;
2. recreate or reinstall the local project regularly using the unchanged G0.5
   dependency lock;
3. do not resolve or upgrade dependencies;
4. restart G0.6 from `preflight`;
5. rerun every checkpoint;
6. do not inherit PASS status from the pre-correction run;
7. keep G0.7 and G1 blocked until G0.6 closes.

## Final state

```text
G0.5: Complete
G0.6: Partial — corrective complete; full rerun required
G0.7: Not started / blocked
G1: Blocked by G0
production integration: prohibited
```
