# Deterministic Review XP Research Simulator

Status: **research implementation through Stage 5B.2**  
Rule version: **`review-v0.1`**  
Scenario schema: **`review-scenario-v0.1`**

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

- Draft 2020-12 schema: `schemas/review-scenario-v0.1.schema.json`;
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
│   └── review-scenario-v0.1.schema.json
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

- parameter sweep and sensitivity analysis;
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

## Next possible stage

```text
Stage 5B.3 — parameter sweep and sensitivity design
```

It is not started by Stage 5B.2.
