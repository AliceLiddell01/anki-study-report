    # G0.4 Selective research recovery

    ## Status

    `COMPLETE` for selective content recovery.

    This status proves manifest reconciliation, exact/adapted content relationships
    and isolation. It does not prove executability, test PASS, evidence reproduction
    or production readiness.

    ## Recorded refs

    - master observation: `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e`;
    - gamification input: `efe822e8c44855717380c6a63066de8358e98360`;
    - gamification batch tip before closure: `8526bf6b6e172f9df8a673a8efb9dc09db406bdd`;
    - core observation: `b3055ac4992c1658101d6d837a9aa74ab1274d9a`;
    - historical branch observation: `unavailable locally`;
    - frozen source: `48298d02c6871df0ffa112d862d9b2af629c523f`.

    The closure commit SHA is recorded by the local operator state and final command
    output because a commit cannot contain its own resulting SHA.

    ## Scope

    G0.4 actioned all 128 G0.3 manifest rows, recovered 127 historical-derived
    targets and deferred `docs/gamification/progression-foundation.md` to G4.
    No production, Core, workflow, root dependency, package or release path changed.

    ## Transfer strategy

    Local Git read exact bytes from `48298d02c6871df0ffa112d862d9b2af629c523f:<source path>`. Exact imports were
    written as bytes and verified by Git blob identity. Approved adaptations consist
    only of fixed provenance/status prefixes followed by the exact complete frozen
    body. Three indexes/foundations were rewritten as current canonical status
    documents without adding reward formulas.

    ## Manifest reconciliation

    ```text
    manifest rows: 128
    terminal ledger rows: 128
    IMPORT_AS_IS: 115
    IMPORT_WITH_ADAPTATION: 8
    REWRITE: 3
    ARCHIVE_SUPERSEDED: 1
    DEFER: 1
    recovered targets: 127
    deferred: 1
    blocked: 0
    pending: 0
    unexpected: 0
    ```

    Detailed row accounting is in
    [`g0-recovery-ledger.md`](g0-recovery-ledger.md).

    ## Batch results

    ### A — Canonical documentation

    Three canonical documents were rewritten and five Review specifications received
    approved provenance headers. Historical formula-bearing bodies remain exact
    suffixes.

    ### B — Contracts and schemas

    Isolation rules, configs, contracts and active schemas were recovered exactly.
    Scenario schema v0.1 was preserved exactly only under
    `research/gamification-sim/archive/schemas/`; the active old path was not created.

    ### C — Package metadata and Python source

    Python source was recovered exactly. `pyproject.toml` received only the approved
    comment prefix; dependencies and metadata below it remain exact historical bytes.

    ### D — Scenarios and fixtures

    Recovered exactly: 1 fixture, 26 scenarios and 16 synthetic personas.

    ### E — Tests and oracles

    Recovered exactly: 27 Python test paths and 3 Rust-oracle assets. Existence is not
    PASS evidence.

    ### F — Historical evidence

    Two reports were moved to `reports/gamification/historical-source/` with archive
    provenance headers and exact historical bodies. The later calibration correction
    has precedence over conflicting earlier COMPLETE-era claims.

    ## Exact-content verification

    Exact assets use matching source and target Git blob SHA. Adapted files were
    checked as `approved prefix + byte-identical frozen body`. No line-ending,
    whitespace, JSON-key, expected-value or dependency normalization was applied.

    ## Adaptation semantic-diff audit

    Allowed changed hunks are provenance/status prefixes and canonical placement.
    Formula-bearing historical lines changed: **no**. Reward semantics changed:
    **no**. Coefficients, thresholds, caps, taxonomy, eligibility, algorithms and
    acceptance gates changed: **no**.

    ## Canonical rewrites

    - `docs/gamification/README.md`: current candidate/archive/gate index;
    - `docs/gamification/anki-xp-foundation.md`: domain-status boundary only;
    - `research/gamification-sim/README.md`: operational index marked
      `RECOVERED_UNVERIFIED`.

    ## Deferred assets

    `docs/gamification/progression-foundation.md` was not transferred. Gate:
    `G4_ECONOMY`.

    ## Isolation verification

    - no production imports or payload/API changes;
    - no root dependencies;
    - no Fast CI, `.ankiaddon`, packaging or release integration;
    - no generated outputs, environments, caches or Rust target;
    - no Anki collection/revlog, profile, token or telemetry data.

    ## Historical evidence placement

    Historical reports are separated from current docs under
    `reports/gamification/historical-source/`. They are not active sources of truth
    until G0.7 reproduces evidence.

    ## What was not executed

    Fast CI, Docker E2E, real-Anki E2E, Python tests, Rust build/tests, scenario,
    sweep, population, longitudinal, FSRS-reference and Rust-oracle commands were
    intentionally not run.

    ## Risks for G0.5/G0.6/G0.7

    - historical dependencies/toolchains may not install unchanged;
    - parse/import/test failures may reveal frozen defects;
    - historical expected values and digests remain unverified;
    - cross-horizon retention cycling remains open;
    - `R-CURRENT` remains a regression reference, not a production candidate.

    ## Recorded guarantees

    - G0.3 manifest was not changed;
    - no merge, rebase, cherry-pick or force operation was used;
    - `master`, `core` and the historical source were not modified by G0.4;
    - no Pull Request was created;
    - production integration remains prohibited.

    ## Batch commits

    - A: `77f15f3972c7f834c5f46e132353a6da02411896` — docs: recover canonical gamification specifications
- B: `11de3f4941f84dff0e11511ec6f8322ded202cc2` — research: recover gamification contracts and schemas
- C: `cf97b62a8c8fc95d5bdaccbc5192802b41e7a628` — research: recover gamification simulator sources
- D: `09dbbdb05bc1ec977f90643d6d25fc5af6612f92` — research: recover gamification scenarios and fixtures
- E: `1582991b6fc6f5eeec2a000121a313e6a67ba52f` — research: recover gamification tests and oracles
- F: `8526bf6b6e172f9df8a673a8efb9dc09db406bdd` — docs: archive historical gamification evidence

    ## Next step

    `G0.5 — Reproducible environment`
