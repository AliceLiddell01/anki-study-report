    # Gamification Review simulator

    ## Status

    `COMPLETE_CURRENT_EVIDENCE_REPRODUCED_WITH_OPEN_GAP`

    G0.7 reproduced the canonical current evidence on Windows AMD64, preserved and independently verified the raw artifact, and handed the reproduced cycling gap to G1.

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

    The regular installed package exposes the following 17 command surfaces. G0.6 verified the functional commands; G0.7 executed the canonical sweep, sensitivity, bounded population and persistent-card longitudinal evidence contours.

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

## Functional status — G0.6 Complete

The installed package, CLI surface, full recovered Python suite, deterministic
corpus, Rust check/build/tests, Python/Rust parity and FSRS reference passed in
the exact G0.5 environment after the G0.6a correction.

See [functional baseline](functional/README.md) and the
[installed execution boundary correction](../../roadmap/gamification/g0-installed-execution-boundary-correction.md).

The corrective checkpoint remains part of the audit trail, but no
pre-correction PASS state was inherited.

## Evidence status — G0.7 Complete

`CURRENT_EVIDENCE_REPRODUCED`

See [`evidence/README.md`](evidence/README.md) and
[`../../roadmap/gamification/g0-evidence-reproduction.md`](../../roadmap/gamification/g0-evidence-reproduction.md).
The canonical raw artifact is retained in GitHub Actions; only normalized records
are committed.

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
