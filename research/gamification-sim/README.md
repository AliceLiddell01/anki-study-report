    # Gamification Review simulator

    ## Status

    `RECOVERED_UNVERIFIED`

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

    The following command surfaces were inferred statically from the recovered
    `pyproject.toml`, `cli.py` and `__main__.py`. They were not executed:

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

    Exact options and required arguments must be checked with the recovered CLI
    only after G0.5 establishes the environment.

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

    ## Environment status — G0.5 pending

    G0.5 must establish a reproducible environment using the recovered historical
    declarations without silently upgrading dependencies.

    ## Functional status — G0.6 pending

    G0.6 owns parse/import checks, Python tests, corpus validation, Rust oracle and
    focused functional verification.

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
