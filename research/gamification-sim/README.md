# Deterministic Review XP Research Simulator

Status: **research implementation through Stage 5B.2**  
Rule version: **`review-v0.1`**  
Scenario schema: **`review-scenario-v0.2`** (`v0.1` retained as superseded history)

This package is an isolated executable model of the candidate Review XP design documented by Anki Study Report. Stage 5B.1 provides the pure deterministic episode/day calculation core. Stage 5B.2 adds a strict, reproducible multi-day scenario runner around that core without changing any reward formula.

The package is not part of the Anki add-on. It does not import `anki_study_report`, read an Anki collection, build the dashboard, change dashboard payloads, participate in `.ankiaddon` packaging, or run in Fast CI, Full CI, release workflows, or production verification scripts.

## Implemented scope

### Stage 5B.1 — deterministic core

- immutable normalized episode, support, supplemental, workload, and day models;
- strict non-coercing integer validation;
- versioned candidate parameter set `review-v0.1`;
- baseline, retrieval challenge, delay protection, memory gain, and confidence blending;
- separate `CoreEligibility` and `BonusEligibility` handling;
- deterministic safeguards, Undo, idempotency, and card/day uniqueness;
- support and supplemental routing and caps;
- day aggregation, volume credit, completion credit, and contribution bands;
- explainable breakdowns;
- 31 executable golden cases and hard-invariant regression tests.

### Stage 5B.2 — deterministic scenario runner

- Draft 2020-12 schema: `schemas/review-scenario-v0.2.schema.json`;
- strict UTF-8 JSON loading with duplicate-key, BOM, non-standard-number, empty-file, and size checks;
- schema validation through `Draft202012Validator.check_schema()` and deterministic `iter_errors()` output;
- immutable typed scenario, assertion, comparison, manifest, and result models;
- ordered multi-day scenarios with analytical sessions;
- session flattening into the existing `ReviewDayInput` contract;
- execution exclusively through the existing `aggregate_day()` core;
- allowlisted metrics and assertions without `eval`, expressions, JSONPath, or dynamic imports;
- matched control comparison with component deltas, ratios, compatibility warnings, and documented differences;
- canonical JSON and SHA-256 input/output digests;
- deterministic JSON and Markdown reports;
- 26 committed scenarios: 6 ordinary, 7 edge, 6 control, 6 abuse, and 1 regression;
- script-friendly CLI with stable exit codes.

## Architecture

```text
Scenario JSON
→ strict JSON loader
→ local Draft 2020-12 schema
→ Python domain validation
→ immutable ScenarioDefinition
→ sessions flattened into ReviewDayInput
→ existing aggregate_day()
→ day/scenario metrics
→ allowlisted assertions
→ matched-control comparison
→ canonical digests
→ JSON and Markdown reports
```

The runner does not reimplement episode reward, challenge, memory gain, safeguards, caps, volume, completion, or contribution-band formulas. `aggregate_day()` remains their source of truth and calls the existing episode evaluator internally.

## Structure

```text
research/gamification-sim/
├── pyproject.toml
├── README.md
├── fixtures/
│   └── golden_cases.json
├── schemas/
│   ├── review-scenario-v0.1.schema.json  # superseded strict contract
│   └── review-scenario-v0.2.schema.json  # explicit assertion taxonomy
├── scenarios/
│   ├── ordinary/
│   ├── edge/
│   ├── controls/
│   ├── abuse/
│   └── regression/
├── outputs/                    # generated locally; gitignored
├── src/gamification_sim/
│   ├── models.py
│   ├── parameters.py
│   ├── episode_reward.py
│   ├── safeguards.py
│   ├── day_aggregation.py
│   ├── strict_json.py
│   ├── canonical_json.py
│   ├── scenario_models.py
│   ├── scenario_schema.py
│   ├── scenario_loader.py
│   ├── assertions.py
│   ├── comparisons.py
│   ├── scenario_runner.py
│   ├── reporting.py
│   ├── manifest.py
│   └── cli.py
└── tests/
```

## Installation

PowerShell:

```powershell
cd research/gamification-sim
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

The only runtime dependency added by Stage 5B.2 is:

```text
jsonschema>=4.26,<5
```

It is declared only in this isolated research package.

## Stage 5B.1 commands

```powershell
python -m pytest
python -m gamification_sim verify-examples
python -m gamification_sim verify-examples --json
python -m gamification_sim evaluate fixtures/golden_cases.json
python -m gamification_sim evaluate fixtures/golden_cases.json --json
```

## Stage 5B.2 commands

```powershell
python -m gamification_sim validate-scenarios scenarios
python -m gamification_sim validate-scenarios scenarios --json

python -m gamification_sim run-scenario scenarios\edge\session-invariance.json
python -m gamification_sim run-scenario scenarios\edge\session-invariance.json --json --no-write

python -m gamification_sim run-scenarios scenarios
python -m gamification_sim run-scenarios scenarios --json --no-write

python -m gamification_sim verify-report outputs\run-<digest>\results.json

python -m gamification_sim compare-scenarios `
  scenarios\controls\timely-backlog-control.json `
  scenarios\abuse\intentional-backlog.json `
  --no-write
```

Supported run flags:

```text
--json
--output-dir <local-path>
--no-write
```

Exit codes:

```text
0 — valid and all assertions passed
1 — one or more assertions failed
2 — invalid JSON, schema, or domain contract
3 — internal runner error
```

Errors are written to `stderr`. Commands do not prompt interactively.

## Scenario contract

```text
scenario
├── version, stable ID, category, title, description, tags
├── rule version
├── ordered days
│   ├── workload snapshot
│   ├── sessions
│   │   ├── explicit episodes
│   │   └── bounded declarative repeat groups
│   ├── support events
│   ├── supplemental events
│   └── Undo source keys
├── assertions
└── optional matched control and comparison explanation
```

`control_scenario_id` exists only at the scenario root. Assertion objects cannot
select or override a control: every comparison assertion in a scenario uses the
same resolved top-level control, which is executed first.

All closed schema objects reject unknown fields. Scenario IDs and session IDs use stable lowercase kebab-case identifiers. Days must be unique and strictly increasing. Session IDs are unique within a day, and episode `anki_day` must match its containing day.

The loader does not execute embedded code, follow URLs, load external schemas, resolve arbitrary file paths, or repair invalid inputs.

## Strict JSON policy

Scenario files:

- are UTF-8 without BOM;
- have a bounded file size;
- reject duplicate object keys;
- reject `NaN`, `Infinity`, and `-Infinity` through `parse_constant`;
- reject invalid UTF-8 and empty documents;
- are validated against a local schema without network access.

Serialization uses:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
)
```

## Assertions

Every v0.2 assertion declares `class` and a human-readable `rationale`.
Candidate-independent `invariant` assertions execute for every parameter set.
Exact numeric `regression` assertions declare
`applies_to_parameter_set_ids`; a non-matching run records
`NOT_APPLICABLE`, which is neither pass evidence nor a failure. Reports count
`PASSED`, `FAILED`, and `NOT_APPLICABLE` separately.

No expression language is provided. Supported assertion types are:

```text
equals
approximately_equals
less_than
less_than_or_equal
greater_than
greater_than_or_equal
equals_control
delta_from_control_lte
delta_from_control_gte
ratio_to_control_lte
ratio_to_control_gte
```

Scopes:

```text
day
scenario
comparison
```

Metrics:

```text
core_baseline
core_context
support
supplemental
volume_credit
completion_credit
total_review_units
qualified_volume
unique_core_episodes
successful_core_episodes
failed_core_episodes
bonus_share
```

`bonus_share` is the share of the final total contributed by all non-baseline channels. It is defined as `0` when total reward is `0`. A ratio against a zero control is explicitly reported as undefined and fails the assertion rather than being hidden.

## Matched controls

Each committed abuse scenario references a category-`control` scenario. Comparisons report:

- absolute total delta;
- total ratio when defined;
- core baseline delta;
- context delta;
- support delta;
- supplemental delta;
- volume delta;
- completion delta;
- compatibility warnings.

The loader rejects missing controls, self-reference, wrong control category, and cyclic references. The runner checks rule version, horizon, unique card count, core opportunities, and initial memory states. A scenario may document an intentional structural difference; the report still preserves the warning.

## Reports and outputs

By default, run commands write:

```text
outputs/run-<input-digest-prefix>/results.json
outputs/run-<input-digest-prefix>/summary.md
```

`outputs/` is gitignored. Ordinary tests use temporary directories and leave no reports in the repository. `--no-write` performs all validation and calculations without creating output files.

Reports contain the manifest, scenario/day results, assertions, comparisons, warnings, failures, component breakdowns, executed IDs, and canonical digests.

## Reproducibility

The manifest contains:

```text
simulator_version
rule_version
scenario_schema_version
Python major.minor
scenario_ids
input_digest
output_digest
command
```

Digests are SHA-256 over UTF-8 canonical JSON. They exclude timestamps, absolute paths, usernames, hostnames, virtual-environment paths, tokens, and OS-specific path separators.

The output digest uses one explicit detached contract:

```text
output_digest = SHA-256(
  canonical CorpusRunResult where manifest.output_digest == ""
)

output_digest_contract = detached-corpus-result-v1
```

`verify-report` strict-loads an existing JSON report, rejects duplicate keys and
non-standard numbers, and verifies this digest without discovering or executing
any scenarios. Whitespace and object-key formatting do not affect verification.

Equivalent runs produce the same digests regardless of scenario file discovery order, absolute checkout path, current time, or platform path separator.

## Formula summary

For a core episode:

```text
BaselineCredit = AttemptCredit + Pass × OutcomeCredit
ContextBonus   = Pass × ContextCredit
CoreReviewUnits =
    CoreEligibility × BaselineCredit
  + BonusEligibility × ContextBonus
```

For a day:

```text
ReviewDayUnits =
    CoreBaseline
  + CoreContext
  + CappedSupportUnits
  + CappedSupplementalUnits
  + VolumeCredit
  + CompletionCredit
```

No component is accumulated through hidden mutable global state.

## Input and numeric contracts

- Integer-semantic inputs accept only a real Python `int`; `bool`, floats, numeric strings, `NaN`, infinity, and out-of-range values are rejected rather than coerced.
- Support fixtures provide only `source_event_key`, `parent_episode_key`, and `kind`; reward values come from `RewardParameterSet`.
- `INTERDAY_RECOVERY` is valued at `0.12 Review Unit` in `review-v0.1`, subject to unchanged caps.
- `OTHER` contributes `0`.
- Probabilities and eligibility coefficients are range-validated.
- Stability inputs must be positive.
- Formula arithmetic uses Python `float` in deterministic operation order.
- Comparisons use tolerance `1e-9` unless explicitly overridden.
- Rounding is presentation-only.

## Research limitations

`review-v0.1` remains a candidate parameter set. Passing golden fixtures and deterministic scenarios proves implementation conformance and exposes controlled behavior; it does not prove population-level calibration, long-term fairness, or production readiness.

Deliberately excluded:

- Monte Carlo and random seeds;
- synthetic populations;
- FSRS or `py-fsrs` adapters;
- real-history replay;
- Rust/C++ oracle implementations;
- production persistence and reward ledger;
- Anki collection or `revlog` access;
- dashboard or web UI;
- production integration;
- CI integration.

## Isolation contract

The simulator remains outside:

- `anki_study_report/`;
- `web-dashboard/`;
- root dependency manifests and lockfiles;
- bundled Python runtime;
- `build_ankiaddon.ps1` and package scripts;
- `.github/workflows/`;
- production verification scripts;
- `.ankiaddon` contents.

Run it manually from this directory. A future research-only CI job requires a separate explicit decision and must not silently extend Fast CI.

## Stage 5B.3 parameter sweep

```text
review-v0.1 remains immutable
→ strict local sweep config
→ sequential family overlays
→ hard gates
→ nondominated Pareto front
→ one-at-a-time sensitivity and reward-cliff probes
```

The first pass is bounded to 48 candidate evaluations and does not construct a
full Cartesian product. Every catalog entry has a full normalized parameter
snapshot and SHA-256 digest; family overlays apply only declared changed fields.
The runner receives parameters explicitly, while all pre-existing commands keep
using `review-v0.1` by default.

```powershell
python -m gamification_sim list-parameter-sets
python -m gamification_sim validate-sweep configs/review-sweep-v0.1.json
python -m gamification_sim run-sweep configs/review-sweep-v0.1.json --no-write
python -m gamification_sim run-sensitivity configs/review-sweep-v0.1.json --parameter-set R-CURRENT --no-write
```

`run-sweep` rejects candidates before ranking when an H01–H18 invariant,
applicable regression, measured quantitative gate, breakdown identity, cap, or
deterministic digest contract fails. Current-only regressions are recorded as
`NOT_APPLICABLE` for alternatives. Rejections carry stable reason codes.
Candidates with required missing evidence are `INCOMPLETE_EVIDENCE`, not
`REJECT`, and cannot enter the final Pareto front.

Every sweep metric is a typed `MetricResult` with status `MEASURED`, `DERIVED`,
`UNSUPPORTED`, or `DEFERRED`, plus unit, sample count, source IDs, method,
warnings, and (for missing evidence) a required reason with `value: null`.
Collection metadata independence is derived from the input contract and a
matched workload; confidence and FSRS-availability deltas use matched episodes.
Observed volume/completion maxima drive Q06/Q07. The C3/C4 engine now measures
retention, backlog, and long-session metrics from matched 90-day histories for
every evaluated parameter set. A caller that omits longitudinal evidence still
receives explicit `UNSUPPORTED`/`DEFERRED` values, never ideal zero/one constants.

Without `--no-write`, sweep reports are written under the gitignored
`outputs/sweeps/<digest-prefix>/` directory as `manifest.json`,
`candidates.json`, `metrics.csv`, `summary.md`, and `pareto.json`.

Sensitivity grids use explicit endpoints rather than floating `arange`. Every
point reports invariant and quantitative-gate status, five longitudinal metric
deltas, reward-cliff status, and evidence completeness. Cliff probes evaluate
`threshold - epsilon`, `threshold`, and `threshold + epsilon` for challenge,
cap, tier, and contribution-band boundaries.

## Stage 5B.4 property-based invariants

Hypothesis is confined to the `test` extra. The committed property profile uses
`database=None`, `derandomize=True`, a fixed example budget, no deadlines, no
machine clock, and no global random state. It exercises H01–H18 across distinct
catalog candidates, corrected Pareto candidates, every sensitivity endpoint,
and a valid sensitivity boundary that is expected to fail Q01.

Generated cases cover baseline monotonicity, session partitions, replay, Undo,
card/day uniqueness, button neutrality, administrative and preview zero,
component caps, non-negative explainable totals, deterministic serialization,
canonical digests, and invalid numeric/enum/order/JSON inputs. Invalid parameter
sets are rejected at `RewardParameterSet` construction; they are never silently
normalized.

## Stage 5B.5 independent-day workload stress simulation

The strict `review-persona-v0.1` catalog contains 16 parameterized synthetic
classes. It contains model inputs only—no card text, deck names, collection
content, identifiers, or real review history. Each replica receives a child seed
derived from SHA-256 over the master seed, persona ID, and replica number, then
uses its own `random.Random` instance.

```powershell
python -m gamification_sim validate-personas personas
python -m gamification_sim run-population --mode development --parameter-set R-CURRENT --seed 20260716 --no-write
python -m gamification_sim run-population --mode standard --parameter-set R-CURRENT --seed 20260716
python -m gamification_sim run-population --mode long --parameter-set R-CURRENT --seed 20260716 --smoke --no-write
```

Development executes 480 independent persona-days. Standard executes 584,000
independent persona-days. Each generated day is a fresh workload sample; these
runs are cap/distribution stress evidence, not longitudinal card histories.
The full long mode is approximately 1.098 million persona-days and is never part
of the ordinary suite; `--smoke` validates its path with 112 persona-days.
Reports include distribution tails, component shares, baseline preservation,
fairness comparisons, and matched deterministic abuse/control results. Concepts
outside the current input contract are explicitly deferred rather than assigned
placeholder numbers.

## Stage 5B.6 standalone Rust oracle

`rust-oracle/` is an independent Rust CLI for the deterministic episode/day
subset. The boundary is UTF-8 JSONL through files/stdout; there is no FFI, PyO3,
Maturin, shared library, add-on import, build integration, or workflow.

```powershell
python -m gamification_sim verify-rust-oracle --parameter-set R-CURRENT --corpus scenarios --no-write
cargo fmt --manifest-path rust-oracle/Cargo.toml -- --check
cargo test --manifest-path rust-oracle/Cargo.toml
cargo clippy --manifest-path rust-oracle/Cargo.toml -- -D warnings
```

On Windows without MSVC Build Tools, the verified local toolchain is the official
`stable-x86_64-pc-windows-gnu` target (prefix Cargo with
`+stable-x86_64-pc-windows-gnu`). The differential report classifies exact,
within-tolerance, semantic-mismatch, and unsupported cases. Invalid inputs must
be rejected by both implementations and by the Rust process exit code.

## Stage 5B.7 FSRS reference comparison

The optional `fsrs` extra pins official `py-fsrs` 6.3.1. The Rust oracle pins
official `open-spaced-repetition/fsrs-rs` crate 6.6.1. Neither dependency is
required by the deterministic reward core or production add-on.

```powershell
python -m pip install -e ".[test,fsrs]"
python -m gamification_sim verify-fsrs-reference contracts/fsrs-trajectories-v0.1.json --no-write
```

The committed UTC corpus contains 10 synthetic trajectories: new, Good, Hard,
Easy, Again/relearning, long-overdue, high/low desired retention, low-history,
and no-FSRS fallback. The report compares retrievability, stability, difficulty,
counterfactual Good stability, model intervals, and normalized serialized
trajectory signatures.

State tolerances are explicit (`1e-4` for f64/f32 reference state fields).
Scheduled intervals are reported separately: `py-fsrs` applies configured
learning/relearning steps, while `fsrs-rs::next_states` reports the model
interval. This documented scheduler-layer difference is not classified as a
reward defect. High-, low-, no-FSRS, and backlog contexts all retain identical
CoreBaseline.

## Stage 5B.C3 persistent longitudinal card simulation

The separate `review-longitudinal-v0.1` engine keeps stable card lineages and
evolving scheduler state across 30/90/365-day horizons. The py-fsrs path uses
official `fsrs 6.3.1` transitions with fuzzing disabled; the no-FSRS path is
explicitly `neutral-synthetic-v0.1` and does not claim legacy Anki scheduler
parity.

```powershell
python -m gamification_sim validate-longitudinal-config configs/review-longitudinal-v0.1.json
python -m gamification_sim run-longitudinal configs/review-longitudinal-v0.1.json --mode development --seed 20260716 --no-write
```

Each day gathers cards from state-derived due dates, applies a bounded policy
limit, leaves missed cards overdue, reviews the same lineage during catch-up,
updates scheduler state, and then sends normalized inputs to the unchanged
reward core. Matched policies share an initial cohort and latent draws keyed by
master seed, replica, lineage, review ordinal, and channel. Policy names and
iteration order therefore do not select a different random world. Higher
desired retention produces shorter intervals and more scheduled reviews on the
committed matched cohort. Scheduler uncertainty and no-FSRS operation never
suppress the eligible core baseline.

## Stage 5B.C4 matched fairness and abuse controls

Policy-pair definitions declare exactly one changed factor and reject extra
differences. Retention pairs vary only the desired-retention timeline; backlog
pairs vary only the delay window. Every longitudinal comparison verifies equal
initial cohort and latent-stream digests, reports review-count difference,
baseline/context/total deltas, RU per eligible review, and baseline
preservation.

Abuse advantage is not raw cumulative reward. It subtracts the additional
legitimate CoreBaseline caused by a different number of scheduled reviews, then
normalizes the unexplained remainder by the control total. The 90-day
high/low-cycle and intentional-backlog gates require at most 3% unexplained
advantage. Duplicate replay, session splitting, relearning, preview, forced-due,
and micro-scope completion remain explicit one-factor deterministic controls.
Missing policy evidence is serialized as `UNSUPPORTED` with a reason; it is
never emitted as an ideal zero.

## Stage 5B.C5 corrected sweep and sensitivity

The corrected sequential sweep evaluates all 17 catalog entries and bounded
family composites. Exact `R-CURRENT` regressions are `NOT_APPLICABLE` to other
parameter sets; only invariant failures, applicable regressions, measured
quantitative failures, invalid contracts, or nondeterminism can reject a
candidate. `PASS` is required for Pareto participation, and normalized
parameter digests collapse semantically identical overlays before ranking.

The fixed config and seed evaluate 30 distinct candidate IDs. All 30 have
complete longitudinal evidence and pass the candidate gates; the nondominated
front contains 14 unique normalized parameter states. Sensitivity covers 63
explicit points: every point has complete longitudinal evidence and passes all
H01–H18 invariants, while ten points cross a declared quantitative gate. These
crossings are reported as evidence rather than silently removed from the grid.

## Stage 5B.C6 corrected population calibration

The gitignored fixed-seed evidence set contains a 30-day development run over
all four configured candidates and nine policies, a 90-day run over all 14
normalized Pareto candidates and nine policies, and the required seven-policy
365-day `R-CURRENT` run. Repeated 90/365 executions reproduce trajectory, final
cohort, and report digests; a different seed changes the history while retaining
the same contract. Honest baseline preservation remains 1.0 within floating
tolerance in every result.

The cross-horizon abuse check intentionally remains stricter than the individual
3% endpoint gate: each retention-cycle group fails when advantage increases in
every matched replica from day 90 to day 365. `R-CURRENT` stays below 3% at day
365, but both high- and low-retention cycle groups show systematic growth, so
this evidence does not support a complete Stage 5 closure. The intentional
backlog group passes and all generated reports remain under gitignored
`outputs/longitudinal/` directories.
