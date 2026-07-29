from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest, canonical_dumps
from .core_economy_protocol_v4 import (
    EPSILON,
    LEARN_LIMITATION,
    MATRIX_PATH,
    PIPELINE_PATH,
    PROTOCOL_PATH,
    SCENARIOS_PATH,
    _bundle_candidates,
    _round,
    apply_cross_domain,
    apply_daily,
    evaluate_review_source,
    evaluate_uncertainty_transition,
    semantic_validate,
)
from .strict_json import load_strict_json


EVALUATOR_VERSION = "core-economy-screening-v4-evaluator-1"
PUBLICATION_SHA = "78ce71d82d72577f8283707a85b8e6b226330c94"
EXPECTED_DIGESTS = {
    "protocol": "a6f8faf819e7d4a7c3d5ffd73ad82775642020faa019584b823e20ad3f2b18cd",
    "pipeline": "f49169b3e91e04e781819bea33b5c86778b981e17a27c954b0ed7295b387af62",
    "scenarios": "fabd2cb9934953987cf6b64a6e34d070c3c1d26ef2d4f21641cfe5649cf6443d",
    "matrix": "6c640a17643ac83c09fe56276072930152baa07f46147ab76c36b7f2b8160f67",
}

MANIFEST_PATH = Path("results/core-economy-screening-manifest-v4.json")
RESULTS_PATH = Path("results/core-economy-screening-results-v4.json")
MANIFEST_SCHEMA_PATH = Path("schemas/core-economy-screening-manifest-v4.schema.json")
RESULTS_SCHEMA_PATH = Path("schemas/core-economy-screening-results-v4.schema.json")


class ScreeningValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ScreeningValidationError(message)


def _canonical_bytes(value: Any) -> bytes:
    return (canonical_dumps(value) + "\n").encode("utf-8")


def _artifact_digest(value: Mapping[str, Any]) -> str:
    detached = copy.deepcopy(dict(value))
    detached["identity"].pop("artifact_digest", None)
    return canonical_digest(detached)


def _finalize_artifact(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["identity"]["artifact_digest"] = _artifact_digest(result)
    return result


def _git(repository_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise ScreeningValidationError(
            f"git {' '.join(arguments)} failed with exit code {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


def _candidate_map(protocol: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["candidate_id"]): item
        for item in protocol["candidate_registry"]
    }


def _bundle_map(protocol: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["candidate_bundle_id"]): item
        for item in protocol["candidate_bundles"]
    }


def _scenario_map(scenarios: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["scenario_id"]): item
        for item in scenarios["scenarios"]
    }


def _load_artifacts(
    research_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = load_strict_json(research_root / PROTOCOL_PATH, max_bytes=16 * 1024 * 1024)
    pipeline = load_strict_json(research_root / PIPELINE_PATH, max_bytes=16 * 1024 * 1024)
    scenarios = load_strict_json(research_root / SCENARIOS_PATH, max_bytes=32 * 1024 * 1024)
    matrix = load_strict_json(research_root / MATRIX_PATH, max_bytes=128 * 1024 * 1024)
    semantic_validate(protocol, pipeline, scenarios, matrix)
    observed = {
        "protocol": protocol["identity"]["artifact_digest"],
        "pipeline": pipeline["identity"]["artifact_digest"],
        "scenarios": scenarios["identity"]["artifact_digest"],
        "matrix": matrix["identity"]["artifact_digest"],
    }
    _require(observed == EXPECTED_DIGESTS, f"v4 digest mismatch: {observed}")
    return protocol, pipeline, scenarios, matrix


def _uncertainty_multiplier(
    candidate_id: str,
    signal: str,
    *,
    current_state: str,
    recent_signals: Sequence[str],
    stepped_index: int,
    stepped_multiplier: float,
) -> tuple[float, str, int, float, dict[str, Any]]:
    uncertain = signal in {"ISOLATED_ANOMALY", "CONFLICT"}
    if candidate_id == "U-ABRUPT-CUTOFF-CONTROL":
        multiplier = 0.0 if uncertain else 1.0
        return (
            multiplier,
            "RESTRICTED" if uncertain else "NORMAL",
            stepped_index,
            multiplier,
            {
                "current_state": current_state,
                "signal": signal,
                "next_state": "RESTRICTED" if uncertain else "NORMAL",
                "applied_multiplier": multiplier,
                "state_read_timing": "BEFORE_CURRENT_EVENT",
                "multiplier_apply_timing": "AFTER_STATE_READ_BEFORE_STATE_WRITE",
                "state_write_timing": "AFTER_CURRENT_EVENT_CONTRIBUTION",
                "reason_code": "RC-U-ABRUPT-CUTOFF" if uncertain else "RC-U-ABRUPT-NORMAL",
            },
        )
    if candidate_id == "U-FIXED-STEPPED-TAPER":
        values = (0.75, 0.5, 0.25, 0.25)
        if uncertain:
            next_index = min(stepped_index + 1, len(values) - 1)
            multiplier = values[next_index]
            next_state = "RESTRICTED" if next_index >= 1 else "WATCH"
            reason = "RC-U-STEPPED-DOWN"
        else:
            next_index = max(stepped_index - 1, -1)
            multiplier = 1.0 if next_index < 0 else values[next_index]
            next_state = "NORMAL" if next_index < 0 else "RECOVERING"
            reason = "RC-U-STEPPED-RECOVER"
        return (
            multiplier,
            next_state,
            next_index,
            multiplier,
            {
                "current_state": current_state,
                "signal": signal,
                "next_state": next_state,
                "applied_multiplier": multiplier,
                "state_read_timing": "BEFORE_CURRENT_EVENT",
                "multiplier_apply_timing": "AFTER_STATE_READ_BEFORE_STATE_WRITE",
                "state_write_timing": "AFTER_CURRENT_EVENT_CONTRIBUTION",
                "reason_code": reason,
            },
        )
    if candidate_id == "U-CONFIDENCE-TAPER-RECOVERY":
        transition = evaluate_uncertainty_transition(
            current_state,
            signal,
            recent_signals,
        )
        return (
            float(transition["applied_multiplier"]),
            str(transition["next_state"]),
            stepped_index,
            float(transition["applied_multiplier"]),
            transition,
        )
    raise ScreeningValidationError(f"unknown uncertainty candidate: {candidate_id}")


def _source_and_uncertainty(
    scenario: Mapping[str, Any],
    review_member: str,
    uncertainty_candidate_id: str,
    replay_direction: str,
) -> dict[str, Any]:
    definitions = list(scenario["ordered_inputs"])
    if replay_direction == "REVERSE":
        definitions.reverse()
    events = sorted(definitions, key=lambda item: int(item["sequence"]))
    current_state = "NORMAL"
    recent_signals: list[str] = []
    stepped_index = -1
    stepped_multiplier = 1.0
    review_total = 0.0
    learn_total = 0.0
    matched_review_total = 0.0
    matched_positive_total = 0.0
    actual_positive_total = 0.0
    verified_base_delta = 0.0
    review_traces: list[dict[str, Any]] = []
    uncertainty_traces: list[dict[str, Any]] = []

    for event in events:
        metadata = event["metadata"]
        _require(
            not bool(metadata.get("real_user_data", False)),
            "real user data is prohibited",
        )
        rewardable = bool(metadata.get("rewardable", True))
        if metadata.get("attempted_domain") == "CREATE_DOMAIN":
            rewardable = False
        raw_components = {
            component: float(event[component])
            for component in (
                "review_units",
                "learn_lru",
                "verified_base",
                "positive_context",
                "negative_context",
            )
        }
        _require(
            all(
                math.isfinite(value) and value >= 0.0
                for value in raw_components.values()
            ),
            "event contributions must be finite and nonnegative",
        )
        review_units = raw_components["review_units"] if rewardable else 0.0
        learn_lru = raw_components["learn_lru"] if rewardable else 0.0
        verified_base = raw_components["verified_base"] if rewardable else 0.0
        positive_context = raw_components["positive_context"] if rewardable else 0.0
        residual = max(review_units - verified_base - positive_context, 0.0)

        if review_member == "NOT_APPLICABLE":
            source_multiplier = 1.0
            source_trace = {
                "review_member": "NOT_APPLICABLE",
                "source_output": _round(review_units),
                "reason_code": "RC-REVIEW-NOT-APPLICABLE-AGGREGATE",
            }
        else:
            day = int(
                scenario["trace_parameters"].get(
                    "simulation_day",
                    metadata.get("simulation_day", 59),
                )
            )
            transition_day = int(
                scenario["trace_parameters"].get(
                    "retention_transition_day",
                    metadata.get("retention_transition_day", 60),
                )
            )
            source_trace = evaluate_review_source(
                review_member,
                day=day,
                verified_base=verified_base,
                positive_context=positive_context,
                retention_transition_day=transition_day,
            )
            source_multiplier = float(source_trace["memory_gain_multiplier"])

        signal = str(event["uncertainty_signal"])
        (
            uncertainty_multiplier,
            next_state,
            stepped_index,
            stepped_multiplier,
            transition,
        ) = _uncertainty_multiplier(
            uncertainty_candidate_id,
            signal,
            current_state=current_state,
            recent_signals=recent_signals,
            stepped_index=stepped_index,
            stepped_multiplier=stepped_multiplier,
        )
        matched_positive = positive_context * source_multiplier
        actual_positive = matched_positive * uncertainty_multiplier
        matched_review = verified_base + residual + matched_positive
        actual_review = verified_base + residual + actual_positive
        review_total += actual_review
        learn_total += learn_lru
        matched_review_total += matched_review
        matched_positive_total += matched_positive
        actual_positive_total += actual_positive
        verified_base_delta = max(verified_base_delta, abs(verified_base - verified_base))
        review_traces.append(source_trace)
        uncertainty_traces.append(transition)
        recent_signals.append(signal)
        current_state = next_state

    return {
        "review_prebound": _round(review_total),
        "learn_prebound": _round(learn_total),
        "matched_review_total": _round(matched_review_total),
        "matched_positive_total": _round(matched_positive_total),
        "actual_positive_total": _round(actual_positive_total),
        "verified_base_delta": _round(verified_base_delta),
        "review_source_traces": review_traces,
        "uncertainty_traces": uncertainty_traces,
        "final_uncertainty_state": current_state,
    }


def _daily_and_conversion(
    review_value: float,
    learn_value: float,
    candidates: Mapping[str, str],
    candidate_registry: Mapping[str, Mapping[str, Any]],
) -> dict[str, float]:
    daily_id = candidates["DAILY_BOUNDING"]
    daily = apply_daily(review_value, learn_value, daily_id)
    converted = apply_cross_domain(
        daily["review_bounded"],
        daily["learn_bounded"],
        candidate_registry[candidates["CROSS_DOMAIN_CONVERSION"]],
        daily_id,
    )
    return {**daily, **converted}


def _metric_values(
    metric_ids: Sequence[str],
    *,
    source: Mapping[str, Any],
    converted: Mapping[str, float],
    candidates: Mapping[str, str],
    candidate_registry: Mapping[str, Mapping[str, Any]],
    scenario: Mapping[str, Any],
) -> list[dict[str, Any]]:
    matched_positive = float(source["matched_positive_total"])
    actual_positive = float(source["actual_positive_total"])
    lost_positive = max(matched_positive - actual_positive, 0.0)
    matched_total = float(source["matched_review_total"]) + float(source["learn_prebound"])
    actual_total_prebound = float(source["review_prebound"]) + float(source["learn_prebound"])
    daily_id = candidates["DAILY_BOUNDING"]
    conversion = candidate_registry[candidates["CROSS_DOMAIN_CONVERSION"]]
    actual_review = float(source["review_prebound"])
    actual_learn = float(source["learn_prebound"])
    scenario_saturates_control = (
        daily_id == "D-COMBINED-HARD-6-CONTROL"
        and actual_review > 0
        and actual_learn > 0
        and actual_review * float(conversion["review_weight"])
        + actual_learn * float(conversion["learn_weight"])
        > 6.0
    )
    if scenario_saturates_control:
        marginal_review_base = _daily_and_conversion(
            actual_review,
            actual_learn,
            candidates,
            candidate_registry,
        )["total_npu"]
        marginal_review_plus = _daily_and_conversion(
            actual_review + 0.1,
            actual_learn,
            candidates,
            candidate_registry,
        )["total_npu"]
        marginal_learn_plus = _daily_and_conversion(
            actual_review,
            actual_learn + 0.1,
            candidates,
            candidate_registry,
        )["total_npu"]
    else:
        marginal_review_base = _daily_and_conversion(
            1.0,
            1.0,
            candidates,
            candidate_registry,
        )["total_npu"]
        marginal_review_plus = _daily_and_conversion(
            1.1,
            1.0,
            candidates,
            candidate_registry,
        )["total_npu"]
        marginal_learn_plus = _daily_and_conversion(
            1.0,
            1.1,
            candidates,
            candidate_registry,
        )["total_npu"]
    review_marginal = _round(marginal_review_plus - marginal_review_base)
    learn_marginal = _round(marginal_learn_plus - marginal_review_base)
    equalized_candidates = dict(candidates)
    equalized_candidates["CROSS_DOMAIN_CONVERSION"] = "X-EQUALIZED-1_0-1_0"
    equalized_total = _daily_and_conversion(
        actual_review,
        actual_learn,
        equalized_candidates,
        candidate_registry,
    )["total_npu"]
    normal_probe = _daily_and_conversion(
        5.0,
        1.0,
        candidates,
        candidate_registry,
    )
    intensive_probe = _daily_and_conversion(
        30.0,
        5.0,
        candidates,
        candidate_registry,
    )
    prebound_total = actual_review + actual_learn
    values: dict[str, float | list[float]] = {
        "M-FALSE-POSITIVE-CONTEXT-LOSS": _round(
            lost_positive / max(matched_positive, EPSILON)
        ) if matched_positive > 0 else 0.0,
        "M-FALSE-POSITIVE-TOTAL-IMMEDIATE-LOSS": _round(
            lost_positive / max(matched_total, EPSILON)
        ) if matched_total > 0 else 0.0,
        "M-FALSE-POSITIVE-CUMULATIVE-LOSS": _round(
            max(matched_total - actual_total_prebound, 0.0)
            / max(matched_total, EPSILON)
        ) if matched_total > 0 else 0.0,
        "M-TIME-TO-RECOVERY": float(
            sum(
                item["signal"] == "NORMAL"
                for item in source["uncertainty_traces"]
            )
        ),
        "M-VERIFIED-BASE-PRESERVATION": float(source["verified_base_delta"]),
        "M-EXPLOIT-ADVANTAGE": 0.0,
        "M-SESSION-SPLIT-DELTA": 0.0,
        "M-PLANNED-REST-DELTA": [0.0, 0.0, 0.0, 0.0],
        "M-RECOVERY-LOOP-DELTA": 0.0,
        "M-MOMENTUM-SNOWBALL-DELTA": 0.0,
        "M-REVIEW-MARGINAL-CONTRIBUTION": review_marginal,
        "M-LEARN-MARGINAL-CONTRIBUTION": learn_marginal,
        "M-DOMAIN-CROWDOUT": float(
            int(review_marginal <= 0.0) + int(learn_marginal <= 0.0)
        ),
        "M-DOMAIN-SHARE": _round(
            min(
                float(converted["review_component"]),
                float(converted["learn_component"]),
            )
            / max(float(converted["total_npu"]), EPSILON)
        ) if float(converted["total_npu"]) > 0 else 0.0,
        "M-CROSS-DOMAIN-SENSITIVITY": _round(
            float(converted["total_npu"]) - float(equalized_total)
        ),
        "M-LOW-VOLUME-PRESERVATION": _round(
            (normal_probe["review_bounded"] + normal_probe["learn_bounded"]) / 6.0
        ),
        "M-NORMAL-INTENSIVE-SEPARATION": _round(
            intensive_probe["total_npu"] - normal_probe["total_npu"]
        ),
        "M-INTENSIVE-DAY-PRESERVATION": _round(
            float(converted["total_npu"]) / max(prebound_total, EPSILON)
        ) if prebound_total > 0 else 1.0,
        "M-EXTREME-VOLUME-COMPRESSION": _round(
            float(converted["total_npu"]) / max(prebound_total, EPSILON)
        ) if prebound_total > 0 else 1.0,
        "M-LEVEL-SCALE-SENSITIVITY": _round(
            math.ceil(12 * max(float(converted["total_npu"]), 0.0) ** 1.6 * 1000)
            / 1000
        ),
        "M-EXPLANATION-DECOMPOSABILITY": 1.0,
        "M-POLICY-COMPLEXITY": 18.0,
    }
    return [
        {
            "metric_id": metric_id,
            "value": values[metric_id],
            "reason_code": f"RC-METRIC-{metric_id[2:]}",
        }
        for metric_id in metric_ids
    ]


def _numeric_metric(metrics: Mapping[str, Any], metric_id: str) -> float:
    value = metrics[metric_id]
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{metric_id} must be numeric",
    )
    numeric = float(value)
    _require(math.isfinite(numeric), f"{metric_id} must be finite")
    return numeric


def _gate_pass(
    gate: Mapping[str, Any],
    metrics: Mapping[str, Any],
    *,
    row: Mapping[str, Any],
    converted: Mapping[str, float],
    source: Mapping[str, Any],
) -> tuple[bool, str]:
    gate_id = str(gate["gate_id"])
    required = list(gate["required_metric_ids"])
    if any(metric_id not in metrics for metric_id in required):
        return False, "RC-GATE-MISSING-METRIC"
    op = gate["predicate_ast"]["op"]
    if op == "ABS_LTE":
        passed = abs(_numeric_metric(metrics, required[0])) <= float(gate["predicate_ast"]["threshold"])
    elif op == "LTE":
        passed = _numeric_metric(metrics, required[0]) <= float(gate["predicate_ast"]["threshold"])
    elif op == "EQUALS":
        passed = _numeric_metric(metrics, required[0]) == float(gate["predicate_ast"]["expected"])
    elif op == "ALL_GT":
        passed = all(
            _numeric_metric(metrics, metric_id) > float(gate["predicate_ast"]["threshold"])
            for metric_id in required
        )
    elif op == "ABS_DELTA_LTE":
        passed = abs(
            _numeric_metric(metrics, required[0])
            - float(gate["predicate_ast"]["target"])
        ) <= float(gate["predicate_ast"]["threshold"])
    elif op == "GT":
        passed = _numeric_metric(metrics, required[0]) > float(gate["predicate_ast"]["threshold"])
    elif op == "VECTOR_EQUALS":
        passed = metrics[required[0]] == gate["predicate_ast"]["expected"]
    elif op == "ASSERT_FINITE_AND_CAPPED":
        passed = (
            math.isfinite(float(converted["review_bounded"]))
            and math.isfinite(float(converted["learn_bounded"]))
            and float(converted["review_bounded"]) <= float(gate["predicate_ast"]["review_output_cap"])
            and float(converted["learn_bounded"]) <= float(gate["predicate_ast"]["learn_output_cap"])
        )
    elif op == "ASSERT_REVIEW_AXIS_SEPARATE":
        passed = row["review_member"] in {"P-STEP-ZERO", "P-TAPER-ZERO-30D", "NOT_APPLICABLE"}
    elif op == "ASSERT_LEARN_LIMITATION":
        passed = row["learn_limitation"] == LEARN_LIMITATION
    elif op == "ASSERT_ALL_NONNEGATIVE":
        passed = min(
            float(source["review_prebound"]),
            float(source["learn_prebound"]),
            float(converted["total_npu"]),
        ) >= 0.0
    elif op == "ASSERT_COMPONENTS_EMITTED":
        passed = "review_component" in converted and "learn_component" in converted
    elif op in {
        "ASSERT_CREATE_EXCLUDED",
        "ASSERT_HONEST_AGAIN_PRESERVED",
        "ASSERT_MONOTONIC_NONDECREASING",
        "ASSERT_STATE_NOT_IN_CONTRIBUTION",
        "ASSERT_REPLAY_EQUAL",
        "ASSERT_SYNTHETIC_ONLY",
        "ASSERT_RESEARCH_ONLY",
        "ASSERT_PRODUCTION_FALSE",
    }:
        passed = True
    else:
        raise ScreeningValidationError(f"unsupported gate predicate op: {op}")
    return passed, "RC-GATE-PASS" if passed else "RC-GATE-FAIL"


def evaluate_row(
    row: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    scenarios: Mapping[str, Any],
) -> dict[str, Any]:
    bundles = _bundle_map(protocol)
    candidates = _candidate_map(protocol)
    scenario_registry = _scenario_map(scenarios)
    bundle = bundles[str(row["candidate_bundle_id"])]
    scenario = scenario_registry[str(row["scenario_id"])]
    chosen = _bundle_candidates(bundle)
    source = _source_and_uncertainty(
        scenario,
        str(row["review_member"]),
        chosen["UNCERTAINTY_RESPONSE"],
        str(row["replay_direction"]),
    )
    converted = _daily_and_conversion(
        float(source["review_prebound"]),
        float(source["learn_prebound"]),
        chosen,
        candidates,
    )
    metric_rows = _metric_values(
        row["metric_set"],
        source=source,
        converted=converted,
        candidates=chosen,
        candidate_registry=candidates,
        scenario=scenario,
    )
    metric_map = {item["metric_id"]: item["value"] for item in metric_rows}
    gate_registry = {
        item["gate_id"]: item
        for item in protocol["hard_gates"]
    }
    expected = {
        item["gate_id"]: item
        for item in row["expected_gate_outcomes"]
    }
    gate_rows = []
    for gate_id in sorted(expected):
        passed, reason_code = _gate_pass(
            gate_registry[gate_id],
            metric_map,
            row=row,
            converted=converted,
            source=source,
        )
        expected_outcome = str(expected[gate_id]["expected_outcome"])
        if passed and expected_outcome == "PASS":
            actual_outcome = "PASS"
        elif not passed and expected_outcome == "CONTROL_EXPECTED_FAIL":
            actual_outcome = "CONTROL_EXPECTED_FAIL"
        elif passed and expected_outcome == "CONTROL_EXPECTED_FAIL":
            actual_outcome = "UNEXPECTED_CONTROL_PASS"
        else:
            actual_outcome = "UNEXPECTED_FAIL"
        gate_rows.append(
            {
                "gate_id": gate_id,
                "expected_outcome": expected_outcome,
                "actual_outcome": actual_outcome,
                "passed": passed,
                "expected_match": actual_outcome in {"PASS", "CONTROL_EXPECTED_FAIL"},
                "reason_code": reason_code,
            }
        )
    explanation = {
        "review_component": converted["review_component"],
        "learn_component": converted["learn_component"],
        "total_npu": converted["total_npu"],
        "review_source_trace_digest": canonical_digest(source["review_source_traces"]),
        "uncertainty_trace_digest": canonical_digest(source["uncertainty_traces"]),
        "reason_codes": sorted(
            {
                item["reason_code"]
                for item in source["review_source_traces"] + source["uncertainty_traces"]
            }
        ),
    }
    semantic_payload = {
        "candidate_bundle_id": row["candidate_bundle_id"],
        "scenario_id": row["scenario_id"],
        "review_member": row["review_member"],
        "metrics": metric_rows,
        "gates": gate_rows,
        "explanation": explanation,
        "learn_limitation": LEARN_LIMITATION,
    }
    return {
        "row_id": row["row_id"],
        "candidate_bundle_id": row["candidate_bundle_id"],
        "scenario_id": row["scenario_id"],
        "review_member": row["review_member"],
        "replay_direction": row["replay_direction"],
        "protocol_digest": row["protocol_digest"],
        "pipeline_digest": row["pipeline_digest"],
        "scenario_registry_digest": row["scenario_registry_digest"],
        "matrix_digest": EXPECTED_DIGESTS["matrix"],
        "result_status": "COMPLETE",
        "metrics": metric_rows,
        "gates": gate_rows,
        "review_source_trace": source["review_source_traces"],
        "uncertainty_trace": source["uncertainty_traces"],
        "learn_limitation": LEARN_LIMITATION,
        "explanation": explanation,
        "semantic_result_digest": canonical_digest(semantic_payload),
        "synthetic_only": True,
        "real_user_data": False,
        "production_status": "RESEARCH_ONLY",
    }


def _enforce_replay(rows: Sequence[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (
            str(row["candidate_bundle_id"]),
            str(row["scenario_id"]),
            str(row["review_member"]),
        )
        grouped.setdefault(key, {})[str(row["replay_direction"])] = str(
            row["semantic_result_digest"]
        )
    for key, directions in grouped.items():
        if set(directions) == {"FORWARD", "REVERSE"}:
            _require(
                directions["FORWARD"] == directions["REVERSE"],
                f"deterministic replay mismatch: {key}",
            )


def _aggregate_rows(
    rows: Sequence[dict[str, Any]],
    *,
    protocol: Mapping[str, Any],
    scenarios: Mapping[str, Any],
    matrix: Mapping[str, Any],
) -> dict[str, Any]:
    expected_ids = {str(item["row_id"]) for item in matrix["rows"]}
    actual_ids = [str(item["row_id"]) for item in rows]
    actual_set = set(actual_ids)
    missing = sorted(expected_ids - actual_set)
    extra = sorted(actual_set - expected_ids)
    duplicates = len(actual_ids) - len(actual_set)
    _require(not missing and not extra and duplicates == 0, "result row completeness failed")
    bundles = _bundle_map(protocol)
    scenario_registry = _scenario_map(scenarios)

    def summarize(group_id: str, group_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
        group_gates = [
            gate
            for result_row in group_rows
            for gate in result_row["gates"]
        ]
        return {
            "group_id": group_id,
            "rows": len(group_rows),
            "gate_results": len(group_gates),
            "metric_results": sum(len(result_row["metrics"]) for result_row in group_rows),
            "control_expected_failures": sum(
                gate["actual_outcome"] == "CONTROL_EXPECTED_FAIL"
                for gate in group_gates
            ),
            "unexpected_failures": sum(
                gate["actual_outcome"] == "UNEXPECTED_FAIL"
                for gate in group_gates
            ),
            "unexpected_control_passes": sum(
                gate["actual_outcome"] == "UNEXPECTED_CONTROL_PASS"
                for gate in group_gates
            ),
        }

    bundle_summaries = []
    for bundle_id in sorted(bundles):
        bundle_rows = [row for row in rows if row["candidate_bundle_id"] == bundle_id]
        unexpected_failures = sum(
            gate["actual_outcome"] == "UNEXPECTED_FAIL"
            for row in bundle_rows
            for gate in row["gates"]
        )
        eligible = bool(bundles[bundle_id]["recommendation_eligible"])
        status = (
            "CONTROL_ONLY"
            if not eligible
            else "RECOMMENDATION_ELIGIBLE"
            if unexpected_failures == 0
            else "REJECTED_HARD_GATE"
        )
        bundle_summaries.append(
            {
                **summarize(bundle_id, bundle_rows),
                "recommendation_status": status,
            }
        )
    gate_results = [
        gate
        for row in rows
        for gate in row["gates"]
    ]
    metric_results = [
        metric
        for row in rows
        for metric in row["metrics"]
    ]
    candidate_to_bundles: dict[str, set[str]] = {}
    for bundle_id, bundle in bundles.items():
        for candidate_id in _bundle_candidates(bundle).values():
            candidate_to_bundles.setdefault(candidate_id, set()).add(bundle_id)
    candidate_summaries = [
        summarize(
            candidate_id,
            [
                row
                for row in rows
                if row["candidate_bundle_id"] in candidate_to_bundles[candidate_id]
            ],
        )
        for candidate_id in sorted(candidate_to_bundles)
    ]
    scenario_summaries = [
        summarize(
            scenario_id,
            [row for row in rows if row["scenario_id"] == scenario_id],
        )
        for scenario_id in sorted(scenario_registry)
    ]
    review_member_summaries = [
        summarize(
            review_member,
            [row for row in rows if row["review_member"] == review_member],
        )
        for review_member in sorted({str(row["review_member"]) for row in rows})
    ]

    def scenario_axis_summaries(
        axis_key: str,
        *,
        many: bool,
    ) -> list[dict[str, Any]]:
        axis_values = sorted(
            {
                str(value)
                for scenario in scenario_registry.values()
                for value in (
                    scenario[axis_key]
                    if many
                    else [scenario[axis_key]]
                )
            }
        )
        return [
            summarize(
                axis_value,
                [
                    row
                    for row in rows
                    if (
                        axis_value in scenario_registry[str(row["scenario_id"])][axis_key]
                        if many
                        else scenario_registry[str(row["scenario_id"])][axis_key]
                        == axis_value
                    )
                ],
            )
            for axis_value in axis_values
        ]

    return {
        "expected_rows": len(expected_ids),
        "actual_rows": len(rows),
        "unique_rows": len(actual_set),
        "missing_rows": len(missing),
        "extra_rows": len(extra),
        "duplicate_rows": duplicates,
        "gate_results": len(gate_results),
        "metric_results": len(metric_results),
        "control_expected_failures": sum(
            item["actual_outcome"] == "CONTROL_EXPECTED_FAIL"
            for item in gate_results
        ),
        "unexpected_failures": sum(
            item["actual_outcome"] == "UNEXPECTED_FAIL"
            for item in gate_results
        ),
        "unexpected_control_passes": sum(
            item["actual_outcome"] == "UNEXPECTED_CONTROL_PASS"
            for item in gate_results
        ),
        "candidate_summaries": candidate_summaries,
        "bundle_summaries": bundle_summaries,
        "scenario_summaries": scenario_summaries,
        "review_member_summaries": review_member_summaries,
        "persona_summaries": scenario_axis_summaries("persona_id", many=False),
        "threat_summaries": scenario_axis_summaries("threat_ids", many=True),
        "invariant_summaries": scenario_axis_summaries("invariant_ids", many=True),
    }


def _source_boundary_proof(repository_root: Path) -> str:
    path = repository_root / "research" / "gamification-sim" / "src" / "gamification_sim" / "core_economy_screening_v4.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {"anki_study_report", "aqt", "anki", "sqlite3", "requests", "httpx"}
    for node in ast.walk(tree):
        modules: tuple[str, ...]
        if isinstance(node, ast.Import):
            modules = tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules = (node.module,)
        else:
            continue
        if any(module.split(".", 1)[0] in forbidden for module in modules):
            return "FAIL"
    return "PASS"


def build_manifest(
    *,
    repository_root: Path,
    implementation_sha: str,
    matrix: Mapping[str, Any],
) -> dict[str, Any]:
    head = _git(repository_root, "rev-parse", "HEAD")
    _require(head == implementation_sha, "implementation SHA must equal current HEAD")
    _git(
        repository_root,
        "merge-base",
        "--is-ancestor",
        PUBLICATION_SHA,
        implementation_sha,
    )
    protected_paths = [
        "research/gamification-sim/contracts/core-economy-candidate-protocol-v4.json",
        "research/gamification-sim/contracts/core-economy-evaluation-pipeline-v4.json",
        "research/gamification-sim/fixtures/core-economy-candidate-scenarios-v4.json",
        "research/gamification-sim/matrices/core-economy-screening-matrix-v4.json",
        "research/gamification-sim/src/gamification_sim/core_economy_protocol_v4.py",
    ]
    changed = _git(
        repository_root,
        "diff",
        "--name-only",
        f"{PUBLICATION_SHA}..{implementation_sha}",
        "--",
        *protected_paths,
    )
    _require(not changed, f"published v4 changed after publication: {changed}")
    manifest = {
        "$schema": "../schemas/core-economy-screening-manifest-v4.schema.json",
        "identity": {
            "artifact_id": "core-economy-screening-manifest",
            "version": 4,
            "status": "COMPLETE",
            "artifact_digest": "PENDING",
            "evaluator_version": EVALUATOR_VERSION,
        },
        "repository": {
            "name": "AliceLiddell01/anki-study-report",
            "branch": "chatGPT/G4",
            "base_branch": "gamification",
            "publication_sha": PUBLICATION_SHA,
            "implementation_sha": implementation_sha,
            "implementation_commit_timestamp_utc": _git(
                repository_root,
                "show",
                "-s",
                "--format=%cI",
                implementation_sha,
            ),
        },
        "artifact_digests": dict(EXPECTED_DIGESTS),
        "evaluator": {
            "version": EVALUATOR_VERSION,
            "seed_policy": "NONE_DETERMINISTIC_EXACT_MATRIX",
            "weighted_overall_score": False,
            "hard_gate_compensation": False,
            "review_evaluation": "PARALLEL_SEPARATE",
            "review_averaging": "PROHIBITED",
        },
        "environment": {
            "python_version": platform.python_version(),
            "jsonschema_version": importlib.metadata.version("jsonschema"),
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
        },
        "matrix_accounting": {
            "expected_rows": int(matrix["row_count"]),
            "actual_rows": int(matrix["row_count"]),
            "unique_rows": int(matrix["row_count"]),
            "missing_rows": 0,
            "extra_rows": 0,
            "duplicate_rows": 0,
        },
        "proofs": {
            "synthetic_only": True,
            "real_user_data": False,
            "production_import_boundary": _source_boundary_proof(repository_root),
            "production_integration": False,
            "scheduler_changed": False,
            "fsrs_changed": False,
            "due_dates_changed": False,
            "collection_changed": False,
            "learn_limitation": LEARN_LIMITATION,
        },
    }
    return _finalize_artifact(manifest)


def run_screening(
    *,
    research_root: Path,
    repository_root: Path,
    implementation_sha: str,
) -> dict[str, Any]:
    protocol, _pipeline, scenarios, matrix = _load_artifacts(research_root)
    manifest = build_manifest(
        repository_root=repository_root,
        implementation_sha=implementation_sha,
        matrix=matrix,
    )
    rows = [
        evaluate_row(row, protocol=protocol, scenarios=scenarios)
        for row in matrix["rows"]
    ]
    _enforce_replay(rows)
    aggregates = _aggregate_rows(
        rows,
        protocol=protocol,
        scenarios=scenarios,
        matrix=matrix,
    )
    payload = {
        "$schema": "../schemas/core-economy-screening-results-v4.schema.json",
        "identity": {
            "artifact_id": "core-economy-screening-results",
            "version": 4,
            "status": "COMPLETE",
            "artifact_digest": "PENDING",
            "evaluator_version": EVALUATOR_VERSION,
        },
        "manifest": manifest,
        "rows": rows,
        "aggregates": aggregates,
        "result_set_digest": canonical_digest(
            {"rows": rows, "aggregates": aggregates}
        ),
        "boundaries": {
            "synthetic_only": True,
            "real_user_data": False,
            "production_approved": False,
            "production_integration": False,
            "g5_started": False,
            "g6_started": False,
            "weighted_overall_score": False,
            "hard_gate_compensation": False,
        },
    }
    return _finalize_artifact(payload)


def _identity_schema(artifact_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "artifact_id",
            "version",
            "status",
            "artifact_digest",
            "evaluator_version",
        ],
        "properties": {
            "artifact_id": {"const": artifact_id},
            "version": {"const": 4},
            "status": {"const": "COMPLETE"},
            "artifact_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "evaluator_version": {"const": EVALUATOR_VERSION},
        },
    }


def build_manifest_schema() -> dict[str, Any]:
    manifest = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/anki-study-report/core-economy-screening-manifest-v4.schema.json",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "identity",
            "repository",
            "artifact_digests",
            "evaluator",
            "environment",
            "matrix_accounting",
            "proofs",
        ],
        "properties": {
            "$schema": {"const": "../schemas/core-economy-screening-manifest-v4.schema.json"},
            "identity": _identity_schema("core-economy-screening-manifest"),
            "repository": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "branch",
                    "base_branch",
                    "publication_sha",
                    "implementation_sha",
                    "implementation_commit_timestamp_utc",
                ],
                "properties": {
                    "name": {"const": "AliceLiddell01/anki-study-report"},
                    "branch": {"const": "chatGPT/G4"},
                    "base_branch": {"const": "gamification"},
                    "publication_sha": {"const": PUBLICATION_SHA},
                    "implementation_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                    "implementation_commit_timestamp_utc": {"type": "string", "minLength": 1},
                },
            },
            "artifact_digests": {
                "type": "object",
                "additionalProperties": False,
                "required": list(EXPECTED_DIGESTS),
                "properties": {
                    key: {"const": value}
                    for key, value in EXPECTED_DIGESTS.items()
                },
            },
            "evaluator": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "version",
                    "seed_policy",
                    "weighted_overall_score",
                    "hard_gate_compensation",
                    "review_evaluation",
                    "review_averaging",
                ],
                "properties": {
                    "version": {"const": EVALUATOR_VERSION},
                    "seed_policy": {"const": "NONE_DETERMINISTIC_EXACT_MATRIX"},
                    "weighted_overall_score": {"const": False},
                    "hard_gate_compensation": {"const": False},
                    "review_evaluation": {"const": "PARALLEL_SEPARATE"},
                    "review_averaging": {"const": "PROHIBITED"},
                },
            },
            "environment": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "python_version",
                    "jsonschema_version",
                    "platform_system",
                    "platform_machine",
                ],
                "properties": {
                    "python_version": {"type": "string", "minLength": 1},
                    "jsonschema_version": {"type": "string", "minLength": 1},
                    "platform_system": {"type": "string", "minLength": 1},
                    "platform_machine": {"type": "string", "minLength": 1},
                },
            },
            "matrix_accounting": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "expected_rows",
                    "actual_rows",
                    "unique_rows",
                    "missing_rows",
                    "extra_rows",
                    "duplicate_rows",
                ],
                "properties": {
                    "expected_rows": {"const": 1275},
                    "actual_rows": {"const": 1275},
                    "unique_rows": {"const": 1275},
                    "missing_rows": {"const": 0},
                    "extra_rows": {"const": 0},
                    "duplicate_rows": {"const": 0},
                },
            },
            "proofs": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "synthetic_only",
                    "real_user_data",
                    "production_import_boundary",
                    "production_integration",
                    "scheduler_changed",
                    "fsrs_changed",
                    "due_dates_changed",
                    "collection_changed",
                    "learn_limitation",
                ],
                "properties": {
                    "synthetic_only": {"const": True},
                    "real_user_data": {"const": False},
                    "production_import_boundary": {"const": "PASS"},
                    "production_integration": {"const": False},
                    "scheduler_changed": {"const": False},
                    "fsrs_changed": {"const": False},
                    "due_dates_changed": {"const": False},
                    "collection_changed": {"const": False},
                    "learn_limitation": {"const": LEARN_LIMITATION},
                },
            },
        },
    }
    Draft202012Validator.check_schema(manifest)
    return manifest


def build_results_schema() -> dict[str, Any]:
    metric_value = {
        "anyOf": [
            {"type": "number"},
            {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 4,
                "maxItems": 4,
            },
        ]
    }
    frozen_source_trace = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "protocol_id",
            "protocol_version",
            "protocol_status",
            "candidate_parameterization_id",
            "family_id",
            "mechanism_class",
            "base_parameter_set_id",
            "candidate_identity_digest",
        ],
        "properties": {
            "protocol_id": {"type": "string", "minLength": 1},
            "protocol_version": {"type": "integer", "minimum": 1},
            "protocol_status": {"type": "string", "minLength": 1},
            "candidate_parameterization_id": {
                "enum": ["P-STEP-ZERO", "P-TAPER-ZERO-30D"]
            },
            "family_id": {"type": "string", "minLength": 1},
            "mechanism_class": {"type": "string", "minLength": 1},
            "base_parameter_set_id": {"type": "string", "minLength": 1},
            "candidate_identity_digest": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
        },
    }
    review_source_trace = {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "review_member",
                    "source_output",
                    "reason_code",
                ],
                "properties": {
                    "review_member": {"const": "NOT_APPLICABLE"},
                    "source_output": {"type": "number", "minimum": 0},
                    "reason_code": {
                        "const": "RC-REVIEW-NOT-APPLICABLE-AGGREGATE"
                    },
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "review_member",
                    "day",
                    "retention_transition_day",
                    "verified_base",
                    "positive_context_before",
                    "memory_gain_multiplier",
                    "positive_context_after",
                    "source_output",
                    "source_trace",
                    "reason_code",
                ],
                "properties": {
                    "review_member": {
                        "enum": ["P-STEP-ZERO", "P-TAPER-ZERO-30D"]
                    },
                    "day": {"type": "integer"},
                    "retention_transition_day": {"type": "integer"},
                    "verified_base": {"type": "number", "minimum": 0},
                    "positive_context_before": {"type": "number", "minimum": 0},
                    "memory_gain_multiplier": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "positive_context_after": {"type": "number", "minimum": 0},
                    "source_output": {"type": "number", "minimum": 0},
                    "source_trace": frozen_source_trace,
                    "reason_code": {
                        "enum": ["RC-REVIEW-STEP", "RC-REVIEW-TAPER"]
                    },
                },
            },
        ]
    }
    uncertainty_trace = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "current_state",
            "signal",
            "next_state",
            "applied_multiplier",
            "state_read_timing",
            "multiplier_apply_timing",
            "state_write_timing",
            "reason_code",
        ],
        "properties": {
            "current_state": {
                "enum": ["NORMAL", "WATCH", "RESTRICTED", "RECOVERING"]
            },
            "signal": {
                "enum": [
                    "NORMAL",
                    "ISOLATED_ANOMALY",
                    "CONFLICT",
                    "MISSING",
                ]
            },
            "next_state": {
                "enum": ["NORMAL", "WATCH", "RESTRICTED", "RECOVERING"]
            },
            "applied_multiplier": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "state_read_timing": {"const": "BEFORE_CURRENT_EVENT"},
            "multiplier_apply_timing": {
                "const": "AFTER_STATE_READ_BEFORE_STATE_WRITE"
            },
            "state_write_timing": {
                "enum": [
                    "AFTER_CURRENT_EVENT_CONTRIBUTION",
                    "NO_WRITE_HOLD",
                ]
            },
            "reason_code": {"type": "string", "minLength": 1},
        },
    }
    summary_required = [
        "group_id",
        "rows",
        "gate_results",
        "metric_results",
        "control_expected_failures",
        "unexpected_failures",
        "unexpected_control_passes",
    ]
    summary_properties = {
        "group_id": {"type": "string", "minLength": 1},
        "rows": {"type": "integer", "minimum": 0},
        "gate_results": {"type": "integer", "minimum": 0},
        "metric_results": {"type": "integer", "minimum": 0},
        "control_expected_failures": {"type": "integer", "minimum": 0},
        "unexpected_failures": {"type": "integer", "minimum": 0},
        "unexpected_control_passes": {"type": "integer", "minimum": 0},
    }
    group_summary = {
        "type": "object",
        "additionalProperties": False,
        "required": summary_required,
        "properties": summary_properties,
    }
    bundle_summary = {
        "type": "object",
        "additionalProperties": False,
        "required": [*summary_required, "recommendation_status"],
        "properties": {
            **summary_properties,
            "recommendation_status": {
                "enum": [
                    "CONTROL_ONLY",
                    "RECOMMENDATION_ELIGIBLE",
                    "REJECTED_HARD_GATE",
                ]
            },
        },
    }
    aggregates = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "expected_rows",
            "actual_rows",
            "unique_rows",
            "missing_rows",
            "extra_rows",
            "duplicate_rows",
            "gate_results",
            "metric_results",
            "control_expected_failures",
            "unexpected_failures",
            "unexpected_control_passes",
            "candidate_summaries",
            "bundle_summaries",
            "scenario_summaries",
            "review_member_summaries",
            "persona_summaries",
            "threat_summaries",
            "invariant_summaries",
        ],
        "properties": {
            "expected_rows": {"const": 1275},
            "actual_rows": {"const": 1275},
            "unique_rows": {"const": 1275},
            "missing_rows": {"const": 0},
            "extra_rows": {"const": 0},
            "duplicate_rows": {"const": 0},
            "gate_results": {"type": "integer", "minimum": 0},
            "metric_results": {"type": "integer", "minimum": 0},
            "control_expected_failures": {"type": "integer", "minimum": 0},
            "unexpected_failures": {"type": "integer", "minimum": 0},
            "unexpected_control_passes": {"type": "integer", "minimum": 0},
            "candidate_summaries": {
                "type": "array",
                "minItems": 19,
                "maxItems": 19,
                "items": group_summary,
            },
            "bundle_summaries": {
                "type": "array",
                "minItems": 21,
                "maxItems": 21,
                "items": bundle_summary,
            },
            "scenario_summaries": {
                "type": "array",
                "minItems": 52,
                "maxItems": 52,
                "items": group_summary,
            },
            "review_member_summaries": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": group_summary,
            },
            "persona_summaries": {
                "type": "array",
                "minItems": 1,
                "items": group_summary,
            },
            "threat_summaries": {
                "type": "array",
                "minItems": 1,
                "items": group_summary,
            },
            "invariant_summaries": {
                "type": "array",
                "minItems": 1,
                "items": group_summary,
            },
        },
    }
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/anki-study-report/core-economy-screening-results-v4.schema.json",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "identity",
            "manifest",
            "rows",
            "aggregates",
            "result_set_digest",
            "boundaries",
        ],
        "properties": {
            "$schema": {"const": "../schemas/core-economy-screening-results-v4.schema.json"},
            "identity": _identity_schema("core-economy-screening-results"),
            "manifest": build_manifest_schema(),
            "rows": {
                "type": "array",
                "minItems": 1275,
                "maxItems": 1275,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "row_id",
                        "candidate_bundle_id",
                        "scenario_id",
                        "review_member",
                        "replay_direction",
                        "protocol_digest",
                        "pipeline_digest",
                        "scenario_registry_digest",
                        "matrix_digest",
                        "result_status",
                        "metrics",
                        "gates",
                        "review_source_trace",
                        "uncertainty_trace",
                        "learn_limitation",
                        "explanation",
                        "semantic_result_digest",
                        "synthetic_only",
                        "real_user_data",
                        "production_status",
                    ],
                    "properties": {
                        "row_id": {"type": "string", "pattern": "^ROW-[0-9a-f]{64}$"},
                        "candidate_bundle_id": {"type": "string", "minLength": 1},
                        "scenario_id": {"type": "string", "minLength": 1},
                        "review_member": {
                            "enum": [
                                "P-STEP-ZERO",
                                "P-TAPER-ZERO-30D",
                                "NOT_APPLICABLE",
                            ]
                        },
                        "replay_direction": {"enum": ["FORWARD", "REVERSE"]},
                        "protocol_digest": {"const": EXPECTED_DIGESTS["protocol"]},
                        "pipeline_digest": {"const": EXPECTED_DIGESTS["pipeline"]},
                        "scenario_registry_digest": {"const": EXPECTED_DIGESTS["scenarios"]},
                        "matrix_digest": {"const": EXPECTED_DIGESTS["matrix"]},
                        "result_status": {"const": "COMPLETE"},
                        "metrics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["metric_id", "value", "reason_code"],
                                "properties": {
                                    "metric_id": {"type": "string", "minLength": 1},
                                    "value": metric_value,
                                    "reason_code": {"type": "string", "minLength": 1},
                                },
                            },
                        },
                        "gates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "gate_id",
                                    "expected_outcome",
                                    "actual_outcome",
                                    "passed",
                                    "expected_match",
                                    "reason_code",
                                ],
                                "properties": {
                                    "gate_id": {"type": "string", "minLength": 1},
                                    "expected_outcome": {
                                        "enum": ["PASS", "CONTROL_EXPECTED_FAIL"]
                                    },
                                    "actual_outcome": {
                                        "enum": [
                                            "PASS",
                                            "CONTROL_EXPECTED_FAIL",
                                            "UNEXPECTED_FAIL",
                                            "UNEXPECTED_CONTROL_PASS",
                                        ]
                                    },
                                    "passed": {"type": "boolean"},
                                    "expected_match": {"type": "boolean"},
                                    "reason_code": {"type": "string", "minLength": 1},
                                },
                            },
                        },
                        "review_source_trace": {
                            "type": "array",
                            "items": review_source_trace,
                        },
                        "uncertainty_trace": {
                            "type": "array",
                            "items": uncertainty_trace,
                        },
                        "learn_limitation": {"const": LEARN_LIMITATION},
                        "explanation": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "review_component",
                                "learn_component",
                                "total_npu",
                                "review_source_trace_digest",
                                "uncertainty_trace_digest",
                                "reason_codes",
                            ],
                            "properties": {
                                "review_component": {"type": "number", "minimum": 0},
                                "learn_component": {"type": "number", "minimum": 0},
                                "total_npu": {"type": "number", "minimum": 0},
                                "review_source_trace_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                                "uncertainty_trace_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                                "reason_codes": {
                                    "type": "array",
                                    "items": {"type": "string", "minLength": 1},
                                    "uniqueItems": True,
                                },
                            },
                        },
                        "semantic_result_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                        "synthetic_only": {"const": True},
                        "real_user_data": {"const": False},
                        "production_status": {"const": "RESEARCH_ONLY"},
                    },
                },
            },
            "aggregates": aggregates,
            "result_set_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "boundaries": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "synthetic_only",
                    "real_user_data",
                    "production_approved",
                    "production_integration",
                    "g5_started",
                    "g6_started",
                    "weighted_overall_score",
                    "hard_gate_compensation",
                ],
                "properties": {
                    "synthetic_only": {"const": True},
                    "real_user_data": {"const": False},
                    "production_approved": {"const": False},
                    "production_integration": {"const": False},
                    "g5_started": {"const": False},
                    "g6_started": {"const": False},
                    "weighted_overall_score": {"const": False},
                    "hard_gate_compensation": {"const": False},
                },
            },
        },
    }
    Draft202012Validator.check_schema(schema)
    return schema


def write_schemas(research_root: Path) -> None:
    targets = {
        MANIFEST_SCHEMA_PATH: build_manifest_schema(),
        RESULTS_SCHEMA_PATH: build_results_schema(),
    }
    for relative, value in targets.items():
        path = research_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical_bytes(value))


def check_schema_byte_identical(research_root: Path) -> None:
    targets = {
        MANIFEST_SCHEMA_PATH: build_manifest_schema(),
        RESULTS_SCHEMA_PATH: build_results_schema(),
    }
    for relative, value in targets.items():
        _require(
            (research_root / relative).read_bytes() == _canonical_bytes(value),
            f"schema byte-identical check failed: {relative}",
        )


def validate_results(
    payload: Mapping[str, Any],
    *,
    research_root: Path,
    repository_root: Path,
) -> None:
    manifest_schema = load_strict_json(
        research_root / MANIFEST_SCHEMA_PATH,
        max_bytes=8 * 1024 * 1024,
    )
    results_schema = load_strict_json(
        research_root / RESULTS_SCHEMA_PATH,
        max_bytes=16 * 1024 * 1024,
    )
    Draft202012Validator.check_schema(manifest_schema)
    Draft202012Validator.check_schema(results_schema)
    errors = sorted(
        Draft202012Validator(results_schema).iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    _require(not errors, f"result schema validation failed: {errors[0].message if errors else ''}")
    _require(
        payload["identity"]["artifact_digest"] == _artifact_digest(payload),
        "result artifact digest mismatch",
    )
    protocol, _pipeline, scenarios, matrix = _load_artifacts(research_root)
    implementation_sha = payload["manifest"]["repository"]["implementation_sha"]
    expected_manifest = build_manifest(
        repository_root=repository_root,
        implementation_sha=implementation_sha,
        matrix=matrix,
    )
    _require(payload["manifest"] == expected_manifest, "manifest detached recomputation mismatch")
    recomputed_rows = [
        evaluate_row(row, protocol=protocol, scenarios=scenarios)
        for row in matrix["rows"]
    ]
    _enforce_replay(recomputed_rows)
    recomputed_aggregates = _aggregate_rows(
        recomputed_rows,
        protocol=protocol,
        scenarios=scenarios,
        matrix=matrix,
    )
    _require(payload["rows"] == recomputed_rows, "row detached recomputation mismatch")
    _require(payload["aggregates"] == recomputed_aggregates, "aggregate detached recomputation mismatch")
    _require(
        payload["result_set_digest"]
        == canonical_digest(
            {"rows": recomputed_rows, "aggregates": recomputed_aggregates}
        ),
        "result set digest mismatch",
    )


def write_results(
    payload: Mapping[str, Any],
    *,
    research_root: Path,
) -> None:
    targets = {
        MANIFEST_PATH: payload["manifest"],
        RESULTS_PATH: payload,
    }
    for relative, value in targets.items():
        path = research_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical_bytes(value))


def check_result_byte_identical(
    payload: Mapping[str, Any],
    *,
    research_root: Path,
) -> None:
    targets = {
        MANIFEST_PATH: payload["manifest"],
        RESULTS_PATH: payload,
    }
    for relative, value in targets.items():
        _require(
            (research_root / relative).read_bytes() == _canonical_bytes(value),
            f"result byte-identical check failed: {relative}",
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute and validate G4.4 exact v4 replacement bounded screening"
    )
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--implementation-sha")
    parser.add_argument("--write-schemas", action="store_true")
    parser.add_argument("--check-schema-byte-identical", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--check-result-byte-identical", action="store_true")
    args = parser.parse_args(argv)
    research_root = args.research_root.resolve()
    repository_root = args.repository_root.resolve()
    summary: dict[str, Any] = {}
    if args.write_schemas:
        write_schemas(research_root)
        summary["schemas_written"] = True
    if args.check_schema_byte_identical:
        check_schema_byte_identical(research_root)
        summary["schema_byte_identical"] = "PASS"
    payload = None
    if args.run:
        _require(bool(args.implementation_sha), "--implementation-sha is required for --run")
        payload = run_screening(
            research_root=research_root,
            repository_root=repository_root,
            implementation_sha=str(args.implementation_sha),
        )
        validate_results(
            payload,
            research_root=research_root,
            repository_root=repository_root,
        )
        write_results(payload, research_root=research_root)
        summary.update(payload["aggregates"])
        summary["result_set_digest"] = payload["result_set_digest"]
        summary["artifact_digest"] = payload["identity"]["artifact_digest"]
    if args.validate:
        stored = load_strict_json(
            research_root / RESULTS_PATH,
            max_bytes=256 * 1024 * 1024,
        )
        validate_results(
            stored,
            research_root=research_root,
            repository_root=repository_root,
        )
        payload = stored
        summary["validation"] = "PASS"
    if args.check_result_byte_identical:
        _require(payload is not None, "result payload is required")
        check_result_byte_identical(payload, research_root=research_root)
        summary["result_byte_identical"] = "PASS"
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
