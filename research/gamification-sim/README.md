    # Gamification Review simulator

    ## Status

    `CORRECTIVE_COMPLETE_G0_6_RERUN_REQUIRED`

    G0.5 established the canonical Windows AMD64 / CPython 3.11 environment baseline. G0.6a corrected and focused-verified the regular installed-package execution boundary; the full G0.6 functional baseline must still be rerun from the corrective commit, and evidence remains unverified.

    The package was selectively recovered from the frozen historical source. G0.4
    verifies source/target content relationships and isolation only. It does not
    claim that installation, commands, tests, oracles or simulations work in the
    current environment.

    ## Isolation contract

    - package root: `research/gamification-sim/`;
    - no production imports;
    - no root dependency changes;
    - no Fast CI, packaging or release integration;
    - generated outputs and local environments remain ignored;
    - no Anki profile, collection, revlog, token or production data is included.

    ## Recovered structure

    ```text
    configs/       bounded historical inputs
    contracts/     FSRS and Rust-oracle interfaces/reference inputs
    fixtures/      deterministic golden corpus
    personas/      synthetic independent-day workload personas
    scenarios/     ordinary, edge, control, abuse and regression cases
    schemas/       active schemas
    archive/       superseded schema provenance
    src/           Python package
    tests/         Python tests
    rust-oracle/   isolated Rust implementation and lockfile
    ```

    ## Available commands

    The regular installed package exposes the following 17 command surfaces. Console and module help were focused-verified during G0.6a; only bounded validation probes were executed, while sweep, sensitivity, population and longitudinal runs remain out of scope.

- `gamification-sim compare-scenarios ...` / `py -m gamification_sim compare-scenarios ...`
- `gamification-sim evaluate ...` / `py -m gamification_sim evaluate ...`
- `gamification-sim list-parameter-sets ...` / `py -m gamification_sim list-parameter-sets ...`
- `gamification-sim run-longitudinal ...` / `py -m gamification_sim run-longitudinal ...`
- `gamification-sim run-population ...` / `py -m gamification_sim run-population ...`
- `gamification-sim run-scenario ...` / `py -m gamification_sim run-scenario ...`
- `gamification-sim run-scenarios ...` / `py -m gamification_sim run-scenarios ...`
- `gamification-sim run-sensitivity ...` / `py -m gamification_sim run-sensitivity ...`
- `gamification-sim run-sweep ...` / `py -m gamification_sim run-sweep ...`
- `gamification-sim validate-longitudinal-config ...` / `py -m gamification_sim validate-longitudinal-config ...`
- `gamification-sim validate-personas ...` / `py -m gamification_sim validate-personas ...`
- `gamification-sim validate-scenarios ...` / `py -m gamification_sim validate-scenarios ...`
- `gamification-sim validate-sweep ...` / `py -m gamification_sim validate-sweep ...`
- `gamification-sim verify-examples ...` / `py -m gamification_sim verify-examples ...`
- `gamification-sim verify-fsrs-reference ...` / `py -m gamification_sim verify-fsrs-reference ...`
- `gamification-sim verify-report ...` / `py -m gamification_sim verify-report ...`
- `gamification-sim verify-rust-oracle ...` / `py -m gamification_sim verify-rust-oracle ...`

    The installed CLI resolves repository-only assets through a validated research workspace supplied by `--research-root`, `GAMIFICATION_SIM_RESEARCH_ROOT` or bounded checkout discovery.

## Historical source

    `48298d02c6871df0ffa112d862d9b2af629c523f:research/gamification-sim/`

    ## What G0.4 verified

    - manifest-approved files were recovered to approved paths;
    - exact imports match frozen Git blobs;
    - adapted files contain only approved prefixes plus exact historical bodies;
    - generated outputs were not imported;
    - package isolation from production, CI and release paths was preserved.

    ## What G0.4 did not verify

    - dependency installation or interpreter/toolchain compatibility;
    - Python imports, tests or command execution;
    - Rust build or differential parity;
    - scenario, sweep, population or longitudinal behavior;
    - FSRS reference behavior;
    - historical PASS statements, numerical results or digests.

    ## Environment status — G0.5 Complete

    The canonical baseline is Windows AMD64, CPython 3.11.9 and exact stable Rust 1.97.1 on `x86_64-pc-windows-msvc`. Python dependencies are exact-pinned and SHA-256 locked; a second clean venv completed offline replay, regular local installation and `pip check`. Cargo completed locked online/offline metadata replay without changing `Cargo.lock`.

    See [environment baseline](environment/README.md). This does not claim that CLI commands, tests, simulations or the Rust oracle work.

    ## Installed execution boundary — G0.6a corrective complete

The regular installed package no longer derives the research root from
`__file__` ancestry. Schemas, fixtures, scenarios, personas, configs, contracts
and the Rust oracle remain external canonical workspace assets. Generated
outputs default outside the source tree. The tracked `rust-toolchain.toml`
selects exact Rust 1.97.1 on MSVC; deterministic Cargo commands use
`--locked --offline` and respect caller-provided environment, including
`CARGO_TARGET_DIR`.

Focused verification passed for regular non-editable installation, all 17 CLI
subcommands, 31 golden examples, 26 scenarios, 16 personas,
sweep/longitudinal config validation, 8 corrective tests, 816-item pytest
collection and locked/offline Cargo metadata. The complete Python suite, Rust
build/tests/oracle, parity and evidence were not executed.

See [`../../roadmap/gamification/g0-installed-execution-boundary-correction.md`](../../roadmap/gamification/g0-installed-execution-boundary-correction.md).

## Functional status — G0.6 partial

G0.6 must be rerun from `preflight` on the corrective commit. No
pre-correction PASS checkpoint is inherited.

## Evidence status — G0.7 pending

    G0.7 owns evidence reproduction and the separation of current results from
    historical claims.

    ## Historical reports

    Archived reports:
    - [`../../reports/gamification/historical-source/stage-5-review-simulation-closure.md`](../../reports/gamification/historical-source/stage-5-review-simulation-closure.md)
    - [`../../reports/gamification/historical-source/stage-5-calibration-correction.md`](../../reports/gamification/historical-source/stage-5-calibration-correction.md)

    The later calibration correction has precedence over conflicting earlier
    COMPLETE-era claims.

    ## Open cycling gap

    The cross-horizon 90→365 retention-cycling growth gap remains open. Recovery
    does not select or approve a Review economy candidate.

    ## Generated and untracked outputs

    `outputs/`, virtual environments, caches, coverage, build/dist artifacts and
    `rust-oracle/target/` remain untracked and must not be committed.

    ## Production boundary

    This package is research-only. It is not part of the add-on runtime,
    dashboard, `.ankiaddon`, Fast CI or release pipeline.
