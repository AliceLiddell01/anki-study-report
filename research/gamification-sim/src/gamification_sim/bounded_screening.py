from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import subprocess
import sys
from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest
from .day_aggregation import aggregate_day
from .episode_reward import evaluate_episode
from .longitudinal_config import load_longitudinal_config
from .longitudinal_runner import run_policy
from .matched_analysis import POLICY_PAIRS
from .models import (
    CompletionStatus,
    ConfidenceLevel,
    MemoryContext,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    WorkloadSnapshot,
)
from .parameters import CURRENT_PARAMETERS
from .review_candidate_mechanisms import (
    FROZEN_REVIEW_CANDIDATES,
    REFERENCE_PARAMETERIZATION_ID,
    RewardExecutionContext,
    validate_frozen_review_candidate_protocol,
)
from .strict_json import load_strict_json
from .workspace import ResearchWorkspace, resolve_research_workspace


PROTOCOL_RELATIVE_PATH = Path("contracts/review-xp-candidate-protocol-v1.json")
SCHEMA_RELATIVE_PATH = Path("schemas/review-xp-candidate-protocol-v1.schema.json")
CONFIG_RELATIVE_PATH = Path("configs/review-longitudinal-v0.1.json")
EXPECTED_SCREENING_UNIT_COUNT = 160
ABS_TOLERANCE = 1e-9
EXPECTED_HARD_GATE_IDS = {
    "GATE-ENDPOINT-CAP",
    "GATE-NO-CYCLING-GROWTH",
    "GATE-BASELINE-PRESERVED",
    "GATE-ZERO-SUPPRESSION",
    "GATE-HONEST-BACKLOG-FAIRNESS",
    "GATE-NO-BACKLOG-GAIN",
    "GATE-ORDINARY-UNIT",
    "GATE-AGAIN-CREDIT",
    "GATE-BUTTON-NEUTRAL",
    "GATE-SESSION-INVARIANT",
    "GATE-NO-RESPONSE-TIME-REWARD",
    "GATE-RESPONSE-VALIDITY",
    "GATE-DETERMINISTIC-REPLAY",
    "GATE-SECONDARY-SEED",
    "GATE-EVIDENCE-COMPLETE",
    "GATE-RESEARCH-ONLY",
}

CASE_TO_POLICY_PAIR_ID: Mapping[str, str] = {
    "CASE-RETENTION-HIGH": "retention-high-cycle",
    "CASE-RETENTION-LOW": "retention-low-cycle",
    "CASE-INTENTIONAL-BACKLOG": "intentional-backlog",
    "CASE-HONEST-BACKLOG-RETURN": "honest-backlog-return",
}
MODE_BY_HORIZON: Mapping[int, str] = {
    90: "calibration-90",
    365: "calibration-365",
}


@dataclass(frozen=True, slots=True, order=True)
class ScreeningExecutionUnit:
    candidate_or_reference: str
    policy_pair: str
    control_condition: str
    horizon: int
    replica: int
    seed: int
    population_variant: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_or_reference": self.candidate_or_reference,
            "parameterization": (
                None
                if self.candidate_or_reference == REFERENCE_PARAMETERIZATION_ID
                else self.candidate_or_reference
            ),
            "policy_pair": self.policy_pair,
            "control_condition": self.control_condition,
            "horizon": self.horizon,
            "replica": self.replica,
            "seed": self.seed,
            "population_variant": self.population_variant,
        }

    @property
    def unit_id(self) -> str:
        return canonical_digest(self.payload())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_errors(schema: Mapping[str, Any], payload: Mapping[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: (
            tuple(str(part) for part in item.absolute_path),
            item.message,
        ),
    )
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in errors
    ]


def load_and_validate_screening_protocol(
    workspace: ResearchWorkspace | Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = resolve_research_workspace(workspace)
    protocol_path = resolved.path(PROTOCOL_RELATIVE_PATH)
    schema_path = resolved.path(SCHEMA_RELATIVE_PATH)
    protocol = load_strict_json(protocol_path)
    schema = load_strict_json(schema_path)
    if not isinstance(protocol, dict) or not isinstance(schema, dict):
        raise ValueError("screening protocol and schema must be JSON objects")
    Draft202012Validator.check_schema(schema)
    errors = _schema_errors(schema, protocol)
    if errors:
        raise ValueError("screening protocol schema validation failed: " + "; ".join(errors))
    validate_frozen_review_candidate_protocol(protocol)
    hard_gates = protocol.get("hard_gates")
    if not isinstance(hard_gates, list):
        raise ValueError("hard_gates must be an array")
    hard_gate_ids = {
        item.get("predicate_id")
        for item in hard_gates
        if isinstance(item, dict)
    }
    if hard_gate_ids != EXPECTED_HARD_GATE_IDS:
        raise ValueError("frozen hard-gate registry drifted")
    return protocol, {
        "protocol_path": PROTOCOL_RELATIVE_PATH.as_posix(),
        "protocol_sha256": _sha256(protocol_path),
        "protocol_digest": canonical_digest(protocol),
        "schema_path": SCHEMA_RELATIVE_PATH.as_posix(),
        "schema_sha256": _sha256(schema_path),
        "schema_digest": canonical_digest(schema),
        "schema_draft": schema.get("$schema"),
    }


def _axis(dimensions: Mapping[str, Any], name: str) -> tuple[Any, ...]:
    value = dimensions.get(name)
    if not isinstance(value, list) or not value:
        raise ValueError(f"screening_dimensions.{name} must be a non-empty array")
    return tuple(value)


def build_screening_manifest(
    workspace: ResearchWorkspace | Path | str | None = None,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    protocol, identities = load_and_validate_screening_protocol(resolved)
    dimensions = protocol.get("screening_dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("screening_dimensions must be an object")

    variants = _axis(dimensions, "candidate_or_reference")
    policy_pairs = _axis(dimensions, "policy_pairs")
    controls = _axis(dimensions, "control_conditions")
    horizons = _axis(dimensions, "horizons")
    replicas = _axis(dimensions, "replicas")
    seeds = _axis(dimensions, "seeds")
    populations = _axis(dimensions, "population_variants")
    invariant_checks = _axis(dimensions, "required_invariant_checks")

    expected_variants = (
        REFERENCE_PARAMETERIZATION_ID,
        *(item.parameterization_id for item in FROZEN_REVIEW_CANDIDATES),
    )
    if variants != expected_variants:
        raise ValueError("candidate/reference screening order drifted")
    if policy_pairs != tuple(CASE_TO_POLICY_PAIR_ID):
        raise ValueError("policy-pair screening order drifted")
    if controls != ("MATCHED_CONTROL_FROM_CASE",):
        raise ValueError("control-condition screening axis drifted")
    if horizons != (90, 365):
        raise ValueError("screening horizons drifted")
    if replicas != (0, 1):
        raise ValueError("screening replicas drifted")
    if seeds != (20260716, 20260717):
        raise ValueError("screening seeds drifted")
    if populations != ("CANONICAL_SYNTHETIC_COHORT",):
        raise ValueError("screening population axis drifted")

    units = tuple(
        ScreeningExecutionUnit(*values)
        for values in product(
            variants,
            policy_pairs,
            controls,
            horizons,
            replicas,
            seeds,
            populations,
        )
    )
    unit_payloads = [
        {"unit_id": unit.unit_id, **unit.payload()}
        for unit in units
    ]
    unique_ids = {item["unit_id"] for item in unit_payloads}
    dimension_product = math.prod(
        len(axis)
        for axis in (
            variants,
            policy_pairs,
            controls,
            horizons,
            replicas,
            seeds,
            populations,
        )
    )
    if dimension_product != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError(
            f"screening dimension product must be {EXPECTED_SCREENING_UNIT_COUNT}, "
            f"got {dimension_product}"
        )
    if len(unit_payloads) != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening unit count drifted")
    if len(unique_ids) != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening units are not unique")

    config = load_longitudinal_config(
        resolved.path(CONFIG_RELATIVE_PATH),
        workspace=resolved,
    )
    manifest = {
        "manifest_version": "review-xp-bounded-screening-manifest-v1",
        **identities,
        "config_path": CONFIG_RELATIVE_PATH.as_posix(),
        "config_digest": config.digest,
        "axes": {
            "candidate_or_reference": list(variants),
            "policy_pairs": list(policy_pairs),
            "control_conditions": list(controls),
            "horizons": list(horizons),
            "replicas": list(replicas),
            "seeds": list(seeds),
            "population_variants": list(populations),
        },
        "required_invariant_checks": list(invariant_checks),
        "dimension_product": dimension_product,
        "expected_units": EXPECTED_SCREENING_UNIT_COUNT,
        "actual_units": len(unit_payloads),
        "actual_unique_units": len(unique_ids),
        "missing_units": 0,
        "extra_units": 0,
        "duplicate_units": 0,
        "units": unit_payloads,
    }
    manifest["manifest_digest"] = canonical_digest(manifest)
    return manifest


def validate_screening_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("expected_units") != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening manifest expected count drifted")
    if manifest.get("actual_units") != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening manifest actual count drifted")
    if manifest.get("actual_unique_units") != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening manifest unique count drifted")
    if any(manifest.get(name) != 0 for name in ("missing_units", "extra_units", "duplicate_units")):
        raise ValueError("screening manifest accounting is incomplete")
    units = manifest.get("units")
    if not isinstance(units, list) or len(units) != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening manifest unit list is invalid")
    ids = [item.get("unit_id") for item in units if isinstance(item, dict)]
    if len(ids) != EXPECTED_SCREENING_UNIT_COUNT or len(set(ids)) != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening manifest unit IDs are invalid")


def _policy_pair(case_id: str):
    try:
        pair_id = CASE_TO_POLICY_PAIR_ID[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown screening policy pair: {case_id}") from exc
    for pair in POLICY_PAIRS:
        if pair.pair_id == pair_id:
            return pair
    raise ValueError(f"missing matched policy pair definition: {pair_id}")


def _compact_policy_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": result["policy_id"],
        "scheduler": result["scheduler"],
        "parameter_set_id": result["parameter_set_id"],
        "replica": result["replica"],
        "horizon_days": result["horizon_days"],
        "initial_cohort_digest": result["initial_cohort_digest"],
        "latent_stream_id": result["latent_stream_id"],
        "trajectory_digest": result["trajectory_digest"],
        "final_cohort_digest": result["final_cohort_digest"],
        "metrics": result["metrics"],
        "final_state_summary": result["final_state_summary"],
        **(
            {"candidate_parameterization": result["candidate_parameterization"]}
            if "candidate_parameterization" in result
            else {}
        ),
    }


def _comparison(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    if left["initial_cohort_digest"] != right["initial_cohort_digest"]:
        raise ValueError("screening unit initial cohort mismatch")
    if left["latent_stream_id"] != right["latent_stream_id"]:
        raise ValueError("screening unit latent stream mismatch")
    lm = left["metrics"]
    rm = right["metrics"]
    baseline_delta = lm["core_baseline"] - rm["core_baseline"]
    context_delta = lm["core_context"] - rm["core_context"]
    total_delta = lm["total_review_units"] - rm["total_review_units"]
    denominator = rm["total_review_units"]
    unexplained = total_delta - baseline_delta
    return {
        "baseline_delta": baseline_delta,
        "context_delta": context_delta,
        "total_delta": total_delta,
        "unexplained_advantage": (
            0.0 if denominator == 0.0 else unexplained / denominator
        ),
        "suppression_events": (
            lm["honest_baseline_suppression_events"]
            + rm["honest_baseline_suppression_events"]
        ),
        "left_baseline_preservation": lm["baseline_preservation_ratio"],
        "right_baseline_preservation": rm["baseline_preservation_ratio"],
    }


def run_screening_execution_unit(
    unit: ScreeningExecutionUnit,
    *,
    workspace: ResearchWorkspace | Path | str | None = None,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    config = load_longitudinal_config(
        resolved.path(CONFIG_RELATIVE_PATH),
        workspace=resolved,
    )
    try:
        mode_id = MODE_BY_HORIZON[unit.horizon]
    except KeyError as exc:
        raise ValueError(f"unsupported screening horizon: {unit.horizon}") from exc
    pair = _policy_pair(unit.policy_pair)
    config.mode(mode_id)
    left_policy = next(
        item for item in config.policies if item.policy_id == pair.left_policy_id
    )
    right_policy = next(
        item for item in config.policies if item.policy_id == pair.right_policy_id
    )
    candidate_id = (
        None
        if unit.candidate_or_reference == REFERENCE_PARAMETERIZATION_ID
        else unit.candidate_or_reference
    )
    kwargs = {
        "parameter_set_id": REFERENCE_PARAMETERIZATION_ID,
        "master_seed": unit.seed,
        "mode_id": mode_id,
        "replica": unit.replica,
        "candidate_parameterization_id": candidate_id,
    }
    left = run_policy(config, policy=left_policy, **kwargs)
    right = run_policy(config, policy=right_policy, **kwargs)
    result = {
        "unit_id": unit.unit_id,
        **unit.payload(),
        "pair_definition": {
            "pair_id": pair.pair_id,
            "left_policy_id": pair.left_policy_id,
            "right_policy_id": pair.right_policy_id,
            "changed_factor": pair.changed_factor,
            "controlled_factors": list(pair.controlled_factors),
        },
        "left": _compact_policy_result(left),
        "right": _compact_policy_result(right),
        "comparison": _comparison(left, right),
    }
    result["unit_digest"] = canonical_digest(result)
    return result


def _candidate_context() -> RewardExecutionContext:
    return RewardExecutionContext(day=60, retention_transition_days=(30, 60))


def evaluate_screening_invariants(candidate_id: str) -> dict[str, bool | float]:
    parameterization = (
        None if candidate_id == REFERENCE_PARAMETERIZATION_ID else candidate_id
    )
    context = _candidate_context()
    ordinary = ReviewEpisodeInput(
        "ordinary", "ordinary-card", "2026-01-01", Outcome.GOOD
    )
    again = replace(ordinary, source_event_key="again", outcome=Outcome.AGAIN)
    ordinary_result = evaluate_episode(
        ordinary,
        CURRENT_PARAMETERS,
        candidate_parameterization_id=parameterization,
        execution_context=context,
    )
    again_result = evaluate_episode(
        again,
        CURRENT_PARAMETERS,
        candidate_parameterization_id=parameterization,
        execution_context=context,
    )
    successful_totals = []
    for outcome in (Outcome.HARD, Outcome.GOOD, Outcome.EASY):
        successful_totals.append(
            evaluate_episode(
                replace(
                    ordinary,
                    source_event_key=f"button-{outcome.value}",
                    outcome=outcome,
                ),
                CURRENT_PARAMETERS,
                candidate_parameterization_id=parameterization,
                execution_context=context,
            ).total
        )

    memory = MemoryContext(
        retrievability_actual=0.5,
        retrievability_natural_due=0.5,
        stability_before=1.0,
        stability_good_counterfactual=2.0,
        confidence=ConfidenceLevel.HIGH,
    )
    full = evaluate_episode(
        replace(ordinary, source_event_key="valid-full", memory=memory),
        CURRENT_PARAMETERS,
        candidate_parameterization_id=parameterization,
        execution_context=context,
    )
    half = evaluate_episode(
        replace(
            ordinary,
            source_event_key="valid-half",
            memory=memory,
            response_validity=0.5,
        ),
        CURRENT_PARAMETERS,
        candidate_parameterization_id=parameterization,
        execution_context=context,
    )

    workload = WorkloadSnapshot(
        status=CompletionStatus.PARTIAL,
        natural_due_at_start=1,
        due_visible_under_limits=1,
        due_hidden_by_limits=0,
    )
    day_a = ReviewDayInput(
        "2026-01-01",
        episodes=(ordinary,),
        workload=workload,
        session_ids=("session-a",),
    )
    day_b = replace(day_a, session_ids=("session-a", "session-b"))
    breakdown_a = aggregate_day(
        day_a,
        CURRENT_PARAMETERS,
        candidate_parameterization_id=parameterization,
        execution_context=context,
    )
    breakdown_b = aggregate_day(
        day_b,
        CURRENT_PARAMETERS,
        candidate_parameterization_id=parameterization,
        execution_context=context,
    )
    return {
        "ordinary_review_unit": ordinary_result.total,
        "again_attempt_credit": again_result.total,
        "button_direct_reward_neutral": all(
            math.isclose(value, successful_totals[0], abs_tol=ABS_TOLERANCE)
            for value in successful_totals
        ),
        "session_invariant": breakdown_a == breakdown_b,
        "response_time_positive_reward_absent": (
            "response_time" not in {item.name for item in fields(ReviewEpisodeInput)}
        ),
        "response_validity_proportional": (
            math.isclose(half.baseline, full.baseline, abs_tol=ABS_TOLERANCE)
            and math.isclose(half.context, full.context * 0.5, abs_tol=ABS_TOLERANCE)
        ),
        "deterministic_replay": (
            evaluate_episode(
                ordinary,
                CURRENT_PARAMETERS,
                candidate_parameterization_id=parameterization,
                execution_context=context,
            )
            == ordinary_result
        ),
        "research_only_classification": (
            candidate_id == REFERENCE_PARAMETERIZATION_ID
            or any(
                item.parameterization_id == candidate_id
                for item in FROZEN_REVIEW_CANDIDATES
            )
        ),
    }


def _gate(predicate_id: str, passed: bool, observed: Any) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id,
        "status": "PASS" if passed else "FAIL",
        "observed": observed,
    }


def evaluate_screening_gates(
    units: Sequence[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    validate_screening_manifest(manifest)
    if len(units) != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening evidence must contain exactly 160 units")
    by_key: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for item in units:
        key = (
            item["candidate_or_reference"],
            item["policy_pair"],
            item["control_condition"],
            item["horizon"],
            item["replica"],
            item["seed"],
            item["population_variant"],
        )
        if key in by_key:
            raise ValueError("duplicate screening evidence tuple")
        by_key[key] = item
    if len(by_key) != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening evidence tuple accounting drifted")

    variants = tuple(manifest["axes"]["candidate_or_reference"])
    candidate_ids = tuple(
        item for item in variants if item != REFERENCE_PARAMETERIZATION_ID
    )
    invariants = {
        candidate_id: evaluate_screening_invariants(candidate_id)
        for candidate_id in variants
    }
    outcomes = []
    for candidate_id in candidate_ids:
        rows = [
            item for key, item in by_key.items()
            if key[0] == candidate_id
        ]
        endpoint_values = [
            item["comparison"]["unexplained_advantage"]
            for item in rows
            if item["horizon"] == 365
            and item["policy_pair"] in {
                "CASE-RETENTION-HIGH",
                "CASE-RETENTION-LOW",
            }
        ]
        growth_values = []
        for case_id in ("CASE-RETENTION-HIGH", "CASE-RETENTION-LOW"):
            for replica in (0, 1):
                for seed in (20260716, 20260717):
                    shared = (
                        case_id,
                        "MATCHED_CONTROL_FROM_CASE",
                        replica,
                        seed,
                        "CANONICAL_SYNTHETIC_COHORT",
                    )
                    short = by_key[(candidate_id, shared[0], shared[1], 90, shared[2], shared[3], shared[4])]
                    long = by_key[(candidate_id, shared[0], shared[1], 365, shared[2], shared[3], shared[4])]
                    growth_values.append(
                        long["comparison"]["unexplained_advantage"]
                        - short["comparison"]["unexplained_advantage"]
                    )

        baseline_deltas = []
        honest_differentials = []
        intentional_deltas = []
        suppression_events = 0
        for item in rows:
            reference = by_key[(
                REFERENCE_PARAMETERIZATION_ID,
                item["policy_pair"],
                item["control_condition"],
                item["horizon"],
                item["replica"],
                item["seed"],
                item["population_variant"],
            )]
            baseline_deltas.append(
                abs(
                    item["comparison"]["baseline_delta"]
                    - reference["comparison"]["baseline_delta"]
                )
            )
            suppression_events += item["comparison"]["suppression_events"]
            if item["policy_pair"] == "CASE-HONEST-BACKLOG-RETURN":
                honest_differentials.append(
                    item["comparison"]["total_delta"]
                    - reference["comparison"]["total_delta"]
                )
            if item["policy_pair"] == "CASE-INTENTIONAL-BACKLOG":
                intentional_deltas.append(
                    item["comparison"]["unexplained_advantage"]
                    - reference["comparison"]["unexplained_advantage"]
                )

        invariant = invariants[candidate_id]
        gates = [
            _gate(
                "GATE-ENDPOINT-CAP",
                all(value <= 0.03 + ABS_TOLERANCE for value in endpoint_values),
                endpoint_values,
            ),
            _gate(
                "GATE-NO-CYCLING-GROWTH",
                all(value <= ABS_TOLERANCE for value in growth_values),
                growth_values,
            ),
            _gate(
                "GATE-BASELINE-PRESERVED",
                max(baseline_deltas, default=math.inf) <= ABS_TOLERANCE,
                max(baseline_deltas, default=None),
            ),
            _gate(
                "GATE-ZERO-SUPPRESSION",
                suppression_events == 0,
                suppression_events,
            ),
            _gate(
                "GATE-HONEST-BACKLOG-FAIRNESS",
                all(value >= -ABS_TOLERANCE for value in honest_differentials),
                honest_differentials,
            ),
            _gate(
                "GATE-NO-BACKLOG-GAIN",
                all(value <= ABS_TOLERANCE for value in intentional_deltas),
                intentional_deltas,
            ),
            _gate(
                "GATE-ORDINARY-UNIT",
                math.isclose(
                    float(invariant["ordinary_review_unit"]),
                    1.0,
                    abs_tol=ABS_TOLERANCE,
                ),
                invariant["ordinary_review_unit"],
            ),
            _gate(
                "GATE-AGAIN-CREDIT",
                math.isclose(
                    float(invariant["again_attempt_credit"]),
                    0.25,
                    abs_tol=ABS_TOLERANCE,
                ),
                invariant["again_attempt_credit"],
            ),
            _gate(
                "GATE-BUTTON-NEUTRAL",
                bool(invariant["button_direct_reward_neutral"]),
                invariant["button_direct_reward_neutral"],
            ),
            _gate(
                "GATE-SESSION-INVARIANT",
                bool(invariant["session_invariant"]),
                invariant["session_invariant"],
            ),
            _gate(
                "GATE-NO-RESPONSE-TIME-REWARD",
                bool(invariant["response_time_positive_reward_absent"]),
                invariant["response_time_positive_reward_absent"],
            ),
            _gate(
                "GATE-RESPONSE-VALIDITY",
                bool(invariant["response_validity_proportional"]),
                invariant["response_validity_proportional"],
            ),
            _gate(
                "GATE-DETERMINISTIC-REPLAY",
                bool(invariant["deterministic_replay"]),
                invariant["deterministic_replay"],
            ),
            _gate(
                "GATE-SECONDARY-SEED",
                set(manifest["axes"]["seeds"]) == {20260716, 20260717},
                manifest["axes"]["seeds"],
            ),
            _gate(
                "GATE-EVIDENCE-COMPLETE",
                len(rows) == 32,
                len(rows),
            ),
            _gate(
                "GATE-RESEARCH-ONLY",
                bool(invariant["research_only_classification"]),
                invariant["research_only_classification"],
            ),
        ]
        family = next(
            item.family_id
            for item in FROZEN_REVIEW_CANDIDATES
            if item.parameterization_id == candidate_id
        )
        passed = all(item["status"] == "PASS" for item in gates)
        outcomes.append(
            {
                "parameterization_id": candidate_id,
                "family_id": family,
                "status": "PASS" if passed else "REJECT",
                "survivor_eligible": passed,
                "gates": gates,
            }
        )

    family_candidates = {
        family: [
            item["parameterization_id"]
            for item in outcomes
            if item["family_id"] == family and item["survivor_eligible"]
        ]
        for family in sorted({item.family_id for item in FROZEN_REVIEW_CANDIDATES})
    }
    return {
        "status": "COMPLETE",
        "reference_parameterization_id": REFERENCE_PARAMETERIZATION_ID,
        "parameterizations": outcomes,
        "eligible_parameterizations_by_family": family_candidates,
        "invariants": invariants,
    }


def _git_output(workspace: ResearchWorkspace, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(workspace.root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _validate_git_identity(
    workspace: ResearchWorkspace,
    implementation_sha: str,
    base_sha: str,
) -> None:
    if not all(
        len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
        for value in (implementation_sha, base_sha)
    ):
        raise ValueError("implementation/base SHA must be lowercase 40-character hex")
    if _git_output(workspace, "rev-parse", "HEAD") != implementation_sha:
        raise ValueError("implementation SHA does not match current HEAD")
    subprocess.run(
        ["git", "-C", str(workspace.root), "merge-base", "--is-ancestor", base_sha, implementation_sha],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_bounded_screening(
    workspace: ResearchWorkspace | Path | str | None,
    *,
    implementation_sha: str,
    base_sha: str,
    exact_command: str,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    _validate_git_identity(resolved, implementation_sha, base_sha)
    manifest = build_screening_manifest(resolved)
    validate_screening_manifest(manifest)
    unit_results = []
    for item in manifest["units"]:
        unit_results.append(
            run_screening_execution_unit(
                ScreeningExecutionUnit(
                    item["candidate_or_reference"],
                    item["policy_pair"],
                    item["control_condition"],
                    item["horizon"],
                    item["replica"],
                    item["seed"],
                    item["population_variant"],
                ),
                workspace=resolved,
            )
        )
    gate_evidence = evaluate_screening_gates(unit_results, manifest=manifest)
    payload = {
        "evidence_version": "review-xp-bounded-screening-evidence-v1",
        "provenance": {
            "implementation_sha": implementation_sha,
            "base_sha": base_sha,
            "branch": _git_output(resolved, "branch", "--show-current"),
            "python_version": sys.version.split()[0],
            "fsrs_version": importlib.metadata.version("fsrs"),
            "jsonschema_version": importlib.metadata.version("jsonschema"),
            "exact_command": exact_command,
        },
        "manifest": manifest,
        "units": unit_results,
        "gate_evidence": gate_evidence,
    }
    payload["evidence_digest"] = canonical_digest(payload)
    validate_bounded_screening_result(payload)
    return payload


def validate_bounded_screening_result(payload: Mapping[str, Any]) -> None:
    manifest = payload.get("manifest")
    units = payload.get("units")
    gate_evidence = payload.get("gate_evidence")
    if not isinstance(manifest, dict):
        raise ValueError("screening result manifest is missing")
    if not isinstance(units, list):
        raise ValueError("screening result units are missing")
    if not isinstance(gate_evidence, dict):
        raise ValueError("screening gate evidence is missing")
    validate_screening_manifest(manifest)
    if len(units) != EXPECTED_SCREENING_UNIT_COUNT:
        raise ValueError("screening result unit count drifted")
    if gate_evidence.get("status") != "COMPLETE":
        raise ValueError("screening gate evidence is incomplete")
    digest = payload.get("evidence_digest")
    without_digest = dict(payload)
    without_digest.pop("evidence_digest", None)
    if digest != canonical_digest(without_digest):
        raise ValueError("screening evidence digest mismatch")


def render_bounded_screening_summary(payload: Mapping[str, Any]) -> str:
    manifest = payload["manifest"]
    evidence = payload["gate_evidence"]
    lines = [
        "# G1.4 bounded Review XP screening",
        "",
        f"- Implementation SHA: `{payload['provenance']['implementation_sha']}`",
        f"- Base SHA: `{payload['provenance']['base_sha']}`",
        f"- Expected units: **{manifest['expected_units']}**",
        f"- Actual unique units: **{manifest['actual_unique_units']}**",
        f"- Missing / extra / duplicates: **{manifest['missing_units']} / {manifest['extra_units']} / {manifest['duplicate_units']}**",
        f"- Evidence digest: `{payload['evidence_digest']}`",
        "",
        "| Family | Parameterization | Status |",
        "|---|---|---|",
    ]
    for item in evidence["parameterizations"]:
        lines.append(
            f"| `{item['family_id']}` | `{item['parameterization_id']}` | `{item['status']}` |"
        )
    return "\n".join(lines) + "\n"


def write_bounded_screening_reports(
    payload: Mapping[str, Any],
    output_root: Path,
) -> Path:
    validate_bounded_screening_result(payload)
    if output_root.exists() and output_root.is_symlink():
        raise ValueError("screening output root must not be a symlink")
    run_dir = (
        output_root.resolve()
        / "bounded-screening"
        / str(payload["evidence_digest"])[:12]
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    if run_dir.is_symlink():
        raise ValueError("screening output directory must not be a symlink")
    (run_dir / "evidence.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(payload["manifest"], indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "summary.md").write_text(
        render_bounded_screening_summary(payload),
        encoding="utf-8",
    )
    (run_dir / "run-metadata.json").write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "implementation_sha": payload["provenance"]["implementation_sha"],
                "evidence_digest": payload["evidence_digest"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return run_dir
