# Deterministic Review XP Simulator Core

Status: **research implementation for Stage 5B.1**  
Rule version: **`review-v0.1`**

This package is an isolated, executable model of the candidate Review XP formulas documented by Anki Study Report. It exists to verify exact arithmetic, deterministic safeguards, day aggregation, explainable breakdowns, and hard invariants before any production design is accepted.

The package is not part of the Anki add-on. It does not import `anki_study_report`, read an Anki collection, build the dashboard, change the dashboard payload, participate in `.ankiaddon` packaging, or run in the project's Fast CI / Full CI workflows.

## Implemented scope

The core implements:

- immutable normalized episode, support, supplemental, workload, and day models;
- the versioned candidate parameter set `review-v0.1`;
- `AttemptCredit + Pass × OutcomeCredit` baseline calculation;
- retrieval challenge interpolation and natural-due delay protection;
- counterfactual-`Good` logarithmic memory gain;
- model-confidence blending with a neutral no-FSRS fallback;
- separate `CoreEligibility` and `BonusEligibility` handling;
- deterministic source-event idempotency and card/day uniqueness;
- Undo, administrative, preview, forced-due, support, and supplemental routing;
- support episode/day caps, supplemental day cap, volume tiers, and completion credit;
- contribution bands and structured reason codes;
- executable golden examples and tests for hard invariants H01–H18;
- a small fixture verification CLI.

## Deliberately outside Stage 5B.1

This package does not implement:

- production integration or persistence;
- Anki scheduler, collection, or `revlog` adapters;
- real FSRS scheduling or `py-fsrs`;
- Learn XP, Create XP, global XP conversion, levels, streak, or Momentum;
- synthetic personas, Monte Carlo, parameter sweeps, or sensitivity analysis;
- real-history replay;
- statistical macro or cheating detection;
- notebooks, charts, web server, GUI, Rust, C++, PyO3, or FFI.

Those belong to later research stages. The next intended step is **5B.2 — deterministic scenario runner**.

## Structure

```text
research/gamification-sim/
├── pyproject.toml
├── README.md
├── fixtures/golden_cases.json
├── src/gamification_sim/
│   ├── models.py
│   ├── parameters.py
│   ├── episode_reward.py
│   ├── safeguards.py
│   ├── day_aggregation.py
│   ├── breakdown.py
│   ├── validation.py
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

The runtime package uses only the Python Standard Library. `pytest` is an optional test dependency local to this package.

## Commands

```powershell
python -m pytest
python -m gamification_sim verify-examples
python -m gamification_sim verify-examples --json
python -m gamification_sim evaluate fixtures/golden_cases.json
python -m gamification_sim evaluate fixtures/golden_cases.json --json
```

A golden mismatch returns a non-zero exit code.

## Formula summary

For a core episode:

```text
BaselineCredit = AttemptCredit + Pass × OutcomeCredit
ContextBonus   = Pass × ContextCredit
CoreReviewUnits =
    CoreEligibility × BaselineCredit
  + BonusEligibility × ContextBonus
```

The day is derived from source events on every calculation:

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

## Numeric policy

- Inputs must be finite; `NaN` and infinities are rejected.
- Probabilities and eligibility coefficients are range-validated.
- Stability inputs must be strictly positive.
- Formula arithmetic uses Python `float` in a deterministic operation order.
- Tests and golden comparisons use absolute/relative tolerance `1e-9`.
- Rounding is presentation-only and never occurs inside reward formulas.
- Every result returns its components, caps, eligibility values, reason codes, and rule version.

## Research limitations

`review-v0.1` is a candidate parameter set, not production economy. Golden examples prove implementation conformance to the current documents; they do not prove that the economy is optimally calibrated or fair across real populations. That requires the scenario, parameter, population, and replay stages planned for 5B.2–5B.4.

## Isolation contract

The simulator must remain outside:

- `anki_study_report/`;
- `web-dashboard/`;
- root dependency manifests and lockfiles;
- `build_ankiaddon.ps1` and package scripts;
- `.github/workflows/`;
- production verification scripts;
- `.ankiaddon` contents.

Run it manually from this directory. A future research-only CI check requires a separate explicit decision; it must not silently extend Fast CI.
