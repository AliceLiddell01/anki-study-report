# G0.3 Historical asset inventory

## Status

`COMPLETE`

G0.3 catalogues and classifies the frozen historical source tree. It does not
transfer, execute, repair or validate the historical research package.

Immediate result:

```text
128 tracked assets discovered
128 unique manifest rows
0 historical assets imported
0 production/Core/workflow changes
G0.4 may proceed only from the approved manifest
```

## Recorded refs

| Field | Value |
| --- | --- |
| Repository | `AliceLiddell01/anki-study-report` |
| Recorded at | `2026-07-18` |
| Master | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Gamification input | `589961da04d740913c33bd47d0497ecfe36e52d5` |
| Core | `e4292d090a79b857b81a987c8e0853656f178e0e` |
| Historical branch tip | `48298d02c6871df0ffa112d862d9b2af629c523f` |
| Frozen historical source | `48298d02c6871df0ffa112d862d9b2af629c523f` |
| Historical merge base | `4d197c1037fd66401735e654c6697791364518a4` |
| Source branch drift | none |
| Previous G0.2 tip | `589961da04d740913c33bd47d0497ecfe36e52d5` |
| Manifest | [`g0-historical-asset-manifest.md`](g0-historical-asset-manifest.md) |

The floating historical branch still resolves to the frozen source SHA. Inventory
identity nevertheless uses the exact SHA, never the branch name.

## Scope and non-scope

Included exactly the tracked final-tree files below:

```text
docs/gamification/
research/gamification-sim/
```

Included asset families are concept/specification documents, reports, package
metadata, isolation rules, configs, schemas, contracts, fixtures, scenarios,
personas, Python source/tests, Rust source/manifest/lockfile and committed
reference data.

Excluded from tracked inventory:

- generated `outputs/` trees;
- `.venv`, caches, coverage, build/dist and egg-info;
- `rust-oracle/target/`;
- local simulation reports and temporary JSONL;
- screenshots, Anki profiles, collection/revlog data and `.ankiaddon`;
- external articles and DOI references;
- production add-on code outside the two roots;
- files deleted before the frozen source tip unless a current historical source
  explicitly references them.

## Discovery methodology

1. Re-resolved `master`, `gamification`, `core`, the historical branch and the
   exact source commit.
2. Confirmed the canonical branch was still exactly the G0.2 tip before writes.
3. Compared merge base
   `4d197c1037fd66401735e654c6697791364518a4` with exact source
   `48298d02c6871df0ffa112d862d9b2af629c523f`.
4. Normalized the compare per-file list into a one-time local parser and checked
   uniqueness, roots and family counts.
5. Directly fetched all mandatory historical entry points, all schemas/configs/
   contracts needed for version decisions, package indexes, closure/correction
   reports, representative scenarios/personas, CLI metadata and counting tests.
6. Classified homogeneous bundles structurally. Files not directly fetched were
   not labelled `FULL_CONTENT`.
7. Did not run the package, tests, simulations, Rust oracle or FSRS references.

The one-time parser was not added to the repository.

## Completeness proof

The compare is sufficient as a full tracked-path proof for this frozen source:

- `too_large` was not set;
- the compare completed for all 48 source commits;
- the per-file response contained 128 distinct entries;
- every entry is under one of the two scope roots;
- every scope entry is `added`, proving the tracked roots were absent at the
  historical merge base;
- no branch-wide delta outside the scope roots was returned;
- all mandatory entry points resolve directly at the exact source SHA;
- expected package families and counts agree with the historical indexes and
  counting tests;
- the manifest has 128 rows, 128 unique source paths and no path outside scope.

The compare API reported zero patch statistics for some files, but this was not
interpreted as an empty-file claim. Those files remain `STRUCTURAL` unless their
content was directly fetched.

## Inventory summary

- Total tracked assets: **128**
- `docs/gamification/`: **10**
- `research/gamification-sim/`: **118**
- Unresolved tracked paths: **0**
- Duplicate manifest paths: **0**
- Referenced-but-missing tracked assets confirmed: **0**

### Counts by root

| Value | Count |
| --- | ---: |
| `research/gamification-sim/` | 118 |
| `docs/gamification/` | 10 |

### Counts by package family

| Value | Count |
| --- | ---: |
| `src` | 33 |
| `tests` | 27 |
| `scenarios` | 26 |
| `personas` | 16 |
| `docs` | 10 |
| `schemas` | 5 |
| `rust-oracle` | 3 |
| `configs` | 2 |
| `contracts` | 2 |
| `.gitignore` | 1 |
| `README.md` | 1 |
| `fixtures` | 1 |
| `pyproject.toml` | 1 |

### Counts by asset kind

| Value | Count |
| --- | ---: |
| `PYTHON_SOURCE` | 33 |
| `PYTHON_TEST` | 27 |
| `SCENARIO` | 26 |
| `PERSONA` | 16 |
| `SCHEMA` | 5 |
| `SPECIFICATION` | 5 |
| `CONFIG` | 2 |
| `FOUNDATION_DOC` | 2 |
| `INDEX` | 2 |
| `CLOSURE_REPORT` | 1 |
| `CONTRACT` | 1 |
| `CORRECTION_REPORT` | 1 |
| `FIXTURE` | 1 |
| `ISOLATION_RULE` | 1 |
| `PACKAGE_METADATA` | 1 |
| `REFERENCE_DATA` | 1 |
| `RUST_LOCKFILE` | 1 |
| `RUST_MANIFEST` | 1 |
| `RUST_SOURCE` | 1 |

### Counts by evidence status

| Value | Count |
| --- | ---: |
| `UNKNOWN_UNTIL_EXECUTION` | 116 |
| `CURRENT_CANDIDATE` | 6 |
| `HISTORICAL_ONLY` | 4 |
| `DEFERRED_DOMAIN` | 1 |
| `SUPERSEDED` | 1 |

### Counts by disposition

| Value | Count |
| --- | ---: |
| `IMPORT_AS_IS` | 115 |
| `IMPORT_WITH_ADAPTATION` | 8 |
| `REWRITE` | 3 |
| `ARCHIVE_SUPERSEDED` | 1 |
| `DEFER` | 1 |

### Counts by inspection level

| Value | Count |
| --- | ---: |
| `STRUCTURAL` | 99 |
| `FULL_CONTENT` | 29 |

## Historical package map

| Layer | Assets | Role | Historical source of truth | G0 interpretation |
| --- | --- | --- | --- | --- |
| Product foundations | progression and Anki XP foundations | levels/cross-domain framing | broader foundations, overridden by later Review docs | rewrite or defer |
| Review specifications | taxonomy, reward, abuse, day aggregation | Review event and reward semantics | detailed docs, then actual code/tests | candidate with adaptation |
| Simulation specification | Stage 5A document | scenarios, gates, evidence methodology | specification corrected by later implementation/reports | candidate with adaptation |
| Package contracts | schemas, configs, oracle/FSRS contracts | strict executable boundaries | matching current schema/config plus loaders | preserve, execute later |
| Deterministic core | models, parameters, reward, safeguards, day aggregation | pure Review computation | frozen code and tests | import exact, G0.6 |
| Scenario runner | strict JSON, schemas, loader, runner, reports/digests | deterministic corpus | v0.2 schema and runner/tests | import exact, G0.6 |
| Sweep/evidence | candidate catalog, sweep, evidence and properties | bounded parameter comparison | code/config/tests; claims not reproduced | import exact, G0.6/G0.7 |
| Population | 16 personas and generator | independent-day workload stress | persona schema/files and population code/tests | import exact, not longitudinal proof |
| Longitudinal | config, persistent cards, matched policies/analysis | 30/90/365 histories | longitudinal code/config/tests | import exact, G0.6/G0.7/G1 |
| Oracles | Rust CLI and FSRS reference corpus | implementation parity/reference checks | contracts, Rust/Python adapters and tests | import exact, execute later |
| Reports | closure and correction | chronology and claimed evidence | later correction outranks initial closure | historical evidence only until G0.7 |

## Bundle-level dependency map

| From | Depends on / feeds | Source-of-truth rule | Later gate |
| --- | --- | --- | --- |
| Foundations | Review specifications | later detailed Review decisions override early generic formulas | G0.4 / G4 |
| Review specifications | simulation specification | taxonomy → reward → abuse → day aggregation | G0.4 |
| Simulation specification | schemas/configs/contracts | implementation may refine the draft but must record drift | G0.4 |
| Schemas/configs/contracts | loaders, CLI and runners | strict schema plus domain validation; v0.2 supersedes scenario v0.1 | G0.5/G0.6 |
| Deterministic source | fixtures and scenarios | `aggregate_day()` and episode evaluator are formula sources | G0.6 |
| Scenarios | scenario runner/assertions/comparisons | all 26 paths use v0.2; abuse cases depend on declared controls | G0.6 |
| Personas | population generator | persona schema + 16 committed files | G0.6/G0.7 |
| Longitudinal config | longitudinal engine/matched analysis | persistent lineages and matched latent streams | G0.6/G0.7/G1 |
| Python tests | package modules/contracts | test existence is not PASS evidence | G0.6 |
| Rust oracle | Python differential adapter + golden/scenario corpus | shared data contract, independent formula source | G0.6/G0.7 |
| FSRS corpus | Python/Rust FSRS adapters | reference state contract, not reward correctness | G0.6/G0.7 |
| Closure/correction reports | commands, configs and generated outputs | report claims are historical until reproduced | G0.7 |

## Document and evidence chronology

```text
Progression Foundation (DRAFT v0.2)
→ Anki XP Foundation (DRAFT v0.2)
→ Review Taxonomy / Reward / Abuse / Day (DRAFT v0.1)
→ Simulation Specification (Stage 5A)
→ deterministic core and scenario runner
→ initial sweep/property closure
→ population/Rust/FSRS work
→ Stage 5B.C correction
→ final historical status: PARTIAL
```

`review-v0.1` is a regression reference, not an accepted production economy.
Learn XP and Create XP were not started. The open research problem is
cross-horizon retention-cycling growth.

## Contradictions and supersession map

| Class | Earlier claim | Later/final source | Result | G0.4 treatment |
| --- | --- | --- | --- | --- |
| Status | Stage 5 Review simulation `COMPLETE` | closure/correction say `PARTIAL` | `RESOLVED_BY_LATER_SOURCE` | archive earlier COMPLETE language |
| Candidate | initial sweep recommends `R-CURRENT` | correction says no recommended candidate until cycling closure | `RESOLVED_BY_LATER_SOURCE` | keep as regression reference only |
| Schema | scenario v0.1 | v0.2 adds invariant/regression applicability | `RESOLVED_BY_LATER_SOURCE` | archive v0.1; recover v0.2 |
| Evidence method | independent persona-days presented near calibration | correction explicitly limits them to workload stress | `RESOLVED_BY_LATER_SOURCE` | never call population longitudinal evidence |
| Metrics | placeholder ideal 0/1 values | typed measured/derived/unsupported/deferred evidence | `RESOLVED_BY_LATER_SOURCE` | recover corrected evidence model |
| Stage ordering | package/index retains stale “next Stage 5B.3” text | same source includes later 5B.C/5B.5/5B.6/5B.7 | `RESOLVED_BY_LATER_SOURCE` | rewrite package index |
| Counts | 26 scenarios, distribution 6/7/6/6/1 | 26 paths and corpus-count test match | `NONE` | preserve count, rerun later |
| Counts | 16 personas | 16 paths, schema range and population test match | `NONE` | preserve count, rerun later |
| Counts | 31 golden cases | oracle counting test asserts 31; fixture exists | `NONE` structurally | parse/execute in G0.6 |
| Isolation | package excluded from production/CI; outputs gitignored | branch delta is confined to scope; no workflows changed | `NONE` | preserve isolation |
| Evidence | PASS/digest/result tables | no G0.3 execution | `REQUIRES_EXECUTION` | label historical until G0.7 |
| Cycling | endpoint gates below 3% but 90→365 growth fails | correction leaves gap open | `OPEN` | G1 blocker after executable baseline |

## Referenced but missing assets

No required tracked repository asset referenced by the inspected historical
indexes, package CLI, schemas or contracts was confirmed missing from the frozen
tree.

The following are not missing tracked assets:

- `outputs/` and its report files: declared generated and gitignored;
- sanitized real-history replay: deferred capability, not a committed asset;
- local JSONL oracle inputs/reports: generated temporary artifacts;
- `.venv`, caches, coverage, Rust target and build outputs.

Executable import closure is intentionally deferred to G0.6. G0.3 does not claim
that every Python/Rust import can be resolved in a current environment.

## Declared generated/untracked assets

| Area | Declaration | Inventory treatment |
| --- | --- | --- |
| `outputs/run-*` | scenario JSON/Markdown reports | generated, excluded |
| `outputs/sweeps/*` | sweep manifest/candidates/metrics/summary/Pareto | generated, excluded |
| `outputs/sensitivity/*` | sensitivity reports | generated, excluded |
| `outputs/population/*` | persona metrics/fairness/abuse/charts | generated, excluded |
| `outputs/longitudinal/*` | policy metrics/fairness/abuse/cohort summaries | generated, excluded |
| `outputs/rust-oracle/*` | differential JSON | generated, excluded |
| `outputs/fsrs-reference/*` | FSRS reference JSON | generated, excluded |
| `.venv`, caches, coverage, build/dist | local environment artifacts | ignored, excluded |
| `rust-oracle/target/` | Rust build output | ignored, excluded |

## Disposition summary

| Disposition | Count | Meaning for G0.4 |
| --- | ---: | --- |
| `IMPORT_AS_IS` | 115 | recover exact frozen candidate bytes, still gated by environment/functional/evidence checks |
| `IMPORT_WITH_ADAPTATION` | 8 | preserve meaning/provenance while updating status, placement or current-repository framing |
| `REWRITE` | 3 | create a new canonical index/foundation rather than promoting historical wording |
| `ARCHIVE_SUPERSEDED` | 1 | preserve v0.1 schema solely for provenance |
| `DEFER` | 1 | do not transfer global progression foundation during Review baseline recovery |
| `DISCARD` | 0 | no tracked asset was discarded merely because it was unexecuted |

## G0.4 transfer batches

Only order and prerequisites are defined here; no transfer occurred.

| Batch | Inputs | Prerequisites | Expected target | Post-transfer verification | Blockers |
| --- | --- | --- | --- | --- | --- |
| A — canonical docs/current contracts | `REWRITE`, Review-doc `IMPORT_WITH_ADAPTATION` | approve current/historical wording and precedence | `docs/gamification/` plus historical evidence under `reports/gamification/` | link/path review; status/provenance audit | unresolved content contradiction |
| B — schemas/configs/reference contracts | current `IMPORT_AS_IS`, archived v0.1 | Batch A defines current versions | `research/gamification-sim/` and archive schema area | exact byte/path inventory; strict version cross-check | missing/contradictory version |
| C — deterministic source | Python core/runner/sweep/longitudinal source and package metadata | B; package metadata adapted without formula changes | isolated research package | environment install in G0.5, then focused functional checks | dependency/toolchain failure |
| D — scenarios/fixtures/personas | 26 scenarios, golden fixture, 16 personas | B/C | same isolated package paths | schema/domain validation; count/duplicate checks | corpus drift |
| E — tests and oracles | Python tests, Rust source/manifest/lock, FSRS corpus | C/D | same package paths | G0.6 tests/oracle; G0.7 evidence commands | current toolchain incompatibility |
| F — historical/superseded archive | closure, correction, scenario schema v0.1 | A and archive placement decision | `reports/gamification/` / research archive | no active source-of-truth links to superseded artifacts | archive policy ambiguity |

## Risks and unresolved questions

- Exact historical dependencies may not install unchanged in the current
  environment.
- Some package/source/test files were structurally classified rather than read
  line by line; this is intentional and recorded per manifest row.
- `review-v0.1` formulas and all expected numeric values remain unverified.
- Generated outputs and reported digests are absent by design and must be
  reproduced later.
- Cross-horizon retention cycling remains open and blocks a recommended Review
  candidate.
- The current package README contains stale chronology and cannot be promoted as
  a canonical current index.
- G0.4 must not silently change reward semantics while adapting paths/statuses.
- G0.5/G0.6 may reveal missing environment or import assumptions not detectable
  from path inventory.

## Verification

Performed:

- exact ref resolution and frozen-source availability;
- no-drift comparison from G0.2 tip to `gamification`;
- full merge-base→source compare with `too_large` unset;
- complete 128-path normalization;
- duplicate and root checks;
- family/count reconciliation;
- direct fetch of required entry points and disputed version/status sources;
- representative bundle inspection;
- manifest row count and unique-path validation;
- roadmap/report/manifest link planning.

Intentionally not performed:

```text
Fast CI
Docker E2E
real-Anki E2E
Python tests
Node/TypeScript tests
Rust tests/build
simulator/sweep/population/longitudinal commands
FSRS or Rust oracle execution
```

These checks would test executability/evidence, not G0.3 inventory provenance.

## Environment limitations

- No usable local repository checkout was available.
- Direct archive download and local `git ls-tree` were unavailable because the
  execution environment could not resolve GitHub network access.
- The GitHub connector does not expose recursive tree listing as a dedicated
  action.
- Completeness therefore uses the documented compare-based proof.
- `git diff --check` cannot be run locally; final GitHub per-file comparisons and
  direct file rereads are used instead.
- No claim is made about untracked files that may once have existed outside Git.

## Recorded guarantees

- Every discovered tracked scope path appears once in the manifest.
- No non-existent tracked path is intentionally listed.
- No historical asset was copied or restored.
- No formula, simulator source, dependency or fixture was modified.
- `master`, `core` and the historical source remain read-only.
- No production, frontend, test, script, workflow, package or release path is
  changed by G0.3.
- No Pull Request is created.
- `DISCOVERED` and `INSPECTED` are not presented as `EXERCISABLE` or
  `REPRODUCED`.
- G0.4 has not started.

## Next step

```text
G0.4 — Selective research recovery
```

G0.4 must transfer only approved manifest rows, in the recorded batch order, and
must preserve the distinction between current candidate, historical evidence and
superseded material.
