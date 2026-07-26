from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import random
import statistics
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
from .longitudinal_models import LongitudinalConfig, LongitudinalMode
from .longitudinal_runner import run_policy
from .matched_analysis import POLICY_PAIRS
from .models import (
    CompletionStatus,
    ConfidenceLevel,
    DueRelation,
    MemoryContext,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    WorkloadSnapshot,
)
from .parameters import CURRENT_PARAMETERS
from .population import (
    EXPECTED_PERSONA_IDS,
    derive_persona_seed,
    generate_day,
    load_personas,
)
from .review_candidate_mechanisms import (
    FROZEN_REVIEW_CANDIDATES,
    REFERENCE_PARAMETERIZATION_ID,
    RewardExecutionContext,
)
from .strict_json import load_strict_json
from .validation import close
from .workspace import ResearchWorkspace, resolve_research_workspace


PROTOCOL_RELATIVE_PATH = Path("contracts/review-xp-confirmatory-protocol-v1.json")
SCHEMA_RELATIVE_PATH = Path("schemas/review-xp-confirmatory-protocol-v1.schema.json")
CONFIG_RELATIVE_PATH = Path("configs/review-longitudinal-v0.1.json")
EXPECTED_TOTAL_UNITS = 840
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024
ABS_TOLERANCE = 1e-9

EXPECTED_VARIANTS = (
    REFERENCE_PARAMETERIZATION_ID,
    "P-STEP-ZERO",
    "P-TAPER-ZERO-30D",
)
REJECTED_VARIANTS = {
    "P-STEP-NEUTRAL-RATIO",
    "P-TAPER-NEUTRAL-RATIO-30D",
}
EXPECTED_POLICY_PAIRS = (
    "retention-high-cycle",
    "retention-low-cycle",
    "intentional-backlog",
    "honest-backlog-return",
)
EXPECTED_HORIZONS = (90, 365)
EXPECTED_REPLICAS = (0, 1)
EXPECTED_SEEDS = (5978107021558220631, 5509807251554775963)
EXPECTED_REPLAYS = ("PRIMARY", "SAME_INPUT_REPLAY")
EXPECTED_MODEL_CONDITIONS: Mapping[str, Mapping[int, int]] = {
    "MODEL-NATIVE-COHORT": {90: 24, 365: 20},
    "MODEL-COHORT-20": {90: 20, 365: 20},
    "MODEL-COHORT-24": {90: 24, 365: 24},
}
EXPECTED_PROBES = (
    "INV-ORDINARY-UNIT",
    "INV-AGAIN-CREDIT",
    "INV-BUTTON-NEUTRAL",
    "INV-SESSION-INVARIANT",
    "INV-NO-RESPONSE-TIME",
    "INV-RESPONSE-VALIDITY",
    "ABUSE-DUPLICATE-REPLAY",
    "ABUSE-RELEARNING-LOOP",
    "ABUSE-PREVIEW-FARM",
    "ABUSE-FORCED-DUE",
    "ABUSE-MICRO-SCOPE-COMPLETION",
    "INV-RESEARCH-ONLY",
)
EXPECTED_GATE_IDS = (
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
    "GATE-MODEL-CONDITION-SENSITIVITY",
    "GATE-PERSONA-SAFETY",
    "GATE-ABUSE-PROBES",
    "GATE-EVIDENCE-COMPLETE",
    "GATE-RESEARCH-ONLY",
)
ALLOWED_OUTCOMES = {
    "CONFIRMATORY_ELIGIBLE",
    "CONFIRMATORY_NOT_ELIGIBLE",
    "CONFIRMATORY_INCONCLUSIVE",
}


@dataclass(frozen=True, slots=True, order=True)
class ConfirmatoryExecutionUnit:
    component: str
    variant_id: str
    replay_id: str
    policy_pair: str | None = None
    horizon: int | None = None
    replica: int | None = None
    seed: int | None = None
    model_condition: str | None = None
    persona_id: str | None = None
    probe_id: str | None = None

    def payload(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "variant_id": self.variant_id,
            "parameterization": (
                None
                if self.variant_id == REFERENCE_PARAMETERIZATION_ID
                else self.variant_id
            ),
            "replay_id": self.replay_id,
            "policy_pair": self.policy_pair,
            "horizon": self.horizon,
            "replica": self.replica,
            "seed": self.seed,
            "model_condition": self.model_condition,
            "persona_id": self.persona_id,
            "probe_id": self.probe_id,
        }

    @property
    def unit_id(self) -> str:
        return canonical_digest(self.payload())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_errors(
    schema: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> list[str]:
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


def load_and_validate_confirmatory_protocol(
    workspace: ResearchWorkspace | Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = resolve_research_workspace(workspace)
    protocol_path = resolved.path(PROTOCOL_RELATIVE_PATH)
    schema_path = resolved.path(SCHEMA_RELATIVE_PATH)
    protocol = load_strict_json(protocol_path)
    schema = load_strict_json(schema_path)
    if not isinstance(protocol, dict) or not isinstance(schema, dict):
        raise ValueError("confirmatory protocol and schema must be JSON objects")
    Draft202012Validator.check_schema(schema)
    errors = _schema_errors(schema, protocol)
    if errors:
        raise ValueError(
            "confirmatory protocol schema validation failed: " + "; ".join(errors)
        )
    if tuple(protocol["eligible_variants"]) != EXPECTED_VARIANTS:
        raise ValueError("confirmatory eligible variant registry drifted")
    if set(protocol["rejected_variants"]) != REJECTED_VARIANTS:
        raise ValueError("confirmatory rejected variant registry drifted")
    if tuple(protocol["fresh_seeds"]) != EXPECTED_SEEDS:
        raise ValueError("confirmatory seed registry drifted")
    if tuple(protocol["replay_ids"]) != EXPECTED_REPLAYS:
        raise ValueError("confirmatory replay registry drifted")
    if tuple(protocol["required_gates"]) != EXPECTED_GATE_IDS:
        raise ValueError("confirmatory gate registry drifted")
    if any(protocol["boundaries"].values()):
        raise ValueError("confirmatory boundary must prohibit ranking and production")
    return protocol, {
        "protocol_path": PROTOCOL_RELATIVE_PATH.as_posix(),
        "protocol_sha256": _sha256(protocol_path),
        "protocol_digest": canonical_digest(protocol),
        "schema_path": SCHEMA_RELATIVE_PATH.as_posix(),
        "schema_sha256": _sha256(schema_path),
        "schema_digest": canonical_digest(schema),
        "schema_draft": schema.get("$schema"),
    }


def _core_units() -> tuple[ConfirmatoryExecutionUnit, ...]:
    return tuple(
        ConfirmatoryExecutionUnit(
            "CORE_LONGITUDINAL",
            variant,
            replay,
            policy_pair=pair,
            horizon=horizon,
            replica=replica,
            seed=seed,
            model_condition=condition,
        )
        for variant, pair, horizon, replica, seed, replay, condition in product(
            EXPECTED_VARIANTS,
            EXPECTED_POLICY_PAIRS,
            EXPECTED_HORIZONS,
            EXPECTED_REPLICAS,
            EXPECTED_SEEDS,
            EXPECTED_REPLAYS,
            tuple(EXPECTED_MODEL_CONDITIONS),
        )
    )


def _persona_units() -> tuple[ConfirmatoryExecutionUnit, ...]:
    return tuple(
        ConfirmatoryExecutionUnit(
            "PERSONA_SAFETY",
            variant,
            replay,
            seed=seed,
            persona_id=persona_id,
        )
        for variant, persona_id, seed, replay in product(
            EXPECTED_VARIANTS,
            EXPECTED_PERSONA_IDS,
            EXPECTED_SEEDS,
            EXPECTED_REPLAYS,
        )
    )


def _probe_units() -> tuple[ConfirmatoryExecutionUnit, ...]:
    return tuple(
        ConfirmatoryExecutionUnit(
            "INVARIANT_ABUSE_PROBE",
            variant,
            replay,
            probe_id=probe_id,
        )
        for variant, probe_id, replay in product(
            EXPECTED_VARIANTS,
            EXPECTED_PROBES,
            EXPECTED_REPLAYS,
        )
    )


def build_confirmatory_manifest(
    workspace: ResearchWorkspace | Path | str | None = None,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    protocol, identities = load_and_validate_confirmatory_protocol(resolved)
    config = load_longitudinal_config(
        resolved.path(CONFIG_RELATIVE_PATH),
        workspace=resolved,
    )
    mode90 = config.mode("calibration-90")
    mode365 = config.mode("calibration-365")
    if (
        mode90.horizon_days,
        mode90.cohort_size,
        mode90.replicas,
    ) != (90, 24, 2):
        raise ValueError("calibration-90 mode drifted")
    if (
        mode365.horizon_days,
        mode365.cohort_size,
        mode365.replicas,
    ) != (365, 20, 2):
        raise ValueError("calibration-365 mode drifted")
    pair_ids = {item.pair_id for item in POLICY_PAIRS}
    if not set(EXPECTED_POLICY_PAIRS) <= pair_ids:
        raise ValueError("required confirmatory policy pair missing")
    registered = {item.parameterization_id for item in FROZEN_REVIEW_CANDIDATES}
    if not set(EXPECTED_VARIANTS[1:]) <= registered:
        raise ValueError("confirmatory survivor is absent from frozen registry")
    if set(EXPECTED_VARIANTS) & REJECTED_VARIANTS:
        raise ValueError("rejected parameterization leaked into confirmatory matrix")
    personas = load_personas(resolved.personas, workspace=resolved)
    if tuple(item.persona_id for item in personas) != EXPECTED_PERSONA_IDS:
        raise ValueError("confirmatory persona catalog drifted")

    units = (*_core_units(), *_persona_units(), *_probe_units())
    unit_payloads = [{"unit_id": unit.unit_id, **unit.payload()} for unit in units]
    ids = [item["unit_id"] for item in unit_payloads]
    component_counts = {
        name: sum(item["component"] == name for item in unit_payloads)
        for name in (
            "CORE_LONGITUDINAL",
            "PERSONA_SAFETY",
            "INVARIANT_ABUSE_PROBE",
        )
    }
    expected_counts = {
        "CORE_LONGITUDINAL": protocol["expected_accounting"]["core_units"],
        "PERSONA_SAFETY": protocol["expected_accounting"]["persona_safety_units"],
        "INVARIANT_ABUSE_PROBE": protocol["expected_accounting"]["probe_units"],
    }
    if component_counts != expected_counts:
        raise ValueError(
            f"confirmatory component accounting drifted: {component_counts}"
        )
    if len(unit_payloads) != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory unit count drifted")
    if len(set(ids)) != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory unit IDs are not unique")

    persona_set_digest = canonical_digest(
        [{"persona_id": item.persona_id, "digest": item.digest} for item in personas]
    )
    candidate_digests = {
        item.parameterization_id: item.digest
        for item in FROZEN_REVIEW_CANDIDATES
        if item.parameterization_id in EXPECTED_VARIANTS
    }
    manifest = {
        "manifest_version": "review-xp-confirmatory-manifest-v1",
        **identities,
        "config_path": CONFIG_RELATIVE_PATH.as_posix(),
        "config_digest": config.digest,
        "persona_set_digest": persona_set_digest,
        "candidate_identity_digests": candidate_digests,
        "axes": {
            "variants": list(EXPECTED_VARIANTS),
            "policy_pairs": list(EXPECTED_POLICY_PAIRS),
            "horizons": list(EXPECTED_HORIZONS),
            "replicas": list(EXPECTED_REPLICAS),
            "seeds": list(EXPECTED_SEEDS),
            "replay_ids": list(EXPECTED_REPLAYS),
            "model_conditions": {
                key: {str(h): value[h] for h in EXPECTED_HORIZONS}
                for key, value in EXPECTED_MODEL_CONDITIONS.items()
            },
            "persona_ids": list(EXPECTED_PERSONA_IDS),
            "probe_ids": list(EXPECTED_PROBES),
        },
        "component_counts": component_counts,
        "expected_units": EXPECTED_TOTAL_UNITS,
        "actual_units": len(unit_payloads),
        "actual_unique_units": len(set(ids)),
        "missing_units": 0,
        "extra_units": 0,
        "duplicate_units": 0,
        "units": unit_payloads,
    }
    manifest["manifest_digest"] = canonical_digest(manifest)
    return manifest


def validate_confirmatory_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("expected_units") != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory manifest expected count drifted")
    if manifest.get("actual_units") != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory manifest actual count drifted")
    if manifest.get("actual_unique_units") != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory manifest unique count drifted")
    if any(
        manifest.get(name) != 0
        for name in ("missing_units", "extra_units", "duplicate_units")
    ):
        raise ValueError("confirmatory manifest accounting is incomplete")
    units = manifest.get("units")
    if not isinstance(units, list) or len(units) != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory manifest units are invalid")
    ids = [item.get("unit_id") for item in units if isinstance(item, dict)]
    if len(ids) != EXPECTED_TOTAL_UNITS or len(set(ids)) != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory manifest unit IDs are invalid")
    without_digest = dict(manifest)
    digest = without_digest.pop("manifest_digest", None)
    if digest != canonical_digest(without_digest):
        raise ValueError("confirmatory manifest digest mismatch")


def _policy_pair(pair_id: str):
    for pair in POLICY_PAIRS:
        if pair.pair_id == pair_id:
            return pair
    raise ValueError(f"missing matched policy pair definition: {pair_id}")


def _candidate_id(variant_id: str) -> str | None:
    return None if variant_id == REFERENCE_PARAMETERIZATION_ID else variant_id


def _condition_config(
    config: LongitudinalConfig,
    *,
    horizon: int,
    cohort_size: int,
) -> tuple[LongitudinalConfig, str]:
    mode_id = f"confirmatory-{horizon}-{cohort_size}"
    mode = LongitudinalMode(mode_id, horizon, cohort_size, 1)
    payload = {
        "source_config_digest": config.digest,
        "mode_id": mode_id,
        "horizon_days": horizon,
        "cohort_size": cohort_size,
        "replicas": 1,
    }
    return (
        replace(
            config,
            version=f"{config.version}+confirmatory-v1",
            config_id=f"{config.config_id}+confirmatory-v1",
            modes=(mode,),
            digest=canonical_digest(payload),
        ),
        mode_id,
    )


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


def _comparison(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> dict[str, Any]:
    if left["initial_cohort_digest"] != right["initial_cohort_digest"]:
        raise ValueError("confirmatory unit initial cohort mismatch")
    if left["latent_stream_id"] != right["latent_stream_id"]:
        raise ValueError("confirmatory unit latent stream mismatch")
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


def run_core_execution_unit(
    unit: ConfirmatoryExecutionUnit,
    *,
    workspace: ResearchWorkspace | Path | str | None = None,
) -> dict[str, Any]:
    if unit.component != "CORE_LONGITUDINAL":
        raise ValueError("core runner received a non-core unit")
    if None in (
        unit.policy_pair,
        unit.horizon,
        unit.replica,
        unit.seed,
        unit.model_condition,
    ):
        raise ValueError("core unit is incomplete")
    resolved = resolve_research_workspace(workspace)
    config = load_longitudinal_config(
        resolved.path(CONFIG_RELATIVE_PATH),
        workspace=resolved,
    )
    condition = EXPECTED_MODEL_CONDITIONS[unit.model_condition]
    cohort_size = condition[unit.horizon]
    condition_config, mode_id = _condition_config(
        config,
        horizon=unit.horizon,
        cohort_size=cohort_size,
    )
    pair = _policy_pair(unit.policy_pair)
    by_policy = {item.policy_id: item for item in condition_config.policies}
    kwargs = {
        "parameter_set_id": REFERENCE_PARAMETERIZATION_ID,
        "master_seed": unit.seed,
        "mode_id": mode_id,
        "replica": unit.replica,
        "candidate_parameterization_id": _candidate_id(unit.variant_id),
    }
    left = run_policy(
        condition_config,
        policy=by_policy[pair.left_policy_id],
        **kwargs,
    )
    right = run_policy(
        condition_config,
        policy=by_policy[pair.right_policy_id],
        **kwargs,
    )
    result_payload = {
        "component": unit.component,
        "variant_id": unit.variant_id,
        "policy_pair": unit.policy_pair,
        "horizon": unit.horizon,
        "replica": unit.replica,
        "seed": unit.seed,
        "model_condition": unit.model_condition,
        "cohort_size": cohort_size,
        "pair_definition": {
            "left_policy_id": pair.left_policy_id,
            "right_policy_id": pair.right_policy_id,
            "changed_factor": pair.changed_factor,
            "controlled_factors": list(pair.controlled_factors),
        },
        "left": _compact_policy_result(left),
        "right": _compact_policy_result(right),
        "comparison": _comparison(left, right),
    }
    return {
        "unit_id": unit.unit_id,
        **unit.payload(),
        "result_payload": result_payload,
        "result_digest": canonical_digest(result_payload),
    }


def _persona_result(
    unit: ConfirmatoryExecutionUnit,
    *,
    workspace: ResearchWorkspace,
) -> dict[str, Any]:
    if unit.component != "PERSONA_SAFETY":
        raise ValueError("persona runner received a non-persona unit")
    if unit.persona_id is None or unit.seed is None:
        raise ValueError("persona unit is incomplete")
    personas = load_personas(workspace.personas, workspace=workspace)
    persona = next(item for item in personas if item.persona_id == unit.persona_id)
    child_seed = derive_persona_seed(unit.seed, persona.persona_id, 0)
    rng = random.Random(child_seed)
    totals: list[float] = []
    baseline_awarded = 0.0
    baseline_expected = 0.0
    suppression_events = 0
    failures: set[str] = set()
    history = hashlib.sha256()
    parameterization = _candidate_id(unit.variant_id)
    for day_index in range(60, 90):
        day, honest_outcomes = generate_day(persona, rng, 0, day_index)
        result = aggregate_day(
            day,
            CURRENT_PARAMETERS,
            candidate_parameterization_id=parameterization,
            execution_context=RewardExecutionContext(
                day=day_index,
                retention_transition_days=(30, 60),
            ),
        )
        expected = sum(
            CURRENT_PARAMETERS.attempt_credit
            + (CURRENT_PARAMETERS.outcome_credit if outcome.passed else 0.0)
            for outcome in honest_outcomes
        )
        totals.append(result.total)
        baseline_awarded += result.core_baseline
        baseline_expected += expected
        suppression_events += int(result.core_baseline + ABS_TOLERANCE < expected)
        if result.total < -ABS_TOLERANCE:
            failures.add("NEGATIVE_TOTAL")
        if result.volume_credit > CURRENT_PARAMETERS.volume_cap + ABS_TOLERANCE:
            failures.add("VOLUME_CAP")
        if result.completion_credit > CURRENT_PARAMETERS.completion_cap + ABS_TOLERANCE:
            failures.add("COMPLETION_CAP")
        if not close(
            result.total,
            result.core_baseline
            + result.core_context
            + result.capped_support
            + result.capped_supplemental
            + result.volume_credit
            + result.completion_credit,
        ):
            failures.add("BREAKDOWN_SUM")
        history.update(
            (
                f"{day_index}:{len(honest_outcomes)}:"
                f"{result.total:.17g}:{result.core_baseline:.17g}\n"
            ).encode()
        )
    preservation = (
        1.0
        if baseline_expected == 0.0
        else baseline_awarded / baseline_expected
    )
    if not close(preservation, 1.0):
        failures.add("BASELINE_SUPPRESSION")
    payload = {
        "component": unit.component,
        "variant_id": unit.variant_id,
        "persona_id": unit.persona_id,
        "seed": unit.seed,
        "derived_seed": child_seed,
        "window_start_day": 60,
        "window_end_day": 89,
        "day_count": len(totals),
        "mean_total_review_units": statistics.fmean(totals),
        "min_total_review_units": min(totals),
        "max_total_review_units": max(totals),
        "baseline_preservation_ratio": preservation,
        "suppression_events": suppression_events,
        "gate_failures": sorted(failures),
        "history_digest": history.hexdigest(),
    }
    return {
        "unit_id": unit.unit_id,
        **unit.payload(),
        "result_payload": payload,
        "result_digest": canonical_digest(payload),
    }


def _probe_inputs(
    variant_id: str,
) -> tuple[str | None, RewardExecutionContext, ReviewEpisodeInput]:
    parameterization = _candidate_id(variant_id)
    context = RewardExecutionContext(day=60, retention_transition_days=(30, 60))
    ordinary = ReviewEpisodeInput(
        "ordinary",
        "ordinary-card",
        "2026-03-02",
        Outcome.GOOD,
    )
    return parameterization, context, ordinary


def _probe_value(variant_id: str, probe_id: str) -> tuple[bool, Any]:
    parameterization, context, ordinary = _probe_inputs(variant_id)
    ordinary_result = evaluate_episode(
        ordinary,
        CURRENT_PARAMETERS,
        candidate_parameterization_id=parameterization,
        execution_context=context,
    )
    if probe_id == "INV-ORDINARY-UNIT":
        observed = ordinary_result.total
        return math.isclose(observed, 1.0, abs_tol=ABS_TOLERANCE), observed
    if probe_id == "INV-AGAIN-CREDIT":
        observed = evaluate_episode(
            replace(ordinary, source_event_key="again", outcome=Outcome.AGAIN),
            CURRENT_PARAMETERS,
            candidate_parameterization_id=parameterization,
            execution_context=context,
        ).total
        return math.isclose(observed, 0.25, abs_tol=ABS_TOLERANCE), observed
    if probe_id == "INV-BUTTON-NEUTRAL":
        values = [
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
            for outcome in (Outcome.HARD, Outcome.GOOD, Outcome.EASY)
        ]
        passed = all(
            math.isclose(value, values[0], abs_tol=ABS_TOLERANCE)
            for value in values
        )
        return passed, values
    if probe_id == "INV-SESSION-INVARIANT":
        workload = WorkloadSnapshot(
            status=CompletionStatus.PARTIAL,
            natural_due_at_start=1,
            due_visible_under_limits=1,
            due_hidden_by_limits=0,
        )
        one = ReviewDayInput(
            ordinary.anki_day,
            episodes=(ordinary,),
            workload=workload,
            session_ids=("session-a",),
        )
        split = replace(one, session_ids=("session-a", "session-b"))
        left = aggregate_day(
            one,
            CURRENT_PARAMETERS,
            candidate_parameterization_id=parameterization,
            execution_context=context,
        )
        right = aggregate_day(
            split,
            CURRENT_PARAMETERS,
            candidate_parameterization_id=parameterization,
            execution_context=context,
        )
        return left == right, {"single": left.total, "split": right.total}
    if probe_id == "INV-NO-RESPONSE-TIME":
        observed = "response_time" not in {
            item.name for item in fields(ReviewEpisodeInput)
        }
        return observed, observed
    if probe_id == "INV-RESPONSE-VALIDITY":
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
        passed = (
            math.isclose(half.baseline, full.baseline, abs_tol=ABS_TOLERANCE)
            and math.isclose(
                half.context,
                full.context * 0.5,
                abs_tol=ABS_TOLERANCE,
            )
        )
        return passed, {
            "full_baseline": full.baseline,
            "half_baseline": half.baseline,
            "full_context": full.context,
            "half_context": half.context,
        }

    def day_total(
        episodes: tuple[ReviewEpisodeInput, ...],
        *,
        status: CompletionStatus = CompletionStatus.PARTIAL,
    ) -> float:
        return aggregate_day(
            ReviewDayInput(
                ordinary.anki_day,
                episodes=episodes,
                workload=WorkloadSnapshot(
                    status=status,
                    natural_due_at_start=len(episodes),
                    due_visible_under_limits=len(episodes),
                ),
            ),
            CURRENT_PARAMETERS,
            candidate_parameterization_id=parameterization,
            execution_context=context,
        ).total

    if probe_id == "ABUSE-DUPLICATE-REPLAY":
        exploit = day_total((ordinary, ordinary))
        control = day_total((ordinary,))
        return math.isclose(exploit, control, abs_tol=ABS_TOLERANCE), {
            "exploit": exploit,
            "control": control,
        }
    if probe_id == "ABUSE-RELEARNING-LOOP":
        attempts = tuple(
            replace(
                ordinary,
                source_event_key=f"again-{index}",
                card_lineage="same-card",
                outcome=Outcome.AGAIN,
            )
            for index in range(3)
        )
        controls = tuple(
            replace(
                ordinary,
                source_event_key=f"control-{index}",
                card_lineage=f"control-card-{index}",
                outcome=Outcome.AGAIN,
            )
            for index in range(3)
        )
        exploit = day_total(attempts)
        control = day_total(controls)
        return exploit <= control + ABS_TOLERANCE, {
            "exploit": exploit,
            "control": control,
        }
    if probe_id == "ABUSE-PREVIEW-FARM":
        preview = replace(
            ordinary,
            source_event_key="preview",
            preview_without_rescheduling=True,
        )
        observed = day_total((preview,))
        return math.isclose(observed, 0.0, abs_tol=ABS_TOLERANCE), observed
    if probe_id == "ABUSE-FORCED-DUE":
        memory = MemoryContext(
            retrievability_actual=0.5,
            retrievability_natural_due=0.5,
            stability_before=1.0,
            stability_good_counterfactual=2.0,
            confidence=ConfidenceLevel.HIGH,
        )
        on_time = replace(ordinary, source_event_key="on-time", memory=memory)
        forced = replace(
            ordinary,
            source_event_key="forced",
            memory=memory,
            due_relation=DueRelation.FORCED_DUE,
        )
        control = day_total((on_time,))
        exploit = day_total((forced,))
        return exploit <= control + ABS_TOLERANCE, {
            "exploit": exploit,
            "control": control,
        }
    if probe_id == "ABUSE-MICRO-SCOPE-COMPLETION":
        episodes = tuple(
            replace(
                ordinary,
                source_event_key=f"review-{index}",
                card_lineage=f"card-{index}",
            )
            for index in range(10)
        )
        collection = day_total(
            episodes,
            status=CompletionStatus.COLLECTION_CLEARED,
        )
        scope = day_total(
            episodes,
            status=CompletionStatus.SCOPE_CLEARED,
        )
        return scope <= collection + ABS_TOLERANCE, {
            "scope": scope,
            "collection": collection,
        }
    if probe_id == "INV-RESEARCH-ONLY":
        observed = (
            variant_id == REFERENCE_PARAMETERIZATION_ID
            or any(
                item.parameterization_id == variant_id
                for item in FROZEN_REVIEW_CANDIDATES
            )
        )
        return observed, observed
    raise ValueError(f"unknown confirmatory probe: {probe_id}")


def _probe_result(unit: ConfirmatoryExecutionUnit) -> dict[str, Any]:
    if unit.component != "INVARIANT_ABUSE_PROBE" or unit.probe_id is None:
        raise ValueError("probe runner received an invalid unit")
    passed, observed = _probe_value(unit.variant_id, unit.probe_id)
    payload = {
        "component": unit.component,
        "variant_id": unit.variant_id,
        "probe_id": unit.probe_id,
        "passed": passed,
        "observed": observed,
    }
    return {
        "unit_id": unit.unit_id,
        **unit.payload(),
        "result_payload": payload,
        "result_digest": canonical_digest(payload),
    }


def run_confirmatory_execution_unit(
    unit: ConfirmatoryExecutionUnit,
    *,
    workspace: ResearchWorkspace | Path | str | None = None,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    if unit.component == "CORE_LONGITUDINAL":
        return run_core_execution_unit(unit, workspace=resolved)
    if unit.component == "PERSONA_SAFETY":
        return _persona_result(unit, workspace=resolved)
    if unit.component == "INVARIANT_ABUSE_PROBE":
        return _probe_result(unit)
    raise ValueError(f"unknown confirmatory component: {unit.component}")


def _gate(predicate_id: str, passed: bool, observed: Any) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id,
        "status": "PASS" if passed else "FAIL",
        "observed": observed,
    }


def _semantic_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        item["component"],
        item["variant_id"],
        item.get("policy_pair"),
        item.get("horizon"),
        item.get("replica"),
        item.get("seed"),
        item.get("model_condition"),
        item.get("persona_id"),
        item.get("probe_id"),
    )


def _replay_status(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, list[str]]:
    by_key: dict[tuple[Any, ...], dict[str, Mapping[str, Any]]] = {}
    for item in rows:
        by_key.setdefault(_semantic_key(item), {})[item["replay_id"]] = item
    failures = []
    for key, replay_map in by_key.items():
        if set(replay_map) != set(EXPECTED_REPLAYS):
            failures.append(f"missing replay for {key}")
            continue
        if (
            replay_map["PRIMARY"]["result_digest"]
            != replay_map["SAME_INPUT_REPLAY"]["result_digest"]
        ):
            failures.append(f"replay digest mismatch for {key}")
    return not failures, failures


def evaluate_confirmatory_gates(
    units: Sequence[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    validate_confirmatory_manifest(manifest)
    if len(units) != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory evidence unit count drifted")
    ids = [item.get("unit_id") for item in units]
    if len(set(ids)) != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory evidence has duplicate unit IDs")
    manifest_by_id = {
        item["unit_id"]: item
        for item in manifest["units"]
    }
    if set(ids) != set(manifest_by_id):
        raise ValueError("confirmatory evidence unit IDs do not match manifest")
    identity_fields = (
        "component",
        "variant_id",
        "parameterization",
        "replay_id",
        "policy_pair",
        "horizon",
        "replica",
        "seed",
        "model_condition",
        "persona_id",
        "probe_id",
    )
    for item in units:
        expected = manifest_by_id[item["unit_id"]]
        if any(item.get(field) != expected.get(field) for field in identity_fields):
            raise ValueError(
                f"confirmatory evidence identity drifted: {item['unit_id']}"
            )
        if item.get("result_digest") != canonical_digest(
            item.get("result_payload")
        ):
            raise ValueError(
                f"confirmatory unit result digest mismatch: {item['unit_id']}"
            )
    candidates = EXPECTED_VARIANTS[1:]
    outcomes = []
    reference_primary = {
        _semantic_key(item): item
        for item in units
        if item["variant_id"] == REFERENCE_PARAMETERIZATION_ID
        and item["replay_id"] == "PRIMARY"
    }
    reference_rows = [
        item
        for item in units
        if item["variant_id"] == REFERENCE_PARAMETERIZATION_ID
    ]

    for candidate_id in candidates:
        rows = [item for item in units if item["variant_id"] == candidate_id]
        replay_ok, replay_failures = _replay_status(
            [*reference_rows, *rows]
        )
        core_primary = [
            item
            for item in rows
            if item["component"] == "CORE_LONGITUDINAL"
            and item["replay_id"] == "PRIMARY"
        ]
        persona_primary = [
            item
            for item in rows
            if item["component"] == "PERSONA_SAFETY"
            and item["replay_id"] == "PRIMARY"
        ]
        probe_primary = [
            item
            for item in rows
            if item["component"] == "INVARIANT_ABUSE_PROBE"
            and item["replay_id"] == "PRIMARY"
        ]

        endpoint_values = [
            item["result_payload"]["comparison"]["unexplained_advantage"]
            for item in core_primary
            if item["horizon"] == 365
            and item["policy_pair"] in {
                "retention-high-cycle",
                "retention-low-cycle",
            }
        ]
        growth_values = []
        by_core = {
            (
                item["policy_pair"],
                item["replica"],
                item["seed"],
                item["model_condition"],
                item["horizon"],
            ): item
            for item in core_primary
        }
        for pair, replica, seed, condition in product(
            ("retention-high-cycle", "retention-low-cycle"),
            EXPECTED_REPLICAS,
            EXPECTED_SEEDS,
            tuple(EXPECTED_MODEL_CONDITIONS),
        ):
            short = by_core[(pair, replica, seed, condition, 90)]
            long = by_core[(pair, replica, seed, condition, 365)]
            growth_values.append(
                long["result_payload"]["comparison"]["unexplained_advantage"]
                - short["result_payload"]["comparison"]["unexplained_advantage"]
            )

        baseline_deltas = []
        honest_differentials = []
        intentional_deltas = []
        suppression_events = 0
        for item in core_primary:
            ref_key = (
                item["component"],
                REFERENCE_PARAMETERIZATION_ID,
                item.get("policy_pair"),
                item.get("horizon"),
                item.get("replica"),
                item.get("seed"),
                item.get("model_condition"),
                item.get("persona_id"),
                item.get("probe_id"),
            )
            reference = reference_primary[ref_key]
            comparison = item["result_payload"]["comparison"]
            ref_comparison = reference["result_payload"]["comparison"]
            baseline_deltas.append(
                abs(comparison["baseline_delta"] - ref_comparison["baseline_delta"])
            )
            suppression_events += comparison["suppression_events"]
            if item["policy_pair"] == "honest-backlog-return":
                honest_differentials.append(
                    comparison["total_delta"] - ref_comparison["total_delta"]
                )
            if item["policy_pair"] == "intentional-backlog":
                intentional_deltas.append(
                    comparison["unexplained_advantage"]
                    - ref_comparison["unexplained_advantage"]
                )

        probe_by_id = {
            item["probe_id"]: item["result_payload"]
            for item in probe_primary
        }
        invariant_probe_ids = EXPECTED_PROBES[:6]
        abuse_probe_ids = EXPECTED_PROBES[6:11]
        research_probe = probe_by_id["INV-RESEARCH-ONLY"]
        persona_failures = [
            {
                "persona_id": item["persona_id"],
                "seed": item["seed"],
                "failures": item["result_payload"]["gate_failures"],
                "suppression_events": item["result_payload"]["suppression_events"],
                "baseline_preservation_ratio": item["result_payload"][
                    "baseline_preservation_ratio"
                ],
            }
            for item in persona_primary
            if (
                item["result_payload"]["gate_failures"]
                or item["result_payload"]["suppression_events"]
                or not close(
                    item["result_payload"]["baseline_preservation_ratio"],
                    1.0,
                )
            )
        ]
        model_condition_counts = {
            condition: sum(
                item["model_condition"] == condition for item in core_primary
            )
            for condition in EXPECTED_MODEL_CONDITIONS
        }
        expected_core_per_condition = (
            len(EXPECTED_POLICY_PAIRS)
            * len(EXPECTED_HORIZONS)
            * len(EXPECTED_REPLICAS)
            * len(EXPECTED_SEEDS)
        )
        evidence_complete = (
            len(core_primary) == 96
            and len(persona_primary) == 32
            and len(probe_primary) == 12
            and all(
                count == expected_core_per_condition
                for count in model_condition_counts.values()
            )
        )
        gates = [
            _gate(
                "GATE-ENDPOINT-CAP",
                bool(endpoint_values)
                and all(value <= 0.03 + ABS_TOLERANCE for value in endpoint_values),
                endpoint_values,
            ),
            _gate(
                "GATE-NO-CYCLING-GROWTH",
                bool(growth_values)
                and all(value <= ABS_TOLERANCE for value in growth_values),
                growth_values,
            ),
            _gate(
                "GATE-BASELINE-PRESERVED",
                bool(baseline_deltas)
                and max(baseline_deltas) <= ABS_TOLERANCE,
                max(baseline_deltas, default=None),
            ),
            _gate(
                "GATE-ZERO-SUPPRESSION",
                suppression_events == 0,
                suppression_events,
            ),
            _gate(
                "GATE-HONEST-BACKLOG-FAIRNESS",
                bool(honest_differentials)
                and all(value >= -ABS_TOLERANCE for value in honest_differentials),
                honest_differentials,
            ),
            _gate(
                "GATE-NO-BACKLOG-GAIN",
                bool(intentional_deltas)
                and all(value <= ABS_TOLERANCE for value in intentional_deltas),
                intentional_deltas,
            ),
            _gate(
                "GATE-ORDINARY-UNIT",
                bool(probe_by_id["INV-ORDINARY-UNIT"]["passed"]),
                probe_by_id["INV-ORDINARY-UNIT"]["observed"],
            ),
            _gate(
                "GATE-AGAIN-CREDIT",
                bool(probe_by_id["INV-AGAIN-CREDIT"]["passed"]),
                probe_by_id["INV-AGAIN-CREDIT"]["observed"],
            ),
            _gate(
                "GATE-BUTTON-NEUTRAL",
                bool(probe_by_id["INV-BUTTON-NEUTRAL"]["passed"]),
                probe_by_id["INV-BUTTON-NEUTRAL"]["observed"],
            ),
            _gate(
                "GATE-SESSION-INVARIANT",
                bool(probe_by_id["INV-SESSION-INVARIANT"]["passed"]),
                probe_by_id["INV-SESSION-INVARIANT"]["observed"],
            ),
            _gate(
                "GATE-NO-RESPONSE-TIME-REWARD",
                bool(probe_by_id["INV-NO-RESPONSE-TIME"]["passed"]),
                probe_by_id["INV-NO-RESPONSE-TIME"]["observed"],
            ),
            _gate(
                "GATE-RESPONSE-VALIDITY",
                bool(probe_by_id["INV-RESPONSE-VALIDITY"]["passed"]),
                probe_by_id["INV-RESPONSE-VALIDITY"]["observed"],
            ),
            _gate(
                "GATE-DETERMINISTIC-REPLAY",
                replay_ok,
                replay_failures,
            ),
            _gate(
                "GATE-SECONDARY-SEED",
                set(manifest["axes"]["seeds"]) == set(EXPECTED_SEEDS),
                manifest["axes"]["seeds"],
            ),
            _gate(
                "GATE-MODEL-CONDITION-SENSITIVITY",
                all(
                    count == expected_core_per_condition
                    for count in model_condition_counts.values()
                )
                and all(value <= ABS_TOLERANCE for value in growth_values)
                and all(value <= 0.03 + ABS_TOLERANCE for value in endpoint_values),
                model_condition_counts,
            ),
            _gate(
                "GATE-PERSONA-SAFETY",
                not persona_failures,
                persona_failures,
            ),
            _gate(
                "GATE-ABUSE-PROBES",
                all(probe_by_id[item]["passed"] for item in abuse_probe_ids),
                {
                    item: probe_by_id[item]["observed"]
                    for item in abuse_probe_ids
                },
            ),
            _gate(
                "GATE-EVIDENCE-COMPLETE",
                evidence_complete,
                {
                    "core_primary": len(core_primary),
                    "persona_primary": len(persona_primary),
                    "probe_primary": len(probe_primary),
                },
            ),
            _gate(
                "GATE-RESEARCH-ONLY",
                bool(research_probe["passed"]),
                research_probe["observed"],
            ),
        ]
        if tuple(item["predicate_id"] for item in gates) != EXPECTED_GATE_IDS:
            raise ValueError("confirmatory gate order drifted")
        complete = gates[-2]["status"] == "PASS"
        passed = all(item["status"] == "PASS" for item in gates)
        outcome = (
            "CONFIRMATORY_ELIGIBLE"
            if passed
            else "CONFIRMATORY_NOT_ELIGIBLE"
            if complete
            else "CONFIRMATORY_INCONCLUSIVE"
        )
        family = next(
            item.family_id
            for item in FROZEN_REVIEW_CANDIDATES
            if item.parameterization_id == candidate_id
        )
        outcomes.append(
            {
                "parameterization_id": candidate_id,
                "family_id": family,
                "outcome": outcome,
                "gates": gates,
            }
        )

    return {
        "status": "COMPLETE",
        "reference_parameterization_id": REFERENCE_PARAMETERIZATION_ID,
        "outcomes": outcomes,
        "ranking_performed": False,
        "final_candidate_selected": False,
        "production_approved": False,
        "g1_6_started": False,
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
        raise ValueError(
            "implementation/base SHA must be lowercase 40-character hex"
        )
    if _git_output(workspace, "rev-parse", "HEAD") != implementation_sha:
        raise ValueError("implementation SHA does not match current HEAD")
    subprocess.run(
        [
            "git",
            "-C",
            str(workspace.root),
            "merge-base",
            "--is-ancestor",
            base_sha,
            implementation_sha,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_confirmatory(
    workspace: ResearchWorkspace | Path | str | None,
    *,
    implementation_sha: str,
    base_sha: str,
    exact_command: str,
) -> dict[str, Any]:
    resolved = resolve_research_workspace(workspace)
    _validate_git_identity(resolved, implementation_sha, base_sha)
    manifest = build_confirmatory_manifest(resolved)
    validate_confirmatory_manifest(manifest)
    results = []
    for item in manifest["units"]:
        results.append(
            run_confirmatory_execution_unit(
                ConfirmatoryExecutionUnit(
                    component=item["component"],
                    variant_id=item["variant_id"],
                    replay_id=item["replay_id"],
                    policy_pair=item["policy_pair"],
                    horizon=item["horizon"],
                    replica=item["replica"],
                    seed=item["seed"],
                    model_condition=item["model_condition"],
                    persona_id=item["persona_id"],
                    probe_id=item["probe_id"],
                ),
                workspace=resolved,
            )
        )
    gate_evidence = evaluate_confirmatory_gates(
        results,
        manifest=manifest,
    )
    payload = {
        "evidence_version": "review-xp-confirmatory-evidence-v1",
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
        "units": results,
        "gate_evidence": gate_evidence,
    }
    payload["evidence_digest"] = canonical_digest(payload)
    validate_confirmatory_result(payload)
    return payload


def validate_confirmatory_result(payload: Mapping[str, Any]) -> None:
    manifest = payload.get("manifest")
    units = payload.get("units")
    gate_evidence = payload.get("gate_evidence")
    if not isinstance(manifest, dict):
        raise ValueError("confirmatory result manifest is missing")
    if not isinstance(units, list):
        raise ValueError("confirmatory result units are missing")
    if not isinstance(gate_evidence, dict):
        raise ValueError("confirmatory gate evidence is missing")
    validate_confirmatory_manifest(manifest)
    if len(units) != EXPECTED_TOTAL_UNITS:
        raise ValueError("confirmatory result unit count drifted")
    outcomes = gate_evidence.get("outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != 2:
        raise ValueError("confirmatory outcomes are incomplete")
    if any(item.get("outcome") not in ALLOWED_OUTCOMES for item in outcomes):
        raise ValueError("confirmatory outcome value is invalid")
    if any(
        gate_evidence.get(name) is not False
        for name in (
            "ranking_performed",
            "final_candidate_selected",
            "production_approved",
            "g1_6_started",
        )
    ):
        raise ValueError("confirmatory result crossed a forbidden boundary")
    recomputed_gate_evidence = evaluate_confirmatory_gates(
        units,
        manifest=manifest,
    )
    if gate_evidence != recomputed_gate_evidence:
        raise ValueError("confirmatory gate evidence mismatch")
    digest = payload.get("evidence_digest")
    without_digest = dict(payload)
    without_digest.pop("evidence_digest", None)
    if digest != canonical_digest(without_digest):
        raise ValueError("confirmatory evidence digest mismatch")


def load_and_validate_confirmatory_evidence(path: Path) -> dict[str, Any]:
    payload = load_strict_json(path, max_bytes=MAX_EVIDENCE_BYTES)
    if not isinstance(payload, dict):
        raise ValueError("confirmatory evidence must be a JSON object")
    validate_confirmatory_result(payload)
    return payload


def render_confirmatory_summary(payload: Mapping[str, Any]) -> str:
    manifest = payload["manifest"]
    lines = [
        "# G1.5 Review XP confirmatory evidence",
        "",
        f"- Implementation SHA: `{payload['provenance']['implementation_sha']}`",
        f"- Base SHA: `{payload['provenance']['base_sha']}`",
        f"- Expected units: **{manifest['expected_units']}**",
        f"- Actual unique units: **{manifest['actual_unique_units']}**",
        (
            "- Missing / extra / duplicates: "
            f"**{manifest['missing_units']} / {manifest['extra_units']} / "
            f"{manifest['duplicate_units']}**"
        ),
        f"- Evidence digest: `{payload['evidence_digest']}`",
        "",
        "| Family | Parameterization | Outcome |",
        "|---|---|---|",
    ]
    for item in payload["gate_evidence"]["outcomes"]:
        lines.append(
            f"| `{item['family_id']}` | `{item['parameterization_id']}` | "
            f"`{item['outcome']}` |"
        )
    lines.extend(
        [
            "",
            "No ranking was performed. No final candidate or production behavior "
            "was selected.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_confirmatory_reports(
    payload: Mapping[str, Any],
    output_root: Path,
) -> Path:
    if output_root.exists() and output_root.is_symlink():
        raise ValueError("confirmatory output root must not be a symlink")
    run_id = str(payload["evidence_digest"])[:12]
    run_dir = output_root.resolve() / "confirmatory" / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError("confirmatory run directory already contains files")
    run_dir.mkdir(parents=True, exist_ok=True)
    if run_dir.is_symlink():
        raise ValueError("confirmatory run directory must not be a symlink")
    evidence_path = run_dir / "evidence.json"
    manifest_path = run_dir / "manifest.json"
    summary_path = run_dir / "summary.md"
    metadata_path = run_dir / "run-metadata.json"
    evidence_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            payload["manifest"],
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        render_confirmatory_summary(payload),
        encoding="utf-8",
    )
    metadata = {
        "evidence_version": payload["evidence_version"],
        "evidence_digest": payload["evidence_digest"],
        "manifest_digest": payload["manifest"]["manifest_digest"],
        "implementation_sha": payload["provenance"]["implementation_sha"],
        "base_sha": payload["provenance"]["base_sha"],
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return run_dir
