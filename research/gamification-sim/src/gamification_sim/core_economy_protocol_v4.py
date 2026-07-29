from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest, canonical_dumps
from .review_candidate_mechanisms import (
    RewardExecutionContext,
    frozen_review_candidate_trace,
    memory_gain_multiplier,
)
from .strict_json import load_strict_json

PROTOCOL_VERSION = 4
PIPELINE_VERSION = 4
VALIDATOR_VERSION = "core-economy-protocol-v4-validator-1"
GENERATOR_VERSION = "core-economy-protocol-v4-generator-1"
EPSILON = 1e-12
ROUNDING_DECIMALS = 12

PROTOCOL_PATH = Path("contracts/core-economy-candidate-protocol-v4.json")
PROTOCOL_SCHEMA_PATH = Path("schemas/core-economy-candidate-protocol-v4.schema.json")
PIPELINE_PATH = Path("contracts/core-economy-evaluation-pipeline-v4.json")
PIPELINE_SCHEMA_PATH = Path("schemas/core-economy-evaluation-pipeline-v4.schema.json")
SCENARIOS_PATH = Path("fixtures/core-economy-candidate-scenarios-v4.json")
SCENARIOS_SCHEMA_PATH = Path("schemas/core-economy-candidate-scenarios-v4.schema.json")
MATRIX_PATH = Path("matrices/core-economy-screening-matrix-v4.json")
MATRIX_SCHEMA_PATH = Path("schemas/core-economy-screening-matrix-v4.schema.json")
NEGATIVE_CORPUS_PATH = Path("fixtures/core-economy-candidate-protocol-v4-negative/manifest.json")
HUMAN_PROTOCOL_REPOSITORY_PATH = Path("docs/gamification/core-economy-candidate-protocol-v4.md")
ROADMAP_CLOSEOUT_REPOSITORY_PATH = Path("roadmap/gamification/g4-core-economy-candidate-protocol-v4.md")

HISTORICAL_SHA256 = {
    "contracts/core-economy-candidate-protocol-v1.json": "6b993ebd5f5587145e4e4c6d6d7e946d4b3da7e8633ddfd1334eab29dda93abf",
    "schemas/core-economy-candidate-protocol-v1.schema.json": "fd9287da36657b6b4125d3240e8d05bc864cbbf024d41805ec24e270b91dc222",
    "fixtures/core-economy-candidate-scenarios-v1.json": "3f9f320fa6131b4ecbfe3272d41631005e778425a8662203c37f3d6c534dd193",
    "schemas/core-economy-candidate-scenarios-v1.schema.json": "7de2c784d1b81755a2bdb7f25b514937baf4089ecc632090a5c1a4c8919a0a4e",
    "matrices/core-economy-screening-matrix-v1.json": "daba6406b60698dd0c2f4cd990f2923396bd23d0a4c0861891fe3632ccebaf13",
    "schemas/core-economy-screening-matrix-v1.schema.json": "917b86215e65d4ccc536b694dd49bac1c288ecccf212f1ed5743d35b74a610b3",
    "contracts/core-economy-candidate-protocol-v2.json": "2282502227babd3260397099f0de8f718c252e463b26820979a65fc740b24eb1",
    "contracts/core-economy-evaluation-pipeline-v2.json": "601f6d2ba1ddd8f6a7d65b2f665228d2c35aa8144c6b20d41ad1910bdebb0715",
    "schemas/core-economy-candidate-protocol-v2.schema.json": "0cb7306cfa3c3acb74f32a7c5a72c079244485f00c190fe95078b6c33d5c831e",
    "schemas/core-economy-evaluation-pipeline-v2.schema.json": "3fbbd52115ddef342a889a0cf79db4b136ede2e3a2df1c08bd59e83023b1fc6c",
    "fixtures/core-economy-candidate-scenarios-v2.json": "3f8929a842621fa410ea17398b9096b6fdaaaf7d521e4b6178bc5068142710d8",
    "schemas/core-economy-candidate-scenarios-v2.schema.json": "a49a233789224d5bcc3e05eb1b09a9788a68d6e0b5ae414078bee3a4715ba7dc",
    "matrices/core-economy-screening-matrix-v2.json": "3081f45e399830a084b987a2366370e2efeae5b55d5fa9f23f8af72601017012",
    "schemas/core-economy-screening-matrix-v2.schema.json": "bf1b02ad1255b52a1d5ab5bebff73079a45795df14b7b35e2008ea8b546d5edd",
    "fixtures/core-economy-candidate-protocol-v2-negative/manifest.json": "962e9da69d7005381d99fed258783b664b6f41170702c0fa0642da8a9febca88",
    "src/gamification_sim/core_economy_protocol_v2.py": "76570b9507fcea25be46159238990180c408f6d839ddedba177f2dbbe97a8460",
    "tests/test_core_economy_protocol_v2.py": "0b2673e76997a9d61b6194922597258d3f33f8f97b7407b89d748d4125aea045",
    "contracts/core-economy-candidate-protocol-v3.json": "2a471436821ee6322e229a2bc9f0fb9f0143e87697774c752f116ae2827ab790",
    "contracts/core-economy-evaluation-pipeline-v3.json": "1207f77b7ab7f6e9b6a228664f2848b9b567498cb2abd449f65806d2bd67c6d8",
    "schemas/core-economy-candidate-protocol-v3.schema.json": "faa1a55cbabb3a8b3d6bb1faaf20c69f0dbe1a66d5b34ecf5ec5627eeb69ef11",
    "schemas/core-economy-evaluation-pipeline-v3.schema.json": "1bef2f06fe324eb803aaf73ed45945ede24d2a9beb06ba9f5f4d3128281d36c2",
    "fixtures/core-economy-candidate-scenarios-v3.json": "9a586f7940abcda2a3cf7a5b1d5c7e9ac6b593651acbb99c7c32736b44979d66",
    "schemas/core-economy-candidate-scenarios-v3.schema.json": "505e7d6a197c33dbc8681cce1d1631b8b4b52dba3addc30fe56bf11de9a31a72",
    "matrices/core-economy-screening-matrix-v3.json": "4125b0ac2a17d6ba3bc6498f8892802be1032ee41c4240d565e63a2107d80a42",
    "schemas/core-economy-screening-matrix-v3.schema.json": "f75f6f9c334b10e47455bd9a536d25738c1db780662333bd31eebe6668582667",
    "fixtures/core-economy-candidate-protocol-v3-negative/manifest.json": "106999cd3688d6071a403b92ac5421ca39caf1876c579bbca5831ce0274f2d3f",
    "src/gamification_sim/core_economy_protocol_v3.py": "fafa5550e8eb19c74ddb457557d2067a37140e961a304f61eaebed90ab832728",
    "tests/test_core_economy_protocol_v3.py": "89f38b7c6263bd66c8c0f2374a21b9e9b74974431b980c2a51c4976cbbbf894e",
}

G1_SOURCE_IDENTITIES = {
    "implementation_path": "src/gamification_sim/review_candidate_mechanisms.py",
    "implementation_sha256": "15eb0f4f20745ad7fe36f6baa56222bb7897c08f021f160bef88bb36cd71b092",
    "protocol_path": "contracts/review-xp-candidate-protocol-v1.json",
    "protocol_sha256": "9ff11bd82b67ca6fa1c1ce9d4ec1b8baa1309ea48179f8a751921b6e86ab5e8f",
}

G2_SOURCE_IDENTITIES = {
    "allocation_path": "src/gamification_sim/learn_reward_allocation.py",
    "allocation_sha256": "2f207024c6a30ec12861c7badfa66492035430b61e7dd30b09b97006dd7652bd",
    "candidate_protocol_path": "contracts/learn-xp-candidate-protocol-v1.json",
    "candidate_protocol_sha256": "d6cc80ec44326f63357aab043943e69768ade202b715026279c96d0d52484572",
    "confirmatory_protocol_path": "contracts/learn-xp-confirmatory-protocol-v1.json",
    "confirmatory_protocol_sha256": "34b15b6256dec4704766bd7fdf3942a1cd0abfab0742c4d2ec14dda6c9c6e9c6",
}

REQUIRED_DIMENSIONS = (
    "CROSS_DOMAIN_CONVERSION",
    "UNCERTAINTY_RESPONSE",
    "DAILY_BOUNDING",
    "PRODUCTIVE_DAY",
    "LEVEL_CURVE",
    "STREAK_PLANNED_REST",
    "MOMENTUM",
    "RECOVERY",
)
REVIEW_MEMBERS = ("P-STEP-ZERO", "P-TAPER-ZERO-30D")
LEARN_CANDIDATE = "C-CONFIRMATION-ONLY-D1-NOTE-SIBLING"
LEARN_LIMITATION = "DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE"
PERSONA_IDS = (
    'BEGINNER_HEAVY',
    'MATURE_DECK',
    'BALANCED',
    'BACKLOG_RETURNER',
    'LOW_VOLUME_CONSISTENT',
    'INTENSIVE_LEARNER',
    'ALTERNATING_INTENSIVE_LIGHT',
    'PLANNED_REST_SCHEDULE',
    'IRREGULAR_LEGITIMATE',
)
THREAT_IDS = (
    'DOMAIN_IMBALANCE',
    'RAW_VOLUME_FARMING',
    'BACKLOG_FARMING',
    'NEW_MATERIAL_FLOODING',
    'SESSION_SPLIT_FARMING',
    'CALENDAR_BOUNDARY_FARMING',
    'CONFIGURATION_FARMING',
    'ANSWER_BEHAVIOR_FARMING',
    'STREAK_PRESSURE',
    'PLANNED_REST_EXPLOIT',
    'RECOVERY_BONUS_LOOP',
    'MOMENTUM_SNOWBALL',
    'UNCERTAINTY_COLLAPSE',
    'EXPLANATION_OPACITY',
)
INVARIANT_IDS = (
    'INV-G3-CREATE-XP-EXCLUDED',
    'INV-REVIEW-UNCERTAINTY-PRESERVED',
    'INV-LEARN-LIMITATION-PRESERVED',
    'INV-SCHEDULER-UNCHANGED',
    'INV-FSRS-UNCHANGED',
    'INV-DUE-DATES-UNCHANGED',
    'INV-NO-DIRECT-BUTTON-PRICING',
    'INV-HONEST-AGAIN-NOT-PUNISHED',
    'INV-NO-RESPONSE-TIME-REWARD',
    'INV-NO-TIME-SPENT-REWARD',
    'INV-NO-SESSION-SPLIT-GAIN',
    'INV-NO-BACKLOG-SIZE-GAIN',
    'INV-NO-NEW-MATERIAL-FLOOD-GAIN',
    'INV-NO-CONFIGURATION-GAIN',
    'INV-XP-NONNEGATIVE',
    'INV-LEVEL-MONOTONIC',
    'INV-PLANNED-REST-NEUTRAL',
    'INV-NO-ABSENCE-XP-DEBT',
    'INV-RECOVERY-NO-BONUS-LOOP',
    'INV-STREAK-NO-XP-MULTIPLIER',
    'INV-MOMENTUM-BOUNDED-NONSPENDABLE',
    'INV-MOMENTUM-NO-RECURSIVE-MULTIPLIER',
    'INV-DETERMINISTIC-REPLAY',
    'INV-DECOMPOSABLE-EVIDENCE',
    'INV-EXPLAINABLE-CONTRIBUTIONS',
    'INV-RESEARCH-ONLY',
    'INV-NO-REAL-USER-DATA',
    'INV-NO-PRODUCTION-APPROVAL',
)

class ProtocolValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ProtocolValidationError(code, message)


def _round(value: float) -> float:
    return round(float(value), ROUNDING_DECIMALS)


def _canonical_bytes(value: Any) -> bytes:
    return (canonical_dumps(value) + "\n").encode("utf-8")


def _digest_preimage(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    identity = result.get("identity")
    if isinstance(identity, dict):
        identity.pop("artifact_digest", None)
    if result.get("identity", {}).get("artifact_id") == "core-economy-candidate-protocol":
        result["artifact_registry"] = {"digest_scope": "EXCLUDED_FROM_PROTOCOL_DIGEST"}
    return result


def artifact_digest(value: Mapping[str, Any]) -> str:
    return canonical_digest(_digest_preimage(value))


def _finalize_digest(value: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(value)
    value["identity"]["artifact_digest"] = artifact_digest(value)
    return value


def _typed_ast(op: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"op": op}
    if args:
        node["args"] = list(args)
    node.update(kwargs)
    return node


UNCERTAINTY_STATES = ("NORMAL", "WATCH", "RESTRICTED", "RECOVERING")
UNCERTAINTY_SIGNALS = ("NORMAL", "ISOLATED_ANOMALY", "CONFLICT", "MISSING")
UNCERTAINTY_MULTIPLIERS = {
    "NORMAL": 1.0,
    "WATCH": 0.75,
    "RESTRICTED": 0.5,
    "RECOVERING": 0.75,
}


def _uncertainty_transition_table() -> list[dict[str, Any]]:
    definitions = [
        ("NORMAL", "NORMAL", "NORMAL", 1.0, "RC-U-NORMAL-HOLD", "ALWAYS"),
        ("NORMAL", "ISOLATED_ANOMALY", "WATCH", 0.75, "RC-U-ISOLATED-WATCH", "CURRENT_SIGNAL_IS_ISOLATED_ANOMALY"),
        ("NORMAL", "CONFLICT", "WATCH", 0.75, "RC-U-FIRST-CONFLICT-WATCH", "CONFLICT_COUNT_IN_WINDOW_GTE_1"),
        ("WATCH", "NORMAL", "RECOVERING", 0.75, "RC-U-WATCH-RECOVERING", "CURRENT_SIGNAL_IS_NORMAL"),
        ("WATCH", "ISOLATED_ANOMALY", "WATCH", 0.75, "RC-U-WATCH-HOLD", "CURRENT_SIGNAL_IS_ISOLATED_ANOMALY"),
        ("WATCH", "CONFLICT", "WATCH", 0.75, "RC-U-CONFLICT-WINDOW-HOLD", "CONFLICT_COUNT_IN_WINDOW_LT_2"),
        ("WATCH", "CONFLICT", "RESTRICTED", 0.5, "RC-U-REPEATED-CONFLICT-RESTRICTED", "CONFLICT_COUNT_IN_WINDOW_GTE_2"),
        ("RESTRICTED", "NORMAL", "RECOVERING", 0.5, "RC-U-RESTRICTED-RECOVERING", "CURRENT_SIGNAL_IS_NORMAL"),
        ("RESTRICTED", "ISOLATED_ANOMALY", "RESTRICTED", 0.5, "RC-U-RESTRICTED-HOLD", "CURRENT_SIGNAL_IS_ISOLATED_ANOMALY"),
        ("RESTRICTED", "CONFLICT", "RESTRICTED", 0.5, "RC-U-CONFLICT-RESTRICTED-HOLD", "CURRENT_SIGNAL_IS_CONFLICT"),
        ("RECOVERING", "NORMAL", "RECOVERING", 0.75, "RC-U-RECOVERY-HOLD", "CONSECUTIVE_NORMAL_INCLUDING_CURRENT_LT_2"),
        ("RECOVERING", "NORMAL", "NORMAL", 1.0, "RC-U-RECOVERY-COMPLETE", "CONSECUTIVE_NORMAL_INCLUDING_CURRENT_GTE_2"),
        ("RECOVERING", "ISOLATED_ANOMALY", "WATCH", 0.75, "RC-U-RECOVERY-INTERRUPTED-WATCH", "CURRENT_SIGNAL_IS_ISOLATED_ANOMALY"),
        ("RECOVERING", "CONFLICT", "RESTRICTED", 0.5, "RC-U-RECOVERY-CONFLICT-RESTRICTED", "CURRENT_SIGNAL_IS_CONFLICT"),
    ]
    rows = []
    for current_state, signal, next_state, multiplier, reason_code, predicate in definitions:
        rows.append(
            {
                "current_state": current_state,
                "signal": signal,
                "recent_evidence_window": {
                    "kind": "TRAILING_EVENT_COUNT",
                    "size": 3,
                    "includes_current": True,
                },
                "predicate": {"op": predicate},
                "next_state": next_state,
                "applied_multiplier": multiplier,
                "state_read_timing": "BEFORE_CURRENT_EVENT",
                "multiplier_apply_timing": "AFTER_STATE_READ_BEFORE_STATE_WRITE",
                "state_write_timing": "AFTER_CURRENT_EVENT_CONTRIBUTION",
                "reason_code": reason_code,
                "missing_evidence_behavior": "HOLD_CURRENT_STATE_AND_USE_CURRENT_STATE_MULTIPLIER",
            }
        )
    for current_state in UNCERTAINTY_STATES:
        rows.append(
            {
                "current_state": current_state,
                "signal": "MISSING",
                "recent_evidence_window": {
                    "kind": "TRAILING_EVENT_COUNT",
                    "size": 3,
                    "includes_current": True,
                },
                "predicate": {"op": "MISSING_SIGNAL"},
                "next_state": current_state,
                "applied_multiplier": UNCERTAINTY_MULTIPLIERS[current_state],
                "state_read_timing": "BEFORE_CURRENT_EVENT",
                "multiplier_apply_timing": "AFTER_STATE_READ_BEFORE_STATE_WRITE",
                "state_write_timing": "NO_WRITE_HOLD",
                "reason_code": "RC-U-MISSING-HOLD",
                "missing_evidence_behavior": "HOLD_CURRENT_STATE_AND_USE_CURRENT_STATE_MULTIPLIER",
            }
        )
    return rows


def evaluate_uncertainty_transition(
    current_state: str,
    signal: str | None,
    recent_signals: Sequence[str] = (),
) -> dict[str, Any]:
    if current_state not in UNCERTAINTY_STATES:
        _fail("UNCERTAINTY_UNKNOWN_STATE", current_state)
    normalized_signal = "MISSING" if signal is None else signal
    if normalized_signal not in UNCERTAINTY_SIGNALS:
        _fail("UNCERTAINTY_UNKNOWN_SIGNAL", normalized_signal)
    window = [item for item in recent_signals[-2:] if item in UNCERTAINTY_SIGNALS]
    window.append(normalized_signal)
    conflict_count = sum(item == "CONFLICT" for item in window)
    consecutive_normal = 0
    for item in reversed(window):
        if item != "NORMAL":
            break
        consecutive_normal += 1

    def predicate_matches(row: Mapping[str, Any]) -> bool:
        op = row["predicate"]["op"]
        if op == "CONFLICT_COUNT_IN_WINDOW_LT_2":
            return conflict_count < 2
        if op == "CONFLICT_COUNT_IN_WINDOW_GTE_2":
            return conflict_count >= 2
        if op == "CONSECUTIVE_NORMAL_INCLUDING_CURRENT_LT_2":
            return consecutive_normal < 2
        if op == "CONSECUTIVE_NORMAL_INCLUDING_CURRENT_GTE_2":
            return consecutive_normal >= 2
        return True

    matches = [
        row
        for row in _uncertainty_transition_table()
        if row["current_state"] == current_state
        and row["signal"] == normalized_signal
        and predicate_matches(row)
    ]
    if len(matches) != 1:
        _fail("UNCERTAINTY_TRANSITION_RESOLUTION", f"{current_state}/{normalized_signal}")
    row = matches[0]
    return {
        key: row[key]
        for key in (
            "current_state",
            "signal",
            "next_state",
            "applied_multiplier",
            "state_read_timing",
            "multiplier_apply_timing",
            "state_write_timing",
            "reason_code",
        )
    }


def evaluate_review_source(
    review_member: str,
    *,
    day: int,
    verified_base: float,
    positive_context: float,
    retention_transition_day: int = 60,
) -> dict[str, Any]:
    if review_member not in REVIEW_MEMBERS:
        _fail("REVIEW_MEMBER_SOURCE_MISMATCH", review_member)
    if min(verified_base, positive_context) < 0:
        _fail("NEGATIVE_CONTRIBUTION", "Review source components cannot be negative")
    context = RewardExecutionContext(
        day=day,
        retention_transition_days=(retention_transition_day,),
    )
    multiplier = memory_gain_multiplier(review_member, context)
    trace = frozen_review_candidate_trace(review_member)
    return {
        "review_member": review_member,
        "day": day,
        "retention_transition_day": retention_transition_day,
        "verified_base": _round(verified_base),
        "positive_context_before": _round(positive_context),
        "memory_gain_multiplier": _round(multiplier),
        "positive_context_after": _round(positive_context * multiplier),
        "source_output": _round(verified_base + positive_context * multiplier),
        "source_trace": trace,
        "reason_code": "RC-REVIEW-STEP" if review_member == "P-STEP-ZERO" else "RC-REVIEW-TAPER",
    }


def _candidate_registry() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = [
        {
            "candidate_id": "X-EQUALIZED-1_0-1_0",
            "dimension_id": "CROSS_DOMAIN_CONVERSION",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "review_weight": 1.0,
            "learn_weight": 1.0,
            "output_unit": "NORMALIZED_PROGRESSION_UNIT",
            "normalization_shape": "ORDINARY_SOURCE_ANCHOR_IDENTITY",
            "formula_ast": _typed_ast("ADD", _typed_ast("MUL", "review_weight", "review_daily"), _typed_ast("MUL", "learn_weight", "learn_daily")),
            "source_anchors": {"ordinary_review_unit": 1.0, "maximum_review_unit": 1.32, "confirmed_learn_lru": 1.0},
            "limitations": ["NO_PRODUCTION_PRICING_CLAIM", "HUMAN_VALUE_EQUIVALENCE_NOT_ESTABLISHED"],
        },
        {
            "candidate_id": "X-LEARN-LEANING-0_8-1_2",
            "dimension_id": "CROSS_DOMAIN_CONVERSION",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "review_weight": 0.8,
            "learn_weight": 1.2,
            "output_unit": "NORMALIZED_PROGRESSION_UNIT",
            "normalization_shape": "ORDINARY_SOURCE_ANCHOR_IDENTITY",
            "formula_ast": _typed_ast("ADD", _typed_ast("MUL", "review_weight", "review_daily"), _typed_ast("MUL", "learn_weight", "learn_daily")),
            "source_anchors": {"ordinary_review_unit": 1.0, "maximum_review_unit": 1.32, "confirmed_learn_lru": 1.0},
            "limitations": ["SENSITIVITY_ONLY", "NO_PRODUCTION_PRICING_CLAIM"],
        },
        {
            "candidate_id": "X-REVIEW-LEANING-1_2-0_8-CONTROL",
            "dimension_id": "CROSS_DOMAIN_CONVERSION",
            "control_only": True,
            "recommendation_eligible": False,
            "production_status": "RESEARCH_ONLY",
            "review_weight": 1.2,
            "learn_weight": 0.8,
            "output_unit": "NORMALIZED_PROGRESSION_UNIT",
            "normalization_shape": "ORDINARY_SOURCE_ANCHOR_IDENTITY",
            "formula_ast": _typed_ast("ADD", _typed_ast("MUL", "review_weight", "review_daily"), _typed_ast("MUL", "learn_weight", "learn_daily")),
            "source_anchors": {"ordinary_review_unit": 1.0, "maximum_review_unit": 1.32, "confirmed_learn_lru": 1.0},
            "limitations": ["CONTROL_ONLY", "NO_PRODUCTION_PRICING_CLAIM"],
        },
        {
            "candidate_id": "U-ABRUPT-CUTOFF-CONTROL",
            "dimension_id": "UNCERTAINTY_RESPONSE",
            "control_only": True,
            "recommendation_eligible": False,
            "production_status": "RESEARCH_ONLY",
            "positive_context_multipliers": [0.0],
            "formula_ast": _typed_ast("ADD", "verified_base", "negative_context", _typed_ast("MUL", "positive_context", "state_multiplier")),
            "limitations": ["EXPECTED_FALSE_POSITIVE_CONTEXT_GATE_FAILURE", "CONTROL_ONLY"],
        },
        {
            "candidate_id": "U-FIXED-STEPPED-TAPER",
            "dimension_id": "UNCERTAINTY_RESPONSE",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "positive_context_multipliers": [0.75, 0.5, 0.25, 0.25],
            "formula_ast": _typed_ast("STEPPED_SEQUENCE", values=[0.75, 0.5, 0.25, 0.25], recovery_increment=0.25),
            "limitations": ["STEPPED_WITH_PLATEAU_NOT_LINEAR", "SYNTHETIC_SEQUENCE"],
        },
        {
            "candidate_id": "U-CONFIDENCE-TAPER-RECOVERY",
            "dimension_id": "UNCERTAINTY_RESPONSE",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "positive_context_multipliers": [1.0, 0.75, 0.5],
            "formula_ast": _typed_ast(
                "TYPED_STATE_MACHINE",
                states=list(UNCERTAINTY_STATES),
                signals=list(UNCERTAINTY_SIGNALS),
                initial_state="NORMAL",
                transitions=_uncertainty_transition_table(),
                affected_component="POSITIVE_CONTEXT",
            ),
            "limitations": ["SIGNAL_COMPONENT_SCOPE_ONLY", "NO_USER_GUILT_STATE", "SYNTHETIC_EVIDENCE_WINDOW"],
        },
        {
            "candidate_id": "D-PER-DOMAIN-BOUNDED-MEDIUM",
            "dimension_id": "DAILY_BOUNDING",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "scope": "PER_DOMAIN_THEN_COMBINE",
            "formula_ast": _typed_ast(
                "PER_DOMAIN_BOUNDED_PIECEWISE",
                review_bands=[[10.0, 1.0], [20.0, 0.5], [70.0, 0.2]],
                learn_bands=[[2.0, 1.0], [8.0, 0.5], [20.0, 0.2]],
                tail_multiplier=0.0,
                review_input_cap=100.0,
                learn_input_cap=30.0,
                review_output_cap=34.0,
                learn_output_cap=10.0,
            ),
            "limitations": ["SYNTHETIC_SCALE", "NO_PRODUCTION_CAP_CLAIM", "PROSPECTIVE_RESEARCH_BOUND"],
        },
        {
            "candidate_id": "D-PER-DOMAIN-SQRT-HIGH",
            "dimension_id": "DAILY_BOUNDING",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "scope": "PER_DOMAIN_THEN_COMBINE",
            "formula_ast": _typed_ast("PER_DOMAIN_SQRT", review_onset=30.0, review_cap=60.0, learn_onset=5.0, learn_cap=20.0),
            "limitations": ["HIGH_SCALE_SENSITIVITY", "NO_PRODUCTION_CAP_CLAIM"],
        },
        {
            "candidate_id": "D-COMBINED-HARD-6-CONTROL",
            "dimension_id": "DAILY_BOUNDING",
            "control_only": True,
            "recommendation_eligible": False,
            "production_status": "RESEARCH_ONLY",
            "scope": "COMBINED_TOTAL_CONTROL",
            "formula_ast": _typed_ast("GLOBAL_HARD_CAP_AFTER_CONVERSION", cap=6.0, allocation="PROPORTIONAL"),
            "limitations": ["EXPECTED_CROWDOUT_AT_SATURATION", "CONTROL_ONLY"],
        },
        {
            "candidate_id": "P-DAY-BOUNDED-075",
            "dimension_id": "PRODUCTIVE_DAY",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "formula_ast": _typed_ast("PRODUCTIVE_IF", predicate="planned_rest == false and total_npu >= 0.75"),
            "limitations": ["CLASSIFICATION_ONLY", "DOES_NOT_DELETE_CONTRIBUTION"],
        },
        {
            "candidate_id": "P-DAY-DOMAIN-EVIDENCE",
            "dimension_id": "PRODUCTIVE_DAY",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "formula_ast": _typed_ast("PRODUCTIVE_IF", predicate="planned_rest == false and (review_verified_base >= 0.50 or confirmed_learn >= 0.50 or total_npu >= 0.75)"),
            "limitations": ["NO_RAW_COUNT_OR_APP_ACTIVITY", "CLASSIFICATION_ONLY"],
        },
        {
            "candidate_id": "L-NPU-POWER-1_6",
            "dimension_id": "LEVEL_CURVE",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "progression_input_unit": "NORMALIZED_PROGRESSION_UNIT",
            "formula_ast": _typed_ast("LEVEL_THRESHOLD", expression="ceil(12*n^1.6*1000)/1000"),
            "limitations": ["PRESENTATION_ONLY", "NO_MASTERY_CLAIM"],
        },
        {
            "candidate_id": "L-NPU-PIECEWISE",
            "dimension_id": "LEVEL_CURVE",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "progression_input_unit": "NORMALIZED_PROGRESSION_UNIT",
            "formula_ast": _typed_ast("PIECEWISE_LEVEL_COST", bands=[[1, 10, 20.0], [11, 20, 40.0], [21, "INF", 80.0]]),
            "limitations": ["PRESENTATION_ONLY", "NO_MASTERY_CLAIM"],
        },
        {
            "candidate_id": "S-STRICT-PLANNED-REST",
            "dimension_id": "STREAK_PLANNED_REST",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "xp_multiplier": False,
            "formula_ast": _typed_ast("STREAK_TRANSITION", productive="INCREMENT", planned_rest="PRESERVE", absent="RESET"),
            "limitations": ["PLANNING_UI_DEFERRED", "NO_PREMIUM_FREEZE"],
        },
        {
            "candidate_id": "S-ONE-GRACE-14D",
            "dimension_id": "STREAK_PLANNED_REST",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "xp_multiplier": False,
            "formula_ast": _typed_ast("STREAK_TRANSITION", productive="INCREMENT", planned_rest="PRESERVE", first_absent_in_14d="PRESERVE", next_absent="RESET"),
            "limitations": ["GRACE_IS_NOT_REWARD", "NO_CONSUMABLE"],
        },
        {
            "candidate_id": "M-EMA-025",
            "dimension_id": "MOMENTUM",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "xp_multiplier": False,
            "formula_ast": _typed_ast("EMA", alpha=0.25, planned_rest="HOLD", range=[0.0, 1.0]),
            "limitations": ["INDICATOR_ONLY", "NON_SPENDABLE"],
        },
        {
            "candidate_id": "M-ROLLING-7-NONREST",
            "dimension_id": "MOMENTUM",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "xp_multiplier": False,
            "formula_ast": _typed_ast("ROLLING_MEAN", window=7, exclude="PLANNED_REST", range=[0.0, 1.0]),
            "limitations": ["INDICATOR_ONLY", "NON_SPENDABLE"],
        },
        {
            "candidate_id": "R-LINEAR-3-NORMAL-DAYS",
            "dimension_id": "RECOVERY",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "contribution_multiplier": 1.0,
            "bonus_allowed": False,
            "formula_ast": _typed_ast("RECOVERY_INDICATOR", increments=[1 / 3, 1 / 3, 1 / 3]),
            "limitations": ["STATE_ONLY", "NO_RETURN_BONUS"],
        },
        {
            "candidate_id": "R-STEPWISE-2-NORMAL-DAYS",
            "dimension_id": "RECOVERY",
            "control_only": False,
            "recommendation_eligible": True,
            "production_status": "RESEARCH_ONLY",
            "contribution_multiplier": 1.0,
            "bonus_allowed": False,
            "formula_ast": _typed_ast("RECOVERY_STATE", sequence=["RECOVERING", "NORMAL"]),
            "limitations": ["STATE_ONLY", "NO_RETURN_BONUS"],
        },
    ]
    return candidates


def _candidate_by_id(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(candidate["candidate_id"]): candidate for candidate in candidates}


def _bundle_registry(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    baseline = {
        "CROSS_DOMAIN_CONVERSION": "X-EQUALIZED-1_0-1_0",
        "UNCERTAINTY_RESPONSE": "U-CONFIDENCE-TAPER-RECOVERY",
        "DAILY_BOUNDING": "D-PER-DOMAIN-BOUNDED-MEDIUM",
        "PRODUCTIVE_DAY": "P-DAY-DOMAIN-EVIDENCE",
        "LEVEL_CURVE": "L-NPU-POWER-1_6",
        "STREAK_PLANNED_REST": "S-STRICT-PLANNED-REST",
        "MOMENTUM": "M-ROLLING-7-NONREST",
        "RECOVERY": "R-STEPWISE-2-NORMAL-DAYS",
    }
    candidate_map = _candidate_by_id(candidates)
    bundles: list[dict[str, Any]] = []
    seen_combinations: dict[tuple[str, ...], str] = {}

    def add(bundle_id: str, overrides: Mapping[str, str], tags: Iterable[str], purpose: str) -> None:
        chosen = dict(baseline)
        chosen.update(overrides)
        combo = tuple(chosen[dimension] for dimension in REQUIRED_DIMENSIONS)
        if combo in seen_combinations:
            return
        selected = [candidate_map[chosen[dimension]] for dimension in REQUIRED_DIMENSIONS]
        control = any(bool(item["control_only"]) for item in selected)
        recommendation = not control and all(bool(item["recommendation_eligible"]) for item in selected)
        bundles.append(
            {
                "candidate_bundle_id": bundle_id,
                "dimension_candidates": [
                    {"dimension_id": dimension, "candidate_id": chosen[dimension]}
                    for dimension in REQUIRED_DIMENSIONS
                ],
                "control_only": control,
                "recommendation_eligible": recommendation,
                "production_status": "RESEARCH_ONLY",
                "review_evaluation": "PARALLEL_SEPARATE",
                "coverage_tags": sorted(set(tags)),
                "purpose": purpose,
            }
        )
        seen_combinations[combo] = bundle_id

    add("B-INTEGRATED-GRACEFUL-MEDIUM", {}, ["INTEGRATED", "BASELINE"], "Recommendation-eligible baseline composition")
    add("B-INTEGRATED-ABRUPT-CONTROL", {"UNCERTAINTY_RESPONSE": "U-ABRUPT-CUTOFF-CONTROL", "DAILY_BOUNDING": "D-COMBINED-HARD-6-CONTROL"}, ["INTEGRATED", "UNCERTAINTY", "DAILY", "CONTROL"], "Integrated expected-fail abrupt and combined-cap control")
    add("B-INTEGRATED-STEPPED", {"UNCERTAINTY_RESPONSE": "U-FIXED-STEPPED-TAPER"}, ["INTEGRATED", "UNCERTAINTY"], "Integrated stepped taper composition")
    add("B-INTEGRATED-GRACEFUL-HIGH", {"CROSS_DOMAIN_CONVERSION": "X-LEARN-LEANING-0_8-1_2", "DAILY_BOUNDING": "D-PER-DOMAIN-SQRT-HIGH"}, ["INTEGRATED", "CROSS_DOMAIN", "DAILY", "XDOMAIN_DAILY"], "High-scale Learn-leaning sensitivity composition")

    for candidate in candidates:
        dimension = str(candidate["dimension_id"])
        candidate_id = str(candidate["candidate_id"])
        add(
            "B-ISO-" + candidate_id,
            {dimension: candidate_id},
            [dimension.replace("_", "-"), {
                "CROSS_DOMAIN_CONVERSION": "CROSS_DOMAIN",
                "UNCERTAINTY_RESPONSE": "UNCERTAINTY",
                "DAILY_BOUNDING": "DAILY",
                "PRODUCTIVE_DAY": "PRODUCTIVE",
                "LEVEL_CURVE": "LEVEL",
                "STREAK_PLANNED_REST": "STREAK",
                "MOMENTUM": "MOMENTUM",
                "RECOVERY": "RECOVERY",
            }[dimension]],
            f"Isolated {dimension} contrast for {candidate_id}",
        )

    conversions = [c["candidate_id"] for c in candidates if c["dimension_id"] == "CROSS_DOMAIN_CONVERSION"]
    daily = [c["candidate_id"] for c in candidates if c["dimension_id"] == "DAILY_BOUNDING"]
    productive = [c["candidate_id"] for c in candidates if c["dimension_id"] == "PRODUCTIVE_DAY"]
    levels = [c["candidate_id"] for c in candidates if c["dimension_id"] == "LEVEL_CURVE"]
    for conversion in conversions:
        for daily_id in daily:
            add(
                f"B-PAIR-XD-{conversion}-{daily_id}",
                {"CROSS_DOMAIN_CONVERSION": str(conversion), "DAILY_BOUNDING": str(daily_id)},
                ["CROSS_DOMAIN", "DAILY", "XDOMAIN_DAILY"],
                "Isolated NORMALIZATION_X_DAILY_BOUNDING / DAILY_BOUNDING_X_CROSS_DOMAIN_CONVERSION pair",
            )
        for productive_id in productive:
            add(
                f"B-PAIR-XP-{conversion}-{productive_id}",
                {"CROSS_DOMAIN_CONVERSION": str(conversion), "PRODUCTIVE_DAY": str(productive_id)},
                ["CROSS_DOMAIN", "PRODUCTIVE", "XDOMAIN_PRODUCTIVE"],
                "Isolated NORMALIZATION_X_PRODUCTIVE_DAY pair",
            )
        for level_id in levels:
            add(
                f"B-PAIR-XL-{conversion}-{level_id}",
                {"CROSS_DOMAIN_CONVERSION": str(conversion), "LEVEL_CURVE": str(level_id)},
                ["CROSS_DOMAIN", "LEVEL", "XDOMAIN_LEVEL"],
                "Isolated NORMALIZATION_X_LEVEL_CURVE pair",
            )
    return bundles


def _hard_gates() -> list[dict[str, Any]]:
    definitions = [
        ("HG-CREATE-EXCLUDED", [], "CREATE_DOMAIN is absent and rejected", "ASSERT_CREATE_EXCLUDED", {}),
        ("HG-REVIEW-AXIS-PRESERVED", [], "Both Review members are evaluated separately with no default or averaging", "ASSERT_REVIEW_AXIS_SEPARATE", {}),
        ("HG-LEARN-LIMITATION-PRESERVED", [], "Learn candidate, status and identity limitation remain exact", "ASSERT_LEARN_LIMITATION", {}),
        ("HG-VERIFIED-BASE-PRESERVED", ["M-VERIFIED-BASE-PRESERVATION"], "absolute delta <= 1e-12", "ABS_LTE", {"threshold": EPSILON}),
        ("HG-HONEST-AGAIN-NOT-PUNISHED", [], "eligible AttemptCredit remains preserved", "ASSERT_HONEST_AGAIN_PRESERVED", {}),
        ("HG-NO-NEGATIVE-XP", [], "all contribution and cumulative values >= 0", "ASSERT_ALL_NONNEGATIVE", {}),
        ("HG-NO-LEVEL-LOSS", [], "level and cumulative progression never decrease", "ASSERT_MONOTONIC_NONDECREASING", {}),
        ("HG-NO-SESSION-SPLIT-GAIN", ["M-SESSION-SPLIT-DELTA"], "absolute delta <= 1e-12", "ABS_LTE", {"threshold": EPSILON}),
        ("HG-NO-BACKLOG-SIZE-GAIN", ["M-EXPLOIT-ADVANTAGE"], "backlog-only delta <= 1e-12", "LTE", {"threshold": EPSILON}),
        ("HG-NO-NEW-MATERIAL-FLOOD-GAIN", ["M-EXPLOIT-ADVANTAGE"], "exposure-only delta <= 1e-12", "LTE", {"threshold": EPSILON}),
        ("HG-NO-CONFIGURATION-GAIN", ["M-EXPLOIT-ADVANTAGE"], "configuration-only delta <= 1e-12", "LTE", {"threshold": EPSILON}),
        ("HG-NO-TIMEZONE-CLOCK-GAIN", ["M-EXPLOIT-ADVANTAGE"], "clock-only delta <= 1e-12", "LTE", {"threshold": EPSILON}),
        ("HG-PLANNED-REST-NEUTRAL", ["M-PLANNED-REST-DELTA"], "equals [0,0,0,0]", "VECTOR_EQUALS", {"expected": [0.0, 0.0, 0.0, 0.0]}),
        ("HG-STREAK-NO-XP-MULTIPLIER", [], "streak state never enters contribution formula", "ASSERT_STATE_NOT_IN_CONTRIBUTION", {"state": "STREAK"}),
        ("HG-MOMENTUM-NO-XP-MULTIPLIER", [], "Momentum state never enters contribution formula", "ASSERT_STATE_NOT_IN_CONTRIBUTION", {"state": "MOMENTUM"}),
        ("HG-MOMENTUM-NO-SNOWBALL", ["M-MOMENTUM-SNOWBALL-DELTA"], "delta <= 1e-12", "LTE", {"threshold": EPSILON}),
        ("HG-RECOVERY-NO-BONUS-LOOP", ["M-RECOVERY-LOOP-DELTA"], "delta <= 1e-12", "LTE", {"threshold": EPSILON}),
        ("HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED", ["M-FALSE-POSITIVE-CONTEXT-LOSS"], "recommendation-eligible contextual loss ratio <= 0.25", "LTE", {"threshold": 0.25}),
        ("HG-FALSE-POSITIVE-CUMULATIVE-HARM-BOUNDED", ["M-FALSE-POSITIVE-CUMULATIVE-LOSS"], "recommendation-eligible cumulative legitimate loss ratio <= 0.20", "LTE", {"threshold": 0.20}),
        ("HG-NO-CROSS-DOMAIN-CROWDOUT", ["M-DOMAIN-CROWDOUT"], "eligible added domain contribution below its own boundary has positive marginal total", "EQUALS", {"expected": 0.0}),
        ("HG-CROSS-DOMAIN-DECOMPOSITION-PRESERVED", ["M-DOMAIN-SHARE"], "Review and Learn components remain separately emitted", "ASSERT_COMPONENTS_EMITTED", {"components": ["REVIEW_DOMAIN", "LEARN_DOMAIN"]}),
        ("HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED", ["M-REVIEW-MARGINAL-CONTRIBUTION", "M-LEARN-MARGINAL-CONTRIBUTION"], "both Review and Learn marginal metrics are > 0 below own boundaries", "ALL_GT", {"threshold": 0.0}),
        ("HG-DAILY-LOW-VOLUME-PRESERVED", ["M-LOW-VOLUME-PRESERVATION"], "ratio == 1 within frozen onset", "ABS_DELTA_LTE", {"target": 1.0, "threshold": EPSILON}),
        ("HG-DAILY-NORMAL-INTENSIVE-DIFFERENTIABLE", ["M-NORMAL-INTENSIVE-SEPARATION"], "normal and intensive legitimate workloads remain strictly distinguishable", "GT", {"threshold": 0.0}),
        ("HG-EXTREME-VOLUME-BOUNDED", ["M-EXTREME-VOLUME-COMPRESSION"], "extreme output is finite and does not exceed exact per-domain output caps", "ASSERT_FINITE_AND_CAPPED", {"review_output_cap": 34.0, "learn_output_cap": 10.0}),
        ("HG-DETERMINISTIC-REPLAY", [], "forward and reverse typed replay identities are deterministic", "ASSERT_REPLAY_EQUAL", {}),
        ("HG-DECOMPOSABLE-EXPLANATION", ["M-EXPLANATION-DECOMPOSABILITY"], "ratio == 1", "ABS_DELTA_LTE", {"target": 1.0, "threshold": EPSILON}),
        ("HG-NO-REAL-USER-DATA", [], "all traces are synthetic", "ASSERT_SYNTHETIC_ONLY", {}),
        ("HG-RESEARCH-ONLY", [], "all candidates and outputs are RESEARCH_ONLY", "ASSERT_RESEARCH_ONLY", {}),
        ("HG-NO-PRODUCTION-APPROVAL", [], "production flags remain false", "ASSERT_PRODUCTION_FALSE", {}),
    ]
    return [
        {
            "gate_id": gate_id,
            "required_metric_ids": metric_ids,
            "predicate": predicate,
            "predicate_ast": _typed_ast(op, **parameters),
            "non_compensable": True,
            "missing_behavior": "FAIL_CLOSED",
        }
        for gate_id, metric_ids, predicate, op, parameters in definitions
    ]


def _metrics() -> list[dict[str, Any]]:
    definitions = [
        ("M-FALSE-POSITIVE-CONTEXT-LOSS", "lost_positive_context / max(matched_positive_context, epsilon)", "MINIMIZE", "<= 0.25 recommendation eligible"),
        ("M-FALSE-POSITIVE-TOTAL-IMMEDIATE-LOSS", "lost_total_contribution / max(matched_total_contribution, epsilon)", "OBSERVE", "NONE"),
        ("M-FALSE-POSITIVE-CUMULATIVE-LOSS", "sum(normal_path-candidate_path)/max(sum(normal_path),epsilon)", "MINIMIZE", "<= 0.20 recommendation eligible"),
        ("M-TIME-TO-RECOVERY", "normal evidence-bearing days until NORMAL and multiplier 1.0", "MINIMIZE", "<= 4"),
        ("M-VERIFIED-BASE-PRESERVATION", "max(abs(verified_base_state-verified_base_normal))", "TARGET_ZERO", "<= 1e-12"),
        ("M-EXPLOIT-ADVANTAGE", "exploit_total-matched_legitimate_total", "MINIMIZE", "<= 1e-12"),
        ("M-SESSION-SPLIT-DELTA", "split_total-unsplit_total", "TARGET_ZERO", "ABS <= 1e-12"),
        ("M-PLANNED-REST-DELTA", "tuple(xp,streak_growth,streak_break,debt)", "TARGET_ZERO", "[0,0,0,0]"),
        ("M-RECOVERY-LOOP-DELTA", "absence_return_total-always_normal_total", "MINIMIZE", "<= 1e-12"),
        ("M-MOMENTUM-SNOWBALL-DELTA", "momentum_only_progression_delta", "TARGET_ZERO", "<= 1e-12"),
        ("M-REVIEW-MARGINAL-CONTRIBUTION", "total(review+delta,learn)-total(review,learn)", "MAXIMIZE", "> 0 below Review boundary"),
        ("M-LEARN-MARGINAL-CONTRIBUTION", "total(review,learn+delta)-total(review,learn)", "MAXIMIZE", "> 0 below Learn boundary"),
        ("M-DOMAIN-CROWDOUT", "count of eligible positive source deltas with non-positive total marginal", "TARGET_ZERO", "0 recommendation eligible"),
        ("M-DOMAIN-SHARE", "domain_component/max(total,epsilon)", "DESCRIPTIVE", "NONE"),
        ("M-CROSS-DOMAIN-SENSITIVITY", "candidate_total-equalized_total on matched trace", "DESCRIPTIVE", "NONE"),
        ("M-LOW-VOLUME-PRESERVATION", "bounded_domain/precompression_domain below onset", "TARGET_ONE", "ABS-1 <= 1e-12"),
        ("M-NORMAL-INTENSIVE-SEPARATION", "intensive_bounded-normal_bounded", "MAXIMIZE", "> 0"),
        ("M-INTENSIVE-DAY-PRESERVATION", "bounded_total/max(precompression_total,epsilon)", "MAXIMIZE", "> 0"),
        ("M-EXTREME-VOLUME-COMPRESSION", "bounded_total/max(precompression_total,epsilon)", "MINIMIZE", "< 1 and finite"),
        ("M-LEVEL-SCALE-SENSITIVITY", "level(candidate_scale)-level(baseline_scale)", "DESCRIPTIVE", "NONE"),
        ("M-EXPLANATION-DECOMPOSABILITY", "explained_value/max(total_value,epsilon)", "TARGET_ONE", "ABS-1 <= 1e-12"),
        ("M-POLICY-COMPLEXITY", "named states + predicates + numeric parameters", "MINIMIZE", "<= 32 recommendation eligible"),
    ]
    return [
        {
            "metric_id": metric_id,
            "formula": formula,
            "formula_ast": _typed_ast("BUILTIN_METRIC_V1", builtin_id=metric_id),
            "direction": direction,
            "threshold": threshold,
            "missing_behavior": "FAIL_CLOSED",
        }
        for metric_id, formula, direction, threshold in definitions
    ]


def _hypotheses() -> list[dict[str, str]]:
    definitions = [
        ("H-FP-CONTEXT", "Abrupt contextual cutoff fails the contextual false-positive gate while graceful candidates pass."),
        ("H-FP-TOTAL", "Total immediate loss remains separately observable and does not replace contextual harm."),
        ("H-BASE", "Verified base remains invariant under uncertainty."),
        ("H-RECOVERY", "Normal evidence restores confidence without bonus or debt."),
        ("H-XDOMAIN-MARGINAL", "Each eligible domain has positive marginal contribution below its own boundary."),
        ("H-XDOMAIN-DECOMPOSE", "Review and Learn contributions remain decomposable after conversion."),
        ("H-XDOMAIN-SENSITIVITY", "Equalized, Learn-leaning and Review-leaning mappings produce prospectively distinguishable sensitivity."),
        ("H-DAILY-LOW", "Low legitimate volume is preserved."),
        ("H-DAILY-NORMAL", "Normal legitimate workloads remain distinguishable."),
        ("H-DAILY-INTENSIVE", "Intensive legitimate workloads remain positive and do not immediately saturate."),
        ("H-DAILY-EXTREME", "Extreme synthetic volume is compressed and bounded."),
        ("H-SESSION", "Session splitting is neutral."),
        ("H-PRODUCTIVE", "Productive-day classification uses bounded evidence rather than raw activity."),
        ("H-LEVEL", "Level mapping consumes NPU and remains monotonic under frozen daily scales."),
        ("H-REST", "Planned rest is neutral and distinct from productive day."),
        ("H-MOMENTUM", "Momentum is an indicator and cannot recursively multiply progression."),
        ("H-RECOVERY-LOOP", "Recovery state cannot create a return bonus loop."),
        ("H-PIPELINE", "Typed operator order is deterministic and component-wise."),
        ("H-REPLAY", "Forward/reverse replay yields identical typed identities."),
        ("H-EXPLAIN", "Every contribution and transition is source/component decomposable."),
    ]
    return [{"hypothesis_id": hypothesis_id, "statement": statement} for hypothesis_id, statement in definitions]


def _pipeline_steps() -> list[dict[str, Any]]:
    raw = [
        ("S01-SOURCE-VALIDATION", "SOURCE_RECORD_BATCH", "VALIDATED_SOURCE_RECORD_BATCH", "NONE", "BEFORE", "NONE", "FAIL_CLOSED_INVALID_SOURCE", ["RC-SOURCE-VALID", "RC-SOURCE-REJECTED"]),
        ("S02-SOURCE-MODEL-TRANSITION", "VALIDATED_SOURCE_RECORD_BATCH", "SOURCE_TRANSITION_BATCH", "REVIEW_MODEL_AXIS_V1", "BEFORE", "AFTER", "FAIL_CLOSED_SOURCE_MODEL", ["RC-REVIEW-STEP", "RC-REVIEW-TAPER", "RC-LEARN-CONFIRMATION"]),
        ("S03-DECOMPOSE-BASE-CONTEXT", "SOURCE_TRANSITION_BATCH", "COMPONENT_BATCH", "NONE", "BEFORE", "NONE", "FAIL_CLOSED_DECOMPOSITION", ["RC-VERIFIED-BASE", "RC-POSITIVE-CONTEXT", "RC-NEGATIVE-CONTEXT"]),
        ("S04-READ-UNCERTAINTY-STATE", "COMPONENT_BATCH", "COMPONENT_WITH_STATE_BATCH", "UNCERTAINTY_RESPONSE", "BEFORE", "NONE", "MISSING_EVIDENCE_HOLDS_STATE", ["RC-UNCERTAINTY-STATE-READ"]),
        ("S05-APPLY-UNCERTAINTY", "COMPONENT_WITH_STATE_BATCH", "TAPERED_COMPONENT_BATCH", "UNCERTAINTY_RESPONSE", "BEFORE", "AFTER", "FAIL_CLOSED_POSITIVE_CONTEXT_ONLY", ["RC-CONTEXT-TAPERED", "RC-VERIFIED-BASE-UNCHANGED"]),
        ("S06-DOMAIN-NORMALIZATION", "TAPERED_COMPONENT_BATCH", "NORMALIZED_COMPONENT_BATCH", "CROSS_DOMAIN_CONVERSION", "BEFORE", "NONE", "FAIL_CLOSED_NORMALIZATION", ["RC-COMPONENTWISE-NORMALIZED"]),
        ("S07-PER-DOMAIN-AGGREGATION", "NORMALIZED_COMPONENT_BATCH", "DOMAIN_DAILY_PREBOUND", "NONE", "BEFORE", "NONE", "FAIL_CLOSED_DOMAIN_AGGREGATION", ["RC-REVIEW-AGGREGATED", "RC-LEARN-AGGREGATED"]),
        ("S08-PER-DOMAIN-DAILY-BOUNDING", "DOMAIN_DAILY_PREBOUND", "DOMAIN_DAILY_BOUNDED", "DAILY_BOUNDING", "BEFORE", "NONE", "FAIL_CLOSED_DAILY_BOUNDING", ["RC-REVIEW-BOUNDED", "RC-LEARN-BOUNDED"]),
        ("S09-CROSS-DOMAIN-CONVERSION", "DOMAIN_DAILY_BOUNDED", "WEIGHTED_DOMAIN_CONTRIBUTION", "CROSS_DOMAIN_CONVERSION", "BEFORE", "NONE", "FAIL_CLOSED_CONVERSION", ["RC-REVIEW-WEIGHTED", "RC-LEARN-WEIGHTED"]),
        ("S10-OPTIONAL-GLOBAL-ENVELOPE", "WEIGHTED_DOMAIN_CONTRIBUTION", "FINAL_DAILY_CONTRIBUTION", "DAILY_BOUNDING", "BEFORE", "NONE", "NO_GLOBAL_ENVELOPE_FOR_RECOMMENDATION_CANDIDATES", ["RC-NO-GLOBAL-ENVELOPE", "RC-CONTROL-GLOBAL-CAP"]),
        ("S11-PRODUCTIVE-DAY", "FINAL_DAILY_CONTRIBUTION", "PRODUCTIVE_DAY_CLASSIFICATION", "PRODUCTIVE_DAY", "BEFORE", "NONE", "FAIL_CLOSED_CLASSIFICATION", ["RC-PRODUCTIVE", "RC-NONPRODUCTIVE", "RC-PLANNED-REST"]),
        ("S12-STREAK-REST", "PRODUCTIVE_DAY_CLASSIFICATION", "STREAK_STATE", "STREAK_PLANNED_REST", "BEFORE", "AFTER", "FAIL_CLOSED_STREAK", ["RC-STREAK-GROW", "RC-STREAK-PRESERVE", "RC-STREAK-RESET"]),
        ("S13-MOMENTUM", "PRODUCTIVE_DAY_CLASSIFICATION", "MOMENTUM_STATE", "MOMENTUM", "BEFORE", "AFTER", "FAIL_CLOSED_MOMENTUM", ["RC-MOMENTUM-UPDATE", "RC-MOMENTUM-REST-HOLD"]),
        ("S14-RECOVERY", "PRODUCTIVE_DAY_CLASSIFICATION", "RECOVERY_STATE", "RECOVERY", "BEFORE", "AFTER", "FAIL_CLOSED_RECOVERY", ["RC-RECOVERY-UPDATE"]),
        ("S15-CUMULATIVE-PROGRESSION", "FINAL_DAILY_CONTRIBUTION", "CUMULATIVE_NPU", "NONE", "BEFORE", "AFTER", "FAIL_CLOSED_ACCUMULATION", ["RC-NPU-ACCUMULATED"]),
        ("S16-LEVEL-MAPPING", "CUMULATIVE_NPU", "LEVEL_STATE", "LEVEL_CURVE", "BEFORE", "NONE", "FAIL_CLOSED_LEVEL", ["RC-LEVEL-MAPPED"]),
        ("S17-EXPLANATION-EMISSION", "ALL_INTERMEDIATE_RECORDS", "EXPLANATION_RECORD", "NONE", "AFTER", "NONE", "FAIL_CLOSED_EXPLANATION", ["RC-EXPLANATION-COMPLETE"]),
    ]
    return [
        {
            "ordinal": index,
            "step_id": step_id,
            "input_type": input_type,
            "output_type": output_type,
            "candidate_dimension": dimension,
            "rounding": {"mode": "ROUND_HALF_EVEN", "decimal_places": ROUNDING_DECIMALS, "apply_at": "STEP_OUTPUT"},
            "state_read_timing": read_timing,
            "state_write_timing": write_timing,
            "missing_data_behavior": missing,
            "fail_closed_reason": missing,
            "reason_codes": reason_codes,
        }
        for index, (step_id, input_type, output_type, dimension, read_timing, write_timing, missing, reason_codes) in enumerate(raw, start=1)
    ]


def build_pipeline() -> dict[str, Any]:
    pipeline = {
        "$schema": "../schemas/core-economy-evaluation-pipeline-v4.schema.json",
        "identity": {
            "artifact_id": "core-economy-evaluation-pipeline",
            "version": PIPELINE_VERSION,
            "status": "FROZEN_PRE_SCREENING",
            "artifact_digest": "PENDING",
            "digest_scope": "CANONICAL_ARTIFACT_EXCLUDING_IDENTITY_DIGEST",
            "validator_version": VALIDATOR_VERSION,
            "generator_version": GENERATOR_VERSION,
        },
        "operator_order_resolution": {
            "selected": "NORMALIZE_COMPONENTS_SEPARATELY_AFTER_UNCERTAINTY",
            "selected_expression": "normalize(verified_base) + normalize(taper(positive_context)) + normalize(negative_context)",
            "prohibited_expression": "normalize(verified_base + positive_context) then taper normalized aggregate",
            "nonlinear_reference_operator": "log1p(3*x)/log1p(3*anchor)",
            "rationale": "Uncertainty may affect only positive context; aggregate-first nonlinear normalization would leak taper into verified base.",
        },
        "numeric_policy": {
            "epsilon": EPSILON,
            "rounding_mode": "ROUND_HALF_EVEN",
            "decimal_places": ROUNDING_DECIMALS,
            "nonfinite": "REJECT",
            "negative_contribution": "REJECT",
        },
        "steps": _pipeline_steps(),
        "state_policy": {
            "read_before_transition": True,
            "write_after_step": True,
            "past_progression_mutation": False,
            "level_loss_allowed": False,
            "xp_debt_allowed": False,
        },
        "uncertainty_state_machine": {
            "initial_state": "NORMAL",
            "states": list(UNCERTAINTY_STATES),
            "signals": list(UNCERTAINTY_SIGNALS),
            "affected_component": "POSITIVE_CONTEXT",
            "unaffected_components": ["VERIFIED_BASE", "NEGATIVE_CONTEXT"],
            "transition_table": _uncertainty_transition_table(),
            "evidence_window": {
                "kind": "TRAILING_EVENT_COUNT",
                "size": 3,
                "invalid_signal_behavior": "REJECT",
                "missing_signal_behavior": "HOLD_CURRENT_STATE_AND_USE_CURRENT_STATE_MULTIPLIER",
            },
            "past_progression_mutation": False,
            "debt_allowed": False,
            "bonus_multiplier_allowed": False,
        },
        "production_flags": {
            "screening_executed": False,
            "simulation_started": False,
            "g4_4_started": False,
            "production_approved": False,
            "production_integration": False,
        },
    }
    return _finalize_digest(pipeline)


def _reason_code_registry(pipeline: Mapping[str, Any]) -> list[str]:
    codes = {
        str(code)
        for step in pipeline["steps"]
        for code in step["reason_codes"]
    }
    codes.update(str(row["reason_code"]) for row in _uncertainty_transition_table())
    codes.update(
        {
            "RC-U-CONFLICT-WINDOW-HOLD",
            "RC-U-RECOVERY-HOLD",
            "RC-EXPECTED-PASS",
            "RC-EXPECTED-ABRUPT-CONTEXT-FAIL",
            "RC-EXPECTED-COMBINED-CROWDOUT-FAIL",
            "RC-EXPECTED-COMBINED-MARGINAL-FAIL",
            "RC-EXPECTED-COMBINED-SEPARATION-FAIL",
            "RC-EXPECTED-COMBINED-CAP-FAIL",
        }
    )
    return sorted(codes)


def build_protocol(
    *,
    pipeline: Mapping[str, Any] | None = None,
    pipeline_digest: str = "PENDING",
    scenario_digest: str = "PENDING",
    matrix_digest: str = "PENDING",
    scenario_count: int = 0,
    matrix_count: int = 0,
) -> dict[str, Any]:
    candidates = _candidate_registry()
    bundles = _bundle_registry(candidates)
    gates = _hard_gates()
    metrics = _metrics()
    protocol = {
        "$schema": "../schemas/core-economy-candidate-protocol-v4.schema.json",
        "identity": {
            "artifact_id": "core-economy-candidate-protocol",
            "version": PROTOCOL_VERSION,
            "status": "FROZEN_PRE_SCREENING",
            "stage": "G4.3_V4_REPLACEMENT_PRE_SCREENING_REPUBLICATION",
            "artifact_digest": "PENDING",
            "digest_scope": "CANONICAL_ARTIFACT_EXCLUDING_IDENTITY_DIGEST_AND_ARTIFACT_REGISTRY_DIGEST_VALUES",
            "validator_version": VALIDATOR_VERSION,
            "generator_version": GENERATOR_VERSION,
        },
        "supersession": {
            "supersedes_version": 3,
            "prior_versions": [
                {"version": 1, "status": "SUPERSEDED_PRE_EXECUTION", "results": "NOT_AVAILABLE"},
                {"version": 2, "status": "SUPERSEDED_PRE_EXECUTION", "results": "NOT_AVAILABLE"},
                {
                    "version": 3,
                    "status": "INVALIDATED_AFTER_SUBSTANTIVE_DEFECT",
                    "results": "INVALIDATED_NOT_DECISION_EVIDENCE",
                },
            ],
            "results_accessed_before_republication": True,
            "v1_artifacts_mutable": False,
            "v2_artifacts_mutable": False,
            "v3_artifacts_mutable": False,
            "invalidated_v3_result_set_digest": "7501d5f3248b468dec6d8c338ca019d0543400b7696eb77b24dbb042d2448612",
            "invalidated_v3_result_artifact_digest": "91fc19ddcde96e5a6699b53abedc1871d4b5b547ec292ecde23980e74d284208",
            "invalidated_v3_implementation_sha": "a0283a4945ab4201c0cda284f60b3c2ad7c118c4",
            "reason_codes": [
                "V3_GATE_REQUIRED_METRIC_NOT_ROW_LOCAL",
                "V3_EXPECTED_CONTROL_RULE_OVERBROAD",
                "V3_MARGINAL_PROBE_NOT_BELOW_COMBINED_BOUNDARY",
            ],
        },
        "governance": {
            "owner_principle": "GRACEFUL_DEGRADATION_OVER_ABRUPT_CUTOFF",
            "design": "CURATED_BOUNDED_FACTORIAL_DESIGN",
            "weighted_overall_score": False,
            "hard_gates_compensable": False,
            "screening": "NOT_STARTED",
            "simulation": "NOT_STARTED",
            "results": "NOT_AVAILABLE",
            "g4_4": "NEXT_NOT_STARTED",
            "production": "PROHIBITED",
            "g4_2_correction_method": "STALE_CLOSEOUT_IDENTITY_LEDGER_CORRECTION",
        },
        "source_contracts": {
            "g4_1": {"artifact_id": "core-economy-problem-contract", "version": 1, "status": "FROZEN_PRE_NORMALIZATION_ANALYSIS", "blob_sha": "dda1336328df7e79bc5ba1978a102faf5ca40e14"},
            "g4_2": {"artifact_id": "core-economy-input-normalization", "version": 1, "status": "FROZEN_PRE_CANDIDATE_FAMILY_DESIGN", "blob_sha": "0cf1bbb6f3f088d48b4c78bcc37145dacc8cebc5"},
            "review_reward": {
                "attempt_credit": 0.25,
                "outcome_credit": 0.65,
                "neutral_context_credit": 0.10,
                "ordinary_success": 1.0,
                "maximum_success": 1.32,
                "source_implementation": dict(G1_SOURCE_IDENTITIES),
            },
            "learn_reward": dict(G2_SOURCE_IDENTITIES),
        },
        "domain_registry": ["REVIEW_DOMAIN", "LEARN_DOMAIN"],
        "excluded_domains": ["CREATE_DOMAIN"],
        "review_axis": {
            "axis_id": "REVIEW_MODEL_AXIS_V1",
            "members": list(REVIEW_MEMBERS),
            "selection": "NONE",
            "default": "NONE",
            "winner": "NONE",
            "evaluation": "PARALLEL_SEPARATE",
            "averaging": "PROHIBITED",
            "source_transition": {
                "evaluator": "gamification_sim.review_candidate_mechanisms.memory_gain_multiplier",
                "retention_transition_day": 60,
                "boundary_days": [59, 60, 61, 75, 89, 90, 91],
                "source_component_scaled": "MEMORY_GAIN_POSITIVE_CONTEXT",
                "unscaled_components": ["VERIFIED_BASE", "NEGATIVE_CONTEXT"],
                "source_identities": dict(G1_SOURCE_IDENTITIES),
            },
        },
        "learn_input": {
            "candidate_id": LEARN_CANDIDATE,
            "status": "CONFIRMATORY_INCONCLUSIVE",
            "limitation": LEARN_LIMITATION,
            "source_unit": "LRU",
            "frozen_source_total": 1.0,
            "common_economy_xp": False,
        },
        "dimension_registry": [
            {"dimension_id": dimension, "candidate_count": sum(1 for c in candidates if c["dimension_id"] == dimension)}
            for dimension in REQUIRED_DIMENSIONS
        ],
        "candidate_registry": candidates,
        "candidate_bundles": bundles,
        "interaction_design": {
            "required_interactions": [
                "NORMALIZATION_X_DAILY_BOUNDING",
                "NORMALIZATION_X_PRODUCTIVE_DAY",
                "NORMALIZATION_X_LEVEL_CURVE",
                "DAILY_BOUNDING_X_CROSS_DOMAIN_CONVERSION",
                "DAILY_BOUNDING_X_DOMAIN_CROWDOUT",
            ],
            "omitted_combination_rationale": "Full Cartesian product is prohibited; exact pair coverage holds all non-paired dimensions at the baseline bundle values.",
            "attribution_limit": "Integrated bundles are end-to-end checks and are never the sole evidence for a pairwise attribution.",
        },
        "hypotheses": _hypotheses(),
        "hard_gates": gates,
        "metrics": metrics,
        "expected_outcome_rule": {
            "rule_id": "EXPECTED-OUTCOME-CANDIDATE-SCENARIO-GATE-V1",
            "source_of_truth": "MATRIX_ROW",
            "identity_fields": [
                "candidate_bundle_id",
                "scenario_id",
                "review_member",
                "replay_direction",
                "gate_id",
            ],
            "default": "PASS",
            "control_failure_requires_exact_predicate": True,
            "post_result_mutation": "PROHIBITED",
        },
        "reason_code_registry": _reason_code_registry(pipeline or build_pipeline()),
        "coverage_registry": {
            "personas": list(PERSONA_IDS),
            "threats": list(THREAT_IDS),
            "invariants": list(INVARIANT_IDS),
        },
        "artifact_registry": {
            "pipeline": {"path": str(PIPELINE_PATH), "version": PIPELINE_VERSION, "digest": pipeline_digest},
            "scenarios": {"path": str(SCENARIOS_PATH), "version": PROTOCOL_VERSION, "digest": scenario_digest, "count": scenario_count, "results": "NOT_AVAILABLE"},
            "matrix": {"path": str(MATRIX_PATH), "version": PROTOCOL_VERSION, "digest": matrix_digest, "count": matrix_count, "result_status": "NOT_RUN"},
            "negative_corpus": {"path": str(NEGATIVE_CORPUS_PATH), "version": PROTOCOL_VERSION, "digest": "COMPUTED_SEPARATELY"},
        },
        "production_flags": {
            "screening_implemented": False,
            "screening_executed": False,
            "simulation_started": False,
            "g4_4_started": False,
            "winner_selected": False,
            "review_default_selected": False,
            "production_approved": False,
            "production_integration": False,
            "real_user_data": False,
            "negative_xp_allowed": False,
            "level_loss_allowed": False,
            "xp_debt_allowed": False,
        },
    }
    return _finalize_digest(protocol)


def _event(sequence: int, *, review_units: float = 0.0, learn_lru: float = 0.0, verified_base: float = 0.0, positive_context: float = 0.0, uncertainty_signal: str = "NORMAL", planned_rest: bool = False, session_id: str = "S1", trace_role: str = "WORK", metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event_type": "SYNTHETIC_DOMAIN_CONTRIBUTION",
        "review_units": _round(review_units),
        "learn_lru": _round(learn_lru),
        "verified_base": _round(verified_base),
        "positive_context": _round(positive_context),
        "negative_context": 0.0,
        "uncertainty_signal": uncertainty_signal,
        "planned_rest": planned_rest,
        "session_id": session_id,
        "trace_role": trace_role,
        "metadata": dict(metadata or {}),
    }


def _workload_events(review_count: int, learn_count: int, *, session_split: bool = False) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    sequence = 1
    for index in range(review_count):
        session = "S1" if not session_split or index % 2 == 0 else "S2"
        events.append(_event(sequence, review_units=1.0, verified_base=1.0, session_id=session))
        sequence += 1
    for index in range(learn_count):
        session = "S1" if not session_split or index % 2 == 0 else "S2"
        events.append(_event(sequence, learn_lru=1.0, session_id=session))
        sequence += 1
    return events


def _scenario(
    scenario_id: str,
    category: str,
    persona_id: str,
    description: str,
    events: Sequence[Mapping[str, Any]],
    *,
    bundle_tags: Sequence[str],
    gates: Sequence[str],
    metrics: Sequence[str],
    threats: Sequence[str],
    invariants: Sequence[str],
    review_pair_required: bool = True,
    replay: Sequence[str] = ("FORWARD",),
    trace_parameters: Mapping[str, Any] | None = None,
    expected_validation_disposition: str = "VALID",
) -> dict[str, Any]:
    metric_hypotheses = {
        "M-FALSE-POSITIVE-CONTEXT-LOSS": "H-FP-CONTEXT",
        "M-FALSE-POSITIVE-TOTAL-IMMEDIATE-LOSS": "H-FP-TOTAL",
        "M-FALSE-POSITIVE-CUMULATIVE-LOSS": "H-RECOVERY",
        "M-TIME-TO-RECOVERY": "H-RECOVERY",
        "M-VERIFIED-BASE-PRESERVATION": "H-BASE",
        "M-SESSION-SPLIT-DELTA": "H-SESSION",
        "M-RECOVERY-LOOP-DELTA": "H-RECOVERY-LOOP",
        "M-MOMENTUM-SNOWBALL-DELTA": "H-MOMENTUM",
        "M-REVIEW-MARGINAL-CONTRIBUTION": "H-XDOMAIN-MARGINAL",
        "M-LEARN-MARGINAL-CONTRIBUTION": "H-XDOMAIN-MARGINAL",
        "M-DOMAIN-CROWDOUT": "H-XDOMAIN-MARGINAL",
        "M-DOMAIN-SHARE": "H-XDOMAIN-DECOMPOSE",
        "M-CROSS-DOMAIN-SENSITIVITY": "H-XDOMAIN-SENSITIVITY",
        "M-LOW-VOLUME-PRESERVATION": "H-DAILY-LOW",
        "M-NORMAL-INTENSIVE-SEPARATION": "H-DAILY-NORMAL",
        "M-INTENSIVE-DAY-PRESERVATION": "H-DAILY-INTENSIVE",
        "M-EXTREME-VOLUME-COMPRESSION": "H-DAILY-EXTREME",
        "M-LEVEL-SCALE-SENSITIVITY": "H-LEVEL",
        "M-EXPLANATION-DECOMPOSABILITY": "H-EXPLAIN",
    }
    hypothesis_ids = {
        metric_hypotheses[metric_id]
        for metric_id in metrics
        if metric_id in metric_hypotheses
    }
    if category == "PRODUCTIVE":
        hypothesis_ids.add("H-PRODUCTIVE")
    if category == "PIPELINE":
        hypothesis_ids.add("H-PIPELINE")
    if "HG-PLANNED-REST-NEUTRAL" in gates:
        hypothesis_ids.add("H-REST")
    if "HG-DETERMINISTIC-REPLAY" in gates:
        hypothesis_ids.add("H-REPLAY")
    return {
        "scenario_id": scenario_id,
        "category": category,
        "persona_id": persona_id,
        "description": description,
        "synthetic_only": True,
        "real_user_data": False,
        "ordered_inputs": [dict(event) for event in events],
        "trace_parameters": dict(trace_parameters or {}),
        "axis_mapping": {
            "review_pair_required": review_pair_required,
            "review_members": list(REVIEW_MEMBERS) if review_pair_required else [],
            "learn_candidate_id": LEARN_CANDIDATE,
            "session_axis": "SESSION",
            "anki_day_axis": "ANKI_DAY",
            "calendar_day_axis": "CALENDAR_DAY",
        },
        "applicable_bundle_tags": sorted(set(bundle_tags) | {"INTEGRATED"}),
        "applicable_gate_ids": sorted(set(gates)),
        "metric_ids": sorted(set(metrics)),
        "hypothesis_ids": sorted(hypothesis_ids),
        "replay_directions": list(replay),
        "threat_ids": sorted(set(threats)),
        "invariant_ids": sorted(set(invariants)),
        "expected_validation_disposition": expected_validation_disposition,
        "result_status": "NOT_AVAILABLE",
    }


def build_scenarios(protocol_digest: str, pipeline_digest: str) -> dict[str, Any]:
    fp_gates = ["HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED", "HG-VERIFIED-BASE-PRESERVED", "HG-DECOMPOSABLE-EXPLANATION", "HG-RESEARCH-ONLY"]
    fp_metrics = ["M-FALSE-POSITIVE-CONTEXT-LOSS", "M-FALSE-POSITIVE-TOTAL-IMMEDIATE-LOSS", "M-VERIFIED-BASE-PRESERVATION", "M-EXPLANATION-DECOMPOSABILITY"]
    x_gates = ["HG-NO-CROSS-DOMAIN-CROWDOUT", "HG-CROSS-DOMAIN-DECOMPOSITION-PRESERVED", "HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED", "HG-RESEARCH-ONLY"]
    x_metrics = ["M-REVIEW-MARGINAL-CONTRIBUTION", "M-LEARN-MARGINAL-CONTRIBUTION", "M-DOMAIN-CROWDOUT", "M-DOMAIN-SHARE", "M-CROSS-DOMAIN-SENSITIVITY"]
    daily_gates = ["HG-DAILY-LOW-VOLUME-PRESERVED", "HG-DAILY-NORMAL-INTENSIVE-DIFFERENTIABLE", "HG-EXTREME-VOLUME-BOUNDED", "HG-NO-SESSION-SPLIT-GAIN"]
    daily_metrics = [
        "M-LOW-VOLUME-PRESERVATION",
        "M-NORMAL-INTENSIVE-SEPARATION",
        "M-INTENSIVE-DAY-PRESERVATION",
        "M-EXTREME-VOLUME-COMPRESSION",
        "M-SESSION-SPLIT-DELTA",
    ]
    scenarios: list[dict[str, Any]] = []

    fp_specs = [
        ("SC-FP-ISOLATED-ANOMALY", 1.08, 0.12, "isolated anomaly at ordinary context"),
        ("SC-FP-MAX-CONTEXT-ANOMALY", 1.0, 0.32, "maximum-context anomaly at 1.32 Review Unit boundary"),
        ("SC-FP-ZERO-CONTEXT-DENOMINATOR", 1.0, 0.0, "zero positive-context denominator edge"),
    ]
    for index, (scenario_id, base, context, description) in enumerate(fp_specs):
        scenarios.append(_scenario(
            scenario_id, "FALSE_POSITIVE", PERSONA_IDS[index], description,
            [_event(1, review_units=base + context, verified_base=base, positive_context=context, trace_role="NORMAL_REFERENCE"), _event(2, review_units=base, verified_base=base, positive_context=context, uncertainty_signal="ISOLATED_ANOMALY", trace_role="ANOMALY")],
            bundle_tags=["UNCERTAINTY"], gates=fp_gates, metrics=fp_metrics,
            threats=["UNCERTAINTY_COLLAPSE", "ANSWER_BEHAVIOR_FARMING"],
            invariants=["INV-HONEST-AGAIN-NOT-PUNISHED", "INV-EXPLAINABLE-CONTRIBUTIONS", "INV-DECOMPOSABLE-EVIDENCE"],
            replay=("FORWARD", "REVERSE"),
            trace_parameters={"matched_verified_base": base, "matched_positive_context": context, "matched_total": base + context},
        ))
    scenarios.append(_scenario(
        "SC-FP-RECOVERY", "FALSE_POSITIVE", PERSONA_IDS[3], "isolated anomaly followed by four normal evidence-bearing days",
        [_event(1, review_units=1.2, verified_base=1.08, positive_context=0.12, uncertainty_signal="ISOLATED_ANOMALY"), *[_event(i, review_units=1.2, verified_base=1.08, positive_context=0.12, uncertainty_signal="NORMAL") for i in range(2, 6)]],
        bundle_tags=["UNCERTAINTY", "RECOVERY"], gates=fp_gates + ["HG-FALSE-POSITIVE-CUMULATIVE-HARM-BOUNDED", "HG-RECOVERY-NO-BONUS-LOOP"], metrics=fp_metrics + ["M-FALSE-POSITIVE-CUMULATIVE-LOSS", "M-TIME-TO-RECOVERY", "M-RECOVERY-LOOP-DELTA"],
        threats=["UNCERTAINTY_COLLAPSE", "RECOVERY_BONUS_LOOP"], invariants=["INV-HONEST-AGAIN-NOT-PUNISHED", "INV-RECOVERY-NO-BONUS-LOOP"], replay=("FORWARD", "REVERSE"),
    ))
    scenarios.append(_scenario(
        "SC-FP-REPEATED-CONFLICT", "FALSE_POSITIVE", PERSONA_IDS[8], "repeated conflicting evidence may reach stronger restriction",
        [_event(i, review_units=1.2, verified_base=1.08, positive_context=0.12, uncertainty_signal="CONFLICT") for i in range(1, 5)],
        bundle_tags=["UNCERTAINTY"], gates=fp_gates + ["HG-FALSE-POSITIVE-CUMULATIVE-HARM-BOUNDED"], metrics=fp_metrics + ["M-FALSE-POSITIVE-CUMULATIVE-LOSS", "M-POLICY-COMPLEXITY"],
        threats=["EXPLANATION_OPACITY", "UNCERTAINTY_COLLAPSE"], invariants=["INV-EXPLAINABLE-CONTRIBUTIONS", "INV-DECOMPOSABLE-EVIDENCE"], replay=("FORWARD", "REVERSE"),
    ))
    scenarios.append(_scenario(
        "SC-FP-MULTIDAY-LEGITIMATE", "FALSE_POSITIVE", PERSONA_IDS[4], "five matched legitimate normal-evidence days",
        [_event(i, review_units=1.2, verified_base=1.08, positive_context=0.12, uncertainty_signal="NORMAL") for i in range(1, 6)],
        bundle_tags=["UNCERTAINTY"], gates=fp_gates + ["HG-FALSE-POSITIVE-CUMULATIVE-HARM-BOUNDED"], metrics=fp_metrics + ["M-FALSE-POSITIVE-CUMULATIVE-LOSS"],
        threats=["UNCERTAINTY_COLLAPSE"], invariants=["INV-HONEST-AGAIN-NOT-PUNISHED", "INV-DETERMINISTIC-REPLAY"], replay=("FORWARD", "REVERSE"),
    ))
    scenarios.append(_scenario(
        "SC-PIPELINE-NONLINEAR-ORDER", "PIPELINE", PERSONA_IDS[8], "component-wise normalization order distinguishes aggregate-first nonlinear behavior",
        [_event(1, review_units=1.32, verified_base=1.0, positive_context=0.32, uncertainty_signal="ISOLATED_ANOMALY")],
        bundle_tags=["UNCERTAINTY", "CROSS_DOMAIN"], gates=["HG-VERIFIED-BASE-PRESERVED", "HG-DETERMINISTIC-REPLAY", "HG-DECOMPOSABLE-EXPLANATION"], metrics=["M-VERIFIED-BASE-PRESERVATION", "M-EXPLANATION-DECOMPOSABILITY"],
        threats=["ANSWER_BEHAVIOR_FARMING"], invariants=["INV-EXPLAINABLE-CONTRIBUTIONS", "INV-DETERMINISTIC-REPLAY", "INV-DECOMPOSABLE-EVIDENCE"], replay=("FORWARD", "REVERSE"),
        trace_parameters={"nonlinear_anchor": 1.32, "selected_order": "COMPONENTWISE_AFTER_UNCERTAINTY"},
    ))

    x_specs = [
        ("SC-XDOMAIN-FIXED-REVIEW-LEARN-0", 10, 0, "fixed Review plus zero Learn"),
        ("SC-XDOMAIN-FIXED-REVIEW-LEARN-1", 10, 1, "fixed Review plus one Learn confirmation"),
        ("SC-XDOMAIN-FIXED-REVIEW-LEARN-5", 10, 5, "fixed Review plus multiple Learn confirmations"),
        ("SC-XDOMAIN-FIXED-LEARN-REVIEW-1", 1, 5, "fixed Learn plus low Review"),
        ("SC-XDOMAIN-FIXED-LEARN-REVIEW-30", 30, 5, "fixed Learn plus increasing Review"),
        ("SC-XDOMAIN-BALANCED", 10, 10, "balanced legitimate mixed day"),
        ("SC-XDOMAIN-REVIEW-HEAVY", 100, 1, "Review-heavy legitimate day"),
        ("SC-XDOMAIN-LEARN-HEAVY", 5, 30, "Learn-heavy legitimate day"),
        ("SC-XDOMAIN-ONE-CAP-BOUNDARY", 100, 5, "above one domain scale while below the other"),
    ]
    for offset, (scenario_id, reviews, learns, description) in enumerate(x_specs):
        scenarios.append(_scenario(
            scenario_id, "CROSS_DOMAIN", PERSONA_IDS[offset % len(PERSONA_IDS)], description, _workload_events(reviews, learns),
            bundle_tags=["CROSS_DOMAIN", "XDOMAIN_DAILY"], gates=x_gates, metrics=x_metrics,
            threats=["DOMAIN_IMBALANCE", "RAW_VOLUME_FARMING"],
            invariants=["INV-EXPLAINABLE-CONTRIBUTIONS", "INV-DECOMPOSABLE-EVIDENCE", "INV-EXPLAINABLE-CONTRIBUTIONS"],
        ))

    for reviews in (5, 10, 30, 100, 300):
        scenarios.append(_scenario(
            f"SC-DAILY-REVIEW-{reviews}", "DAILY_SCALE", PERSONA_IDS[reviews % len(PERSONA_IDS)], f"legitimate day with {reviews} ordinary Reviews", _workload_events(reviews, 0),
            bundle_tags=["DAILY", "XDOMAIN_DAILY"], gates=daily_gates, metrics=daily_metrics,
            threats=["RAW_VOLUME_FARMING"], invariants=["INV-EXPLAINABLE-CONTRIBUTIONS", "INV-XP-NONNEGATIVE"],
        ))
    for learns in (1, 5, 10, 30):
        scenarios.append(_scenario(
            f"SC-DAILY-LEARN-{learns}", "DAILY_SCALE", PERSONA_IDS[learns % len(PERSONA_IDS)], f"legitimate day with {learns} Learn confirmations", _workload_events(0, learns),
            bundle_tags=["DAILY", "XDOMAIN_DAILY"], gates=daily_gates, metrics=daily_metrics,
            threats=["RAW_VOLUME_FARMING"], invariants=["INV-EXPLAINABLE-CONTRIBUTIONS", "INV-XP-NONNEGATIVE"], review_pair_required=False,
        ))
    for scale in (1_000, 10_000, 1_000_000):
        scenarios.append(_scenario(
            f"SC-DAILY-EXTREME-{scale}", "DAILY_SCALE", PERSONA_IDS[3], f"synthetic extreme per-domain input scale {scale}",
            [_event(1, review_units=float(scale), learn_lru=float(scale), verified_base=float(scale), metadata={"aggregate_input": True})],
            bundle_tags=["DAILY", "XDOMAIN_DAILY"], gates=["HG-EXTREME-VOLUME-BOUNDED", "HG-NO-NEGATIVE-XP"], metrics=["M-EXTREME-VOLUME-COMPRESSION", "M-INTENSIVE-DAY-PRESERVATION"],
            threats=["RAW_VOLUME_FARMING", "DOMAIN_IMBALANCE"], invariants=["INV-XP-NONNEGATIVE", "INV-EXPLAINABLE-CONTRIBUTIONS"],
            review_pair_required=False,
            trace_parameters={"review_input": float(scale), "learn_input": float(scale), "expected_review_output_cap": 34.0, "expected_learn_output_cap": 10.0},
        ))

    for day in (59, 60, 61, 75, 89, 90, 91):
        scenarios.append(_scenario(
            f"SC-REVIEW-SOURCE-DAY-{day}", "SOURCE_BOUNDARY", PERSONA_IDS[2], f"exact G1 Review source transition boundary day {day}",
            [_event(1, review_units=1.32, verified_base=1.0, positive_context=0.32, metadata={"simulation_day": day, "retention_transition_day": 60})],
            bundle_tags=["INTEGRATED", "CROSS_DOMAIN"], gates=["HG-REVIEW-AXIS-PRESERVED", "HG-VERIFIED-BASE-PRESERVED", "HG-DETERMINISTIC-REPLAY"], metrics=["M-VERIFIED-BASE-PRESERVATION", "M-CROSS-DOMAIN-SENSITIVITY"],
            threats=["DOMAIN_IMBALANCE", "UNCERTAINTY_COLLAPSE"], invariants=["INV-REVIEW-UNCERTAINTY-PRESERVED", "INV-DETERMINISTIC-REPLAY"],
            replay=("FORWARD", "REVERSE"),
            trace_parameters={"simulation_day": day, "retention_transition_day": 60, "verified_base": 1.0, "memory_gain_positive_context": 0.32},
        ))
    scenarios.append(_scenario(
        "SC-SESSION-SPLIT", "MANIPULATION", PERSONA_IDS[5], "same legitimate work split across two sessions", _workload_events(30, 5, session_split=True),
        bundle_tags=["DAILY"], gates=["HG-NO-SESSION-SPLIT-GAIN", "HG-DETERMINISTIC-REPLAY"], metrics=["M-SESSION-SPLIT-DELTA"],
        threats=["SESSION_SPLIT_FARMING"], invariants=["INV-NO-SESSION-SPLIT-GAIN", "INV-DETERMINISTIC-REPLAY"], replay=("FORWARD", "REVERSE"),
    ))

    interactions = [
        ("SC-INTERACTION-NORMALIZATION-PRODUCTIVE", "PRODUCTIVE", ["CROSS_DOMAIN", "PRODUCTIVE", "XDOMAIN_PRODUCTIVE"], ["HG-CROSS-DOMAIN-DECOMPOSITION-PRESERVED"], ["M-CROSS-DOMAIN-SENSITIVITY", "M-DOMAIN-SHARE"], "normalization x productive-day boundary"),
        ("SC-INTERACTION-NORMALIZATION-LEVEL", "LEVEL", ["CROSS_DOMAIN", "LEVEL", "XDOMAIN_LEVEL"], ["HG-NO-LEVEL-LOSS"], ["M-LEVEL-SCALE-SENSITIVITY"], "normalization x level curve"),
        ("SC-ROUNDING-BOUNDARY", "PIPELINE", ["CROSS_DOMAIN", "DAILY"], ["HG-DETERMINISTIC-REPLAY"], ["M-EXPLANATION-DECOMPOSABILITY"], "rounding boundary at 12 decimal places"),
        ("SC-PLANNED-REST", "STATE", ["STREAK", "MOMENTUM"], ["HG-PLANNED-REST-NEUTRAL"], ["M-PLANNED-REST-DELTA"], "planned rest is neutral"),
        ("SC-MOMENTUM-NO-SNOWBALL", "STATE", ["MOMENTUM"], ["HG-MOMENTUM-NO-SNOWBALL", "HG-MOMENTUM-NO-XP-MULTIPLIER"], ["M-MOMENTUM-SNOWBALL-DELTA"], "Momentum cannot multiply progression"),
        ("SC-RECOVERY-NO-BONUS", "STATE", ["RECOVERY"], ["HG-RECOVERY-NO-BONUS-LOOP"], ["M-RECOVERY-LOOP-DELTA"], "recovery cannot create a return bonus"),
        ("SC-DETERMINISTIC-REPLAY", "REPLAY", ["INTEGRATED"], ["HG-DETERMINISTIC-REPLAY", "HG-DECOMPOSABLE-EXPLANATION"], ["M-EXPLANATION-DECOMPOSABILITY"], "forward/reverse identity and explanation parity"),
    ]
    for index, (scenario_id, category, tags, gates, metrics, description) in enumerate(interactions):
        planned_rest = scenario_id == "SC-PLANNED-REST"
        replay = ("FORWARD", "REVERSE") if scenario_id in {"SC-ROUNDING-BOUNDARY", "SC-DETERMINISTIC-REPLAY"} else ("FORWARD",)
        scenarios.append(_scenario(
            scenario_id, category, PERSONA_IDS[index % len(PERSONA_IDS)], description,
            [_event(1, review_units=0.5 if "ROUNDING" not in scenario_id else 0.333333333333, learn_lru=0.5, verified_base=0.5, planned_rest=planned_rest)],
            bundle_tags=tags, gates=gates, metrics=metrics,
            threats=["EXPLANATION_OPACITY" if "REPLAY" in scenario_id or "ROUNDING" in scenario_id else "MOMENTUM_SNOWBALL" if "MOMENTUM" in scenario_id else "RECOVERY_BONUS_LOOP" if "RECOVERY" in scenario_id else "EXPLANATION_OPACITY"],
            invariants=["INV-DETERMINISTIC-REPLAY", "INV-DECOMPOSABLE-EVIDENCE", "INV-PLANNED-REST-NEUTRAL" if planned_rest else "INV-LEVEL-MONOTONIC"], replay=replay,
        ))

    # Explicit G4.1/G4.2 source-boundary traces. These are semantic
    # scenarios, not identifier-only coverage injection.
    source_specs = [
        (
            "SC-SOURCE-REVIEW-UNCERTAINTY-PARALLEL",
            "MATURE_DECK",
            "same Review evidence remains separate for both frozen Review members",
            _event(1, review_units=1.0, verified_base=1.0, metadata={"review_axis": "REVIEW_MODEL_AXIS_V1", "members": list(REVIEW_MEMBERS), "averaging": "PROHIBITED"}),
            ["DOMAIN_IMBALANCE", "UNCERTAINTY_COLLAPSE"],
            ["INV-REVIEW-UNCERTAINTY-PRESERVED", "INV-DETERMINISTIC-REPLAY"],
            ["HG-REVIEW-AXIS-PRESERVED", "HG-DETERMINISTIC-REPLAY"],
            ["M-EXPLANATION-DECOMPOSABILITY"],
            "VALID",
        ),
        (
            "SC-SOURCE-LEARN-LIMITATION-PRESERVED",
            "BEGINNER_HEAVY",
            "confirmed Learn contribution retains its unresolved identity limitation",
            _event(1, learn_lru=1.0, metadata={"learn_candidate": LEARN_CANDIDATE, "learn_status": "CONFIRMATORY_INCONCLUSIVE", "limitation": LEARN_LIMITATION}),
            ["DOMAIN_IMBALANCE", "EXPLANATION_OPACITY"],
            ["INV-LEARN-LIMITATION-PRESERVED", "INV-EXPLAINABLE-CONTRIBUTIONS"],
            ["HG-LEARN-LIMITATION-PRESERVED", "HG-DECOMPOSABLE-EXPLANATION"],
            ["M-EXPLANATION-DECOMPOSABILITY"],
            "VALID",
        ),
        (
            "SC-SOURCE-BACKLOG-NOT-REWARD",
            "BACKLOG_RETURNER",
            "backlog size and elapsed time are context only and add no contribution",
            _event(1, metadata={"backlog_size": 1000, "time_spent_seconds": 3600, "rewardable": False}),
            ["BACKLOG_FARMING", "RAW_VOLUME_FARMING"],
            ["INV-NO-BACKLOG-SIZE-GAIN", "INV-NO-TIME-SPENT-REWARD", "INV-XP-NONNEGATIVE"],
            ["HG-NO-BACKLOG-SIZE-GAIN", "HG-NO-NEGATIVE-XP"],
            ["M-EXPLOIT-ADVANTAGE"],
            "VALID",
        ),
        (
            "SC-SOURCE-NEW-MATERIAL-CREATE-EXCLUDED",
            "INTENSIVE_LEARNER",
            "raw exposure and excluded Create-domain activity do not become Learn contribution",
            _event(1, metadata={"new_material_exposures": 300, "confirmed_learn": 0, "attempted_domain": "CREATE_DOMAIN", "rewardable": False}),
            ["NEW_MATERIAL_FLOODING", "RAW_VOLUME_FARMING"],
            ["INV-G3-CREATE-XP-EXCLUDED", "INV-NO-NEW-MATERIAL-FLOOD-GAIN", "INV-NO-REAL-USER-DATA"],
            ["HG-CREATE-EXCLUDED", "HG-NO-NEW-MATERIAL-FLOOD-GAIN", "HG-NO-REAL-USER-DATA"],
            ["M-EXPLOIT-ADVANTAGE"],
            "INVALIDATED",
        ),
        (
            "SC-SOURCE-CONFIGURATION-CALENDAR-NEUTRAL",
            "IRREGULAR_LEGITIMATE",
            "scheduler settings, FSRS settings, due dates and clock boundaries remain non-rewardable",
            _event(1, review_units=1.0, verified_base=1.0, metadata={"configured_review_limit": 9999, "timezone_shift_hours": 12, "scheduler_mutated": False, "fsrs_mutated": False, "due_dates_mutated": False}),
            ["CONFIGURATION_FARMING", "CALENDAR_BOUNDARY_FARMING"],
            ["INV-NO-CONFIGURATION-GAIN", "INV-SCHEDULER-UNCHANGED", "INV-FSRS-UNCHANGED", "INV-DUE-DATES-UNCHANGED"],
            ["HG-NO-CONFIGURATION-GAIN", "HG-NO-TIMEZONE-CLOCK-GAIN"],
            ["M-EXPLOIT-ADVANTAGE"],
            "VALID",
        ),
        (
            "SC-SOURCE-HONEST-AGAIN-NO-DIRECT-PRICE",
            "LOW_VOLUME_CONSISTENT",
            "answer button, response speed and time are evidence context rather than direct prices",
            _event(1, review_units=0.25, verified_base=0.25, metadata={"answer_button": "AGAIN", "response_time_ms": 50, "time_spent_seconds": 600, "direct_button_price": False}),
            ["ANSWER_BEHAVIOR_FARMING"],
            ["INV-NO-DIRECT-BUTTON-PRICING", "INV-HONEST-AGAIN-NOT-PUNISHED", "INV-NO-RESPONSE-TIME-REWARD", "INV-NO-TIME-SPENT-REWARD"],
            ["HG-HONEST-AGAIN-NOT-PUNISHED", "HG-VERIFIED-BASE-PRESERVED"],
            ["M-VERIFIED-BASE-PRESERVATION"],
            "VALID",
        ),
        (
            "SC-SOURCE-PLANNED-REST-NO-DEBT",
            "PLANNED_REST_SCHEDULE",
            "planned rest preserves state without contribution, streak growth or debt",
            _event(1, planned_rest=True, metadata={"streak_growth": 0, "xp": 0, "xp_debt": 0}),
            ["STREAK_PRESSURE", "PLANNED_REST_EXPLOIT"],
            ["INV-PLANNED-REST-NEUTRAL", "INV-NO-ABSENCE-XP-DEBT", "INV-STREAK-NO-XP-MULTIPLIER"],
            ["HG-PLANNED-REST-NEUTRAL", "HG-STREAK-NO-XP-MULTIPLIER"],
            ["M-PLANNED-REST-DELTA"],
            "VALID",
        ),
        (
            "SC-SOURCE-MOMENTUM-RECOVERY-STATE-ONLY",
            "ALTERNATING_INTENSIVE_LIGHT",
            "Momentum and recovery remain bounded state indicators without recursive or return bonuses",
            _event(1, review_units=1.0, verified_base=1.0, metadata={"momentum_spendable": False, "momentum_multiplier": 1.0, "recovery_bonus": 0}),
            ["MOMENTUM_SNOWBALL", "RECOVERY_BONUS_LOOP"],
            ["INV-MOMENTUM-BOUNDED-NONSPENDABLE", "INV-MOMENTUM-NO-RECURSIVE-MULTIPLIER", "INV-RECOVERY-NO-BONUS-LOOP"],
            ["HG-MOMENTUM-NO-SNOWBALL", "HG-MOMENTUM-NO-XP-MULTIPLIER", "HG-RECOVERY-NO-BONUS-LOOP"],
            ["M-MOMENTUM-SNOWBALL-DELTA", "M-RECOVERY-LOOP-DELTA"],
            "VALID",
        ),
        (
            "SC-SOURCE-RESEARCH-EXPLANATION-BOUNDARY",
            "BALANCED",
            "decomposition remains synthetic, research-only and production-prohibited",
            _event(1, review_units=1.0, learn_lru=1.0, verified_base=1.0, metadata={"synthetic_only": True, "real_user_data": False, "production_approved": False}),
            ["EXPLANATION_OPACITY"],
            ["INV-DECOMPOSABLE-EVIDENCE", "INV-EXPLAINABLE-CONTRIBUTIONS", "INV-RESEARCH-ONLY", "INV-NO-REAL-USER-DATA", "INV-NO-PRODUCTION-APPROVAL", "INV-LEVEL-MONOTONIC"],
            ["HG-DECOMPOSABLE-EXPLANATION", "HG-RESEARCH-ONLY", "HG-NO-PRODUCTION-APPROVAL", "HG-NO-LEVEL-LOSS"],
            ["M-EXPLANATION-DECOMPOSABILITY"],
            "VALID",
        ),
    ]
    for scenario_id, persona_id, description, event, threats, invariants, gates, metrics, disposition in source_specs:
        scenarios.append(_scenario(
            scenario_id, "SOURCE_BOUNDARY", persona_id, description, [event],
            bundle_tags=["INTEGRATED"], gates=gates, metrics=metrics,
            threats=threats, invariants=invariants, replay=("FORWARD", "REVERSE"),
            expected_validation_disposition=disposition,
        ))

    artifact = {
        "$schema": "../schemas/core-economy-candidate-scenarios-v4.schema.json",
        "identity": {
            "artifact_id": "core-economy-candidate-scenarios",
            "version": PROTOCOL_VERSION,
            "status": "FROZEN_PRE_SCREENING",
            "artifact_digest": "PENDING",
            "digest_scope": "CANONICAL_ARTIFACT_EXCLUDING_IDENTITY_DIGEST",
            "generator_version": GENERATOR_VERSION,
        },
        "protocol_version": PROTOCOL_VERSION,
        "protocol_digest": protocol_digest,
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_digest": pipeline_digest,
        "scenario_count": len(scenarios),
        "expected_outcome_source": "MATRIX_TYPED_IDENTITY_RULE_V1",
        "scenarios": scenarios,
        "results": "NOT_AVAILABLE",
        "production_approved": False,
        "g4_4_started": False,
    }
    return _finalize_digest(artifact)


def _bundle_map(protocol: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(bundle["candidate_bundle_id"]): bundle for bundle in protocol["candidate_bundles"]}


def _bundle_candidates(bundle: Mapping[str, Any]) -> dict[str, str]:
    return {str(item["dimension_id"]): str(item["candidate_id"]) for item in bundle["dimension_candidates"]}


def _expected_gate_outcome(
    bundle: Mapping[str, Any],
    scenario: Mapping[str, Any],
    gate_id: str,
    review_member: str,
) -> dict[str, Any]:
    chosen = _bundle_candidates(bundle)
    abrupt = chosen["UNCERTAINTY_RESPONSE"] == "U-ABRUPT-CUTOFF-CONTROL"
    combined = chosen["DAILY_BOUNDING"] == "D-COMBINED-HARD-6-CONTROL"
    conversion_weights = {
        "X-EQUALIZED-1_0-1_0": (1.0, 1.0),
        "X-LEARN-LEANING-0_8-1_2": (0.8, 1.2),
        "X-REVIEW-LEANING-1_2-0_8-CONTROL": (1.2, 0.8),
    }
    review_input = 0.0
    learn_input = 0.0
    matched_positive = 0.0
    lost_positive = 0.0
    matched_total = 0.0
    for event in scenario["ordered_inputs"]:
        rewardable = bool(event["metadata"].get("rewardable", True))
        if event["metadata"].get("attempted_domain") == "CREATE_DOMAIN":
            rewardable = False
        if not rewardable:
            continue
        raw_review = float(event["review_units"])
        verified_base = float(event["verified_base"])
        positive_context = float(event["positive_context"])
        residual = max(raw_review - verified_base - positive_context, 0.0)
        source_multiplier = 1.0
        if review_member != "NOT_APPLICABLE":
            day = int(
                scenario["trace_parameters"].get(
                    "simulation_day",
                    event["metadata"].get("simulation_day", 59),
                )
            )
            transition_day = int(
                scenario["trace_parameters"].get(
                    "retention_transition_day",
                    event["metadata"].get("retention_transition_day", 60),
                )
            )
            source_multiplier = float(
                evaluate_review_source(
                    review_member,
                    day=day,
                    verified_base=verified_base,
                    positive_context=positive_context,
                    retention_transition_day=transition_day,
                )["memory_gain_multiplier"]
            )
        event_positive = positive_context * source_multiplier
        event_review = verified_base + residual + event_positive
        event_learn = float(event["learn_lru"])
        review_input += event_review
        learn_input += event_learn
        matched_positive += event_positive
        matched_total += event_review + event_learn
        if event["uncertainty_signal"] in {"ISOLATED_ANOMALY", "CONFLICT"}:
            lost_positive += event_positive
    context_loss_ratio = (
        lost_positive / max(matched_positive, EPSILON)
        if matched_positive > 0
        else 0.0
    )
    cumulative_loss_ratio = (
        lost_positive / max(matched_total, EPSILON)
        if matched_total > 0
        else 0.0
    )
    review_weight, learn_weight = conversion_weights[
        chosen["CROSS_DOMAIN_CONVERSION"]
    ]
    combined_saturates = (
        combined
        and review_input > 0
        and learn_input > 0
        and review_input * review_weight + learn_input * learn_weight > 6.0
    )
    outcome = "PASS"
    reason_code = "RC-EXPECTED-PASS"
    predicate_ast = _typed_ast("ALWAYS_PASS")
    if (
        abrupt
        and context_loss_ratio > 0.25
        and gate_id == "HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED"
    ):
        outcome = "CONTROL_EXPECTED_FAIL"
        reason_code = "RC-EXPECTED-ABRUPT-CONTEXT-FAIL"
        predicate_ast = _typed_ast(
            "GT",
            candidate="U-ABRUPT-CUTOFF-CONTROL",
            computed_context_loss_ratio=_round(context_loss_ratio),
            threshold=0.25,
        )
    elif (
        abrupt
        and cumulative_loss_ratio > 0.20
        and gate_id == "HG-FALSE-POSITIVE-CUMULATIVE-HARM-BOUNDED"
    ):
        outcome = "CONTROL_EXPECTED_FAIL"
        reason_code = "RC-EXPECTED-ABRUPT-CUMULATIVE-FAIL"
        predicate_ast = _typed_ast(
            "GT",
            candidate="U-ABRUPT-CUTOFF-CONTROL",
            computed_cumulative_loss_ratio=_round(cumulative_loss_ratio),
            threshold=0.20,
        )
    elif combined_saturates and gate_id == "HG-NO-CROSS-DOMAIN-CROWDOUT":
        outcome = "CONTROL_EXPECTED_FAIL"
        reason_code = "RC-EXPECTED-COMBINED-CROWDOUT-FAIL"
        predicate_ast = _typed_ast("AND", candidate="D-COMBINED-HARD-6-CONTROL", both_domains_positive=True, pre_cap_total_gt=6.0)
    elif combined_saturates and gate_id == "HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED":
        outcome = "CONTROL_EXPECTED_FAIL"
        reason_code = "RC-EXPECTED-COMBINED-MARGINAL-FAIL"
        predicate_ast = _typed_ast("AND", candidate="D-COMBINED-HARD-6-CONTROL", both_domains_positive=True, pre_cap_total_gt=6.0)
    elif combined and gate_id == "HG-DAILY-NORMAL-INTENSIVE-DIFFERENTIABLE":
        outcome = "CONTROL_EXPECTED_FAIL"
        reason_code = "RC-EXPECTED-COMBINED-SEPARATION-FAIL"
        predicate_ast = _typed_ast(
            "EQUALS",
            candidate="D-COMBINED-HARD-6-CONTROL",
            normal_intensive_separation=0.0,
        )
    elif combined and gate_id == "HG-EXTREME-VOLUME-BOUNDED":
        outcome = "CONTROL_EXPECTED_FAIL"
        reason_code = "RC-EXPECTED-COMBINED-CAP-FAIL"
        predicate_ast = _typed_ast(
            "AND",
            candidate="D-COMBINED-HARD-6-CONTROL",
            per_domain_output_caps_applied=False,
        )
    return {
        "gate_id": gate_id,
        "expected_outcome": outcome,
        "reason_code": reason_code,
        "predicate_ast": predicate_ast,
    }


def _applicable_bundles(protocol: Mapping[str, Any], scenario: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    tags = set(scenario["applicable_bundle_tags"])
    bundles = [bundle for bundle in protocol["candidate_bundles"] if tags.intersection(bundle["coverage_tags"])]
    return sorted(bundles, key=lambda value: str(value["candidate_bundle_id"]))


def generate_rows(protocol: Mapping[str, Any], pipeline: Mapping[str, Any], scenarios: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios["scenarios"]:
        members = list(REVIEW_MEMBERS) if scenario["axis_mapping"]["review_pair_required"] else ["NOT_APPLICABLE"]
        for bundle in _applicable_bundles(protocol, scenario):
            for review_member in members:
                for replay_direction in scenario["replay_directions"]:
                    expectation_rule_id = "EXPECTED-OUTCOME-CANDIDATE-SCENARIO-GATE-V1"
                    identity = {
                        "protocol_version": PROTOCOL_VERSION,
                        "pipeline_version": PIPELINE_VERSION,
                        "candidate_bundle_id": bundle["candidate_bundle_id"],
                        "scenario_id": scenario["scenario_id"],
                        "review_member": review_member,
                        "replay_direction": replay_direction,
                        "replica": 0,
                        "seed": None,
                        "expectation_rule_id": expectation_rule_id,
                    }
                    expected = [
                        _expected_gate_outcome(
                            bundle,
                            scenario,
                            gate_id,
                            review_member,
                        )
                        for gate_id in scenario["applicable_gate_ids"]
                    ]
                    review_source_trace = None
                    if review_member != "NOT_APPLICABLE":
                        first = scenario["ordered_inputs"][0]
                        day = int(scenario["trace_parameters"].get("simulation_day", first["metadata"].get("simulation_day", 59)))
                        transition_day = int(scenario["trace_parameters"].get("retention_transition_day", first["metadata"].get("retention_transition_day", 60)))
                        review_source_trace = evaluate_review_source(
                            review_member,
                            day=day,
                            verified_base=float(first["verified_base"]),
                            positive_context=float(first["positive_context"]),
                            retention_transition_day=transition_day,
                        )
                    rows.append(
                        {
                            "row_id": "ROW-" + canonical_digest(identity),
                            **identity,
                            "protocol_digest": protocol["identity"]["artifact_digest"],
                            "pipeline_digest": pipeline["identity"]["artifact_digest"],
                            "scenario_registry_digest": scenarios["identity"]["artifact_digest"],
                            "metric_set": list(scenario["metric_ids"]),
                            "expected_gate_outcomes": expected,
                            "review_source_trace": review_source_trace,
                            "learn_limitation": LEARN_LIMITATION,
                            "result_status": "NOT_RUN",
                            "result": "NOT_AVAILABLE",
                            "production_status": "RESEARCH_ONLY",
                        }
                    )
    return rows


def build_matrix(protocol: Mapping[str, Any], pipeline: Mapping[str, Any], scenarios: Mapping[str, Any]) -> dict[str, Any]:
    rows = generate_rows(protocol, pipeline, scenarios)
    coverage = {
        "expected_rows": len(rows),
        "unique_rows": len({row["row_id"] for row in rows}),
        "duplicates": len(rows) - len({row["row_id"] for row in rows}),
        "missing": 0,
        "extra": 0,
        "candidate_bundles": len({row["candidate_bundle_id"] for row in rows}),
        "scenarios": len({row["scenario_id"] for row in rows}),
        "review_members": sorted({row["review_member"] for row in rows}),
        "gates": len({item["gate_id"] for row in rows for item in row["expected_gate_outcomes"]}),
        "metrics": len({metric for row in rows for metric in row["metric_set"]}),
        "personas": len({scenario["persona_id"] for scenario in scenarios["scenarios"]}),
        "threats": len({threat for scenario in scenarios["scenarios"] for threat in scenario["threat_ids"]}),
        "invariants": len({invariant for scenario in scenarios["scenarios"] for invariant in scenario["invariant_ids"]}),
    }
    artifact = {
        "$schema": "../schemas/core-economy-screening-matrix-v4.schema.json",
        "identity": {
            "artifact_id": "core-economy-screening-matrix",
            "version": PROTOCOL_VERSION,
            "status": "FROZEN_PRE_SCREENING",
            "artifact_digest": "PENDING",
            "digest_scope": "CANONICAL_ARTIFACT_EXCLUDING_IDENTITY_DIGEST",
            "generator_version": GENERATOR_VERSION,
        },
        "protocol_version": PROTOCOL_VERSION,
        "protocol_digest": protocol["identity"]["artifact_digest"],
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_digest": pipeline["identity"]["artifact_digest"],
        "scenario_registry_digest": scenarios["identity"]["artifact_digest"],
        "row_count": len(rows),
        "coverage": coverage,
        "rows": rows,
        "result_status": "NOT_RUN",
        "results": "NOT_AVAILABLE",
        "screening_executed": False,
        "simulation_started": False,
        "g4_4_started": False,
        "production_approved": False,
    }
    return _finalize_digest(artifact)


def build_all() -> dict[str, dict[str, Any]]:
    pipeline = build_pipeline()
    protocol_seed = build_protocol(pipeline=pipeline, pipeline_digest=pipeline["identity"]["artifact_digest"])
    scenarios = build_scenarios(protocol_seed["identity"]["artifact_digest"], pipeline["identity"]["artifact_digest"])
    matrix = build_matrix(protocol_seed, pipeline, scenarios)
    protocol = build_protocol(
        pipeline=pipeline,
        pipeline_digest=pipeline["identity"]["artifact_digest"],
        scenario_digest=scenarios["identity"]["artifact_digest"],
        matrix_digest=matrix["identity"]["artifact_digest"],
        scenario_count=scenarios["scenario_count"],
        matrix_count=matrix["row_count"],
    )
    if protocol["identity"]["artifact_digest"] != protocol_seed["identity"]["artifact_digest"]:
        _fail("DIGEST_PROTOCOL_SCOPE", "protocol digest changed when cross-artifact registry digests were finalized")
    matrix = build_matrix(protocol, pipeline, scenarios)
    protocol = build_protocol(
        pipeline=pipeline,
        pipeline_digest=pipeline["identity"]["artifact_digest"],
        scenario_digest=scenarios["identity"]["artifact_digest"],
        matrix_digest=matrix["identity"]["artifact_digest"],
        scenario_count=scenarios["scenario_count"],
        matrix_count=matrix["row_count"],
    )
    return {"protocol": protocol, "pipeline": pipeline, "scenarios": scenarios, "matrix": matrix}


def _schema_identity(artifact_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["artifact_id", "version", "status", "artifact_digest", "digest_scope"],
        "properties": {
            "artifact_id": {"const": artifact_id},
            "version": {"const": PROTOCOL_VERSION},
            "status": {"const": "FROZEN_PRE_SCREENING"},
            "artifact_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "digest_scope": {"type": "string", "minLength": 1},
            "validator_version": {"type": "string"},
            "generator_version": {"type": "string"},
            "stage": {"type": "string"},
        },
    }


def _base_schema(artifact_id: str, required: Sequence[str], properties: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://example.invalid/anki-study-report/{artifact_id}-v4.schema.json",
        "type": "object",
        "additionalProperties": False,
        "required": list(required),
        "properties": dict(properties),
    }


def _strict_shape(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(value.keys()),
            "properties": {key: _strict_shape(item) for key, item in value.items()},
        }
    if isinstance(value, list):
        if not value:
            return {"type": "array", "minItems": 0, "maxItems": 0}
        item_schemas: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in value:
            schema = _strict_shape(item)
            identity = canonical_dumps(schema)
            if identity not in seen:
                seen.add(identity)
                item_schemas.append(schema)
        item_schema: dict[str, Any]
        if len(item_schemas) == 1:
            item_schema = item_schemas[0]
        else:
            item_schema = {"anyOf": item_schemas}
        return {
            "type": "array",
            "minItems": len(value),
            "maxItems": len(value),
            "items": item_schema,
        }
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if value is None:
        return {"type": "null"}
    if isinstance(value, str):
        return {"type": "string"}
    raise TypeError(f"unsupported JSON value for strict schema: {type(value).__name__}")


def _with_const(schema: dict[str, Any], key: str, value: Any) -> None:
    schema["properties"][key] = {"const": value}


def build_schemas(artifacts: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    protocol = artifacts["protocol"]
    pipeline = artifacts["pipeline"]
    scenarios = artifacts["scenarios"]
    matrix = artifacts["matrix"]

    protocol_properties = {key: _strict_shape(value) for key, value in protocol.items()}
    protocol_properties["identity"] = _schema_identity("core-economy-candidate-protocol")
    protocol_properties["domain_registry"] = {"const": ["REVIEW_DOMAIN", "LEARN_DOMAIN"]}
    protocol_properties["excluded_domains"] = {"const": ["CREATE_DOMAIN"]}
    protocol_properties["candidate_registry"]["minItems"] = protocol_properties["candidate_registry"]["maxItems"] = len(protocol["candidate_registry"])
    protocol_properties["candidate_bundles"]["minItems"] = protocol_properties["candidate_bundles"]["maxItems"] = len(protocol["candidate_bundles"])
    protocol_properties["hypotheses"]["minItems"] = protocol_properties["hypotheses"]["maxItems"] = len(protocol["hypotheses"])
    protocol_properties["hard_gates"]["minItems"] = protocol_properties["hard_gates"]["maxItems"] = len(protocol["hard_gates"])
    protocol_properties["metrics"]["minItems"] = protocol_properties["metrics"]["maxItems"] = len(protocol["metrics"])
    protocol_schema = _base_schema(
        "core-economy-candidate-protocol",
        list(protocol.keys()),
        protocol_properties,
    )

    pipeline_properties = {key: _strict_shape(value) for key, value in pipeline.items()}
    pipeline_properties["identity"] = _schema_identity("core-economy-evaluation-pipeline")
    pipeline_properties["steps"]["minItems"] = pipeline_properties["steps"]["maxItems"] = 17
    pipeline_schema = _base_schema(
        "core-economy-evaluation-pipeline",
        list(pipeline.keys()),
        pipeline_properties,
    )

    scenarios_properties = {key: _strict_shape(value) for key, value in scenarios.items()}
    scenarios_properties["identity"] = _schema_identity("core-economy-candidate-scenarios")
    scenarios_properties["protocol_version"] = {"const": PROTOCOL_VERSION}
    scenarios_properties["pipeline_version"] = {"const": PIPELINE_VERSION}
    scenarios_properties["scenario_count"] = {"const": len(scenarios["scenarios"])}
    scenarios_properties["expected_outcome_source"] = {"const": "MATRIX_TYPED_IDENTITY_RULE_V1"}
    scenarios_properties["results"] = {"const": "NOT_AVAILABLE"}
    scenarios_properties["production_approved"] = {"const": False}
    scenarios_properties["g4_4_started"] = {"const": False}
    scenarios_schema = _base_schema(
        "core-economy-candidate-scenarios",
        list(scenarios.keys()),
        scenarios_properties,
    )

    matrix_properties = {key: _strict_shape(value) for key, value in matrix.items()}
    matrix_properties["identity"] = _schema_identity("core-economy-screening-matrix")
    matrix_properties["protocol_version"] = {"const": PROTOCOL_VERSION}
    matrix_properties["pipeline_version"] = {"const": PIPELINE_VERSION}
    matrix_properties["row_count"] = {"const": len(matrix["rows"])}
    matrix_properties["result_status"] = {"const": "NOT_RUN"}
    matrix_properties["results"] = {"const": "NOT_AVAILABLE"}
    matrix_properties["screening_executed"] = {"const": False}
    matrix_properties["simulation_started"] = {"const": False}
    matrix_properties["g4_4_started"] = {"const": False}
    matrix_properties["production_approved"] = {"const": False}
    matrix_schema = _base_schema(
        "core-economy-screening-matrix",
        list(matrix.keys()),
        matrix_properties,
    )
    return {
        "protocol": protocol_schema,
        "pipeline": pipeline_schema,
        "scenarios": scenarios_schema,
        "matrix": matrix_schema,
    }


def evaluate_false_positive(matched_positive_context: float, matched_total_contribution: float, multiplier: float) -> dict[str, float]:
    if matched_positive_context < 0 or matched_total_contribution <= 0 or not 0 <= multiplier <= 1:
        _fail("FALSE_POSITIVE_INPUT", "invalid false-positive trace")
    lost_context = matched_positive_context * (1 - multiplier)
    return {
        "lost_positive_context": _round(lost_context),
        "context_loss_ratio": _round(lost_context / max(matched_positive_context, EPSILON)),
        "total_immediate_loss_ratio": _round(lost_context / max(matched_total_contribution, EPSILON)),
    }


def _piecewise(value: float, bands: Sequence[tuple[float | None, float]]) -> float:
    remaining = max(float(value), 0.0)
    result = 0.0
    for width, multiplier in bands:
        if width is None:
            result += remaining * multiplier
            remaining = 0.0
            break
        used = min(remaining, width)
        result += used * multiplier
        remaining -= used
        if remaining <= EPSILON:
            break
    return _round(result)


def apply_daily(review_value: float, learn_value: float, daily_candidate_id: str) -> dict[str, float]:
    if not math.isfinite(float(review_value)) or not math.isfinite(float(learn_value)):
        _fail("NONFINITE_CONTRIBUTION", "daily input must be finite")
    if min(review_value, learn_value) < 0:
        _fail("NEGATIVE_CONTRIBUTION", "daily input cannot be negative")
    if daily_candidate_id == "D-PER-DOMAIN-BOUNDED-MEDIUM":
        review = _piecewise(review_value, [(10.0, 1.0), (20.0, 0.5), (70.0, 0.2)])
        learn = _piecewise(learn_value, [(2.0, 1.0), (8.0, 0.5), (20.0, 0.2)])
        return {"review_bounded": review, "learn_bounded": learn, "global_envelope_applied": 0.0}
    if daily_candidate_id == "D-PER-DOMAIN-SQRT-HIGH":
        review = review_value if review_value <= 30 else min(60.0, 30.0 + math.sqrt(review_value - 30.0))
        learn = learn_value if learn_value <= 5 else min(20.0, 5.0 + math.sqrt(learn_value - 5.0))
        return {"review_bounded": _round(review), "learn_bounded": _round(learn), "global_envelope_applied": 0.0}
    if daily_candidate_id == "D-COMBINED-HARD-6-CONTROL":
        return {"review_bounded": _round(review_value), "learn_bounded": _round(learn_value), "global_envelope_applied": 1.0}
    _fail("UNKNOWN_DAILY_CANDIDATE", daily_candidate_id)


def apply_cross_domain(review_bounded: float, learn_bounded: float, conversion_candidate: Mapping[str, Any], daily_candidate_id: str) -> dict[str, float]:
    review_component = _round(review_bounded * float(conversion_candidate["review_weight"]))
    learn_component = _round(learn_bounded * float(conversion_candidate["learn_weight"]))
    total = review_component + learn_component
    if daily_candidate_id == "D-COMBINED-HARD-6-CONTROL" and total > 6.0:
        factor = 6.0 / total
        review_component = _round(review_component * factor)
        learn_component = _round(learn_component * factor)
        total = _round(review_component + learn_component)
    return {"review_component": review_component, "learn_component": learn_component, "total_npu": _round(total)}


def nonlinear_componentwise_selected(verified_base: float, positive_context: float, multiplier: float, anchor: float = 1.32) -> float:
    def norm(value: float) -> float:
        return math.log1p(3 * max(value, 0.0)) / math.log1p(3 * anchor)
    return _round(norm(verified_base) + norm(positive_context * multiplier))


def nonlinear_aggregate_first_prohibited(verified_base: float, positive_context: float, multiplier: float, anchor: float = 1.32) -> float:
    normalized = math.log1p(3 * max(verified_base + positive_context, 0.0)) / math.log1p(3 * anchor)
    return _round(normalized * multiplier)


def _unique(values: Sequence[Mapping[str, Any]], key: str, code: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for value in values:
        identifier = str(value[key])
        if identifier in result:
            _fail(code, f"duplicate {key}: {identifier}")
        result[identifier] = value
    return result


def _assert_digest(value: Mapping[str, Any], code: str) -> None:
    actual = artifact_digest(value)
    expected = value.get("identity", {}).get("artifact_digest")
    if actual != expected:
        _fail(code, f"digest mismatch: expected {expected}, actual {actual}")


def semantic_validate(protocol: Mapping[str, Any], pipeline: Mapping[str, Any], scenarios: Mapping[str, Any], matrix: Mapping[str, Any], *, human_text: str | None = None) -> None:
    if protocol["identity"]["version"] != 4 or pipeline["identity"]["version"] != 4 or scenarios["identity"]["version"] != 4 or matrix["identity"]["version"] != 4:
        _fail("V4_IDENTITY_MIX", "all v4 artifact versions must equal 4")
    for value, code in ((protocol, "PROTOCOL_DIGEST_MISMATCH"), (pipeline, "PIPELINE_DIGEST_MISMATCH"), (scenarios, "SCENARIO_DIGEST_MISMATCH"), (matrix, "MATRIX_DIGEST_MISMATCH")):
        _assert_digest(value, code)
    # Cross-artifact digest/reference continuity.
    protocol_digest = protocol["identity"]["artifact_digest"]
    pipeline_digest = pipeline["identity"]["artifact_digest"]
    scenario_digest = scenarios["identity"]["artifact_digest"]
    matrix_digest = matrix["identity"]["artifact_digest"]
    if scenarios["protocol_digest"] != protocol_digest or scenarios["pipeline_digest"] != pipeline_digest:
        _fail("SCENARIO_CROSS_DIGEST_MISMATCH", "scenario registry does not reference exact protocol/pipeline digests")
    if matrix["protocol_digest"] != protocol_digest or matrix["pipeline_digest"] != pipeline_digest or matrix["scenario_registry_digest"] != scenario_digest:
        _fail("MATRIX_CROSS_DIGEST_MISMATCH", "matrix does not reference exact protocol/pipeline/scenario digests")
    registry = protocol["artifact_registry"]
    if registry["pipeline"]["digest"] != pipeline_digest or registry["scenarios"]["digest"] != scenario_digest or registry["matrix"]["digest"] != matrix_digest:
        _fail("PROTOCOL_ARTIFACT_REGISTRY_MISMATCH", "protocol artifact registry digests do not match canonical artifacts")
    expected_prior = [
        {"version": 1, "status": "SUPERSEDED_PRE_EXECUTION", "results": "NOT_AVAILABLE"},
        {"version": 2, "status": "SUPERSEDED_PRE_EXECUTION", "results": "NOT_AVAILABLE"},
        {
            "version": 3,
            "status": "INVALIDATED_AFTER_SUBSTANTIVE_DEFECT",
            "results": "INVALIDATED_NOT_DECISION_EVIDENCE",
        },
    ]
    if (
        protocol["supersession"]["prior_versions"] != expected_prior
        or not protocol["supersession"]["results_accessed_before_republication"]
        or protocol["supersession"]["v3_artifacts_mutable"]
    ):
        _fail(
            "SUPERSESSION_STATE",
            "v1/v2 remain no-results and invalidated v3 remains immutable",
        )
    if protocol["governance"]["g4_2_correction_method"] != "STALE_CLOSEOUT_IDENTITY_LEDGER_CORRECTION":
        _fail("G4_2_CORRECTION_CLASSIFICATION", "G4.2 correction must be a stale ledger correction")
    if protocol["domain_registry"] != ["REVIEW_DOMAIN", "LEARN_DOMAIN"] or protocol["excluded_domains"] != ["CREATE_DOMAIN"]:
        _fail("DOMAIN_REGISTRY", "only Review and Learn are initial domains; Create is excluded")
    review = protocol["review_axis"]
    if review["members"] != list(REVIEW_MEMBERS) or review["selection"] != "NONE" or review["default"] != "NONE" or review["winner"] != "NONE" or review["averaging"] != "PROHIBITED" or review["evaluation"] != "PARALLEL_SEPARATE":
        _fail("REVIEW_AXIS", "Review axis must retain exact pair with no selection/default/winner/averaging")
    learn = protocol["learn_input"]
    if learn["candidate_id"] != LEARN_CANDIDATE or learn["status"] != "CONFIRMATORY_INCONCLUSIVE" or learn["limitation"] != LEARN_LIMITATION or learn["frozen_source_total"] != 1.0:
        _fail("LEARN_INPUT", "Learn input/status/limitation must remain exact")
    candidates = _unique(protocol["candidate_registry"], "candidate_id", "DUPLICATE_CANDIDATE_ID")
    if len(candidates) != 19:
        _fail("CANDIDATE_COUNT", f"expected 19 candidates, found {len(candidates)}")
    for candidate in candidates.values():
        if candidate["dimension_id"] not in REQUIRED_DIMENSIONS:
            _fail("CANDIDATE_DIMENSION", str(candidate["candidate_id"]))
        if candidate["production_status"] != "RESEARCH_ONLY":
            _fail("PRODUCTION_STATUS", str(candidate["candidate_id"]))
        if candidate["control_only"] and candidate["recommendation_eligible"]:
            _fail("CONTROL_RECOMMENDATION", str(candidate["candidate_id"]))
        if not isinstance(candidate.get("formula_ast"), dict) or not candidate["formula_ast"].get("op"):
            _fail("UNTYPED_FORMULA", str(candidate["candidate_id"]))
    if "U-FIXED-LINEAR-TAPER" in candidates or "U-FIXED-STEPPED-TAPER" not in candidates:
        _fail("INACCURATE_LINEAR_NAME", "stepped taper must not be named linear")
    for control_id in ("U-ABRUPT-CUTOFF-CONTROL", "D-COMBINED-HARD-6-CONTROL", "X-REVIEW-LEANING-1_2-0_8-CONTROL"):
        control = candidates[control_id]
        if not control["control_only"] or control["recommendation_eligible"]:
            _fail("CONTROL_RECOMMENDATION", control_id)
    for candidate in candidates.values():
        if candidate["dimension_id"] in {"STREAK_PLANNED_REST", "MOMENTUM"} and candidate.get("xp_multiplier") is not False:
            _fail("STATE_XP_MULTIPLIER", str(candidate["candidate_id"]))
        if candidate["dimension_id"] == "RECOVERY":
            if candidate.get("bonus_allowed") is not False or float(candidate.get("contribution_multiplier", 0.0)) != 1.0:
                _fail("RECOVERY_BONUS", str(candidate["candidate_id"]))
    for conversion_id in ("X-EQUALIZED-1_0-1_0", "X-LEARN-LEANING-0_8-1_2", "X-REVIEW-LEANING-1_2-0_8-CONTROL"):
        candidate = candidates[conversion_id]
        if float(candidate.get("review_weight", 0)) <= 0 or float(candidate.get("learn_weight", 0)) <= 0:
            _fail("CROSS_DOMAIN_WEIGHT", conversion_id)
    daily_candidates = [candidate for candidate in candidates.values() if candidate["dimension_id"] == "DAILY_BOUNDING"]
    for candidate in daily_candidates:
        if candidate.get("scope") not in {"PER_DOMAIN_THEN_COMBINE", "COMBINED_TOTAL_CONTROL"}:
            _fail("DAILY_SCOPE", str(candidate["candidate_id"]))
        if candidate["scope"] == "COMBINED_TOTAL_CONTROL" and candidate["recommendation_eligible"]:
            _fail("COMBINED_CAP_RECOMMENDATION", str(candidate["candidate_id"]))
    bundles = _unique(protocol["candidate_bundles"], "candidate_bundle_id", "DUPLICATE_BUNDLE_ID")
    combinations: set[tuple[str, ...]] = set()
    for bundle in bundles.values():
        chosen = _bundle_candidates(bundle)
        if tuple(chosen) != REQUIRED_DIMENSIONS or len(chosen) != len(REQUIRED_DIMENSIONS):
            _fail("BUNDLE_DIMENSION_SET", str(bundle["candidate_bundle_id"]))
        for dimension, candidate_id in chosen.items():
            if candidate_id not in candidates or candidates[candidate_id]["dimension_id"] != dimension:
                _fail("BUNDLE_CANDIDATE_REFERENCE", str(bundle["candidate_bundle_id"]))
        combination = tuple(chosen[dimension] for dimension in REQUIRED_DIMENSIONS)
        if combination in combinations:
            _fail("DUPLICATE_BUNDLE_COMBINATION", str(bundle["candidate_bundle_id"]))
        combinations.add(combination)
        if bundle["control_only"] and bundle["recommendation_eligible"]:
            _fail("CONTROL_RECOMMENDATION", str(bundle["candidate_bundle_id"]))
    gates = _unique(protocol["hard_gates"], "gate_id", "DUPLICATE_GATE_ID")
    metrics = _unique(protocol["metrics"], "metric_id", "DUPLICATE_METRIC_ID")
    for gate in gates.values():
        if any(metric_id not in metrics for metric_id in gate["required_metric_ids"]):
            _fail("GATE_METRIC_REFERENCE", str(gate["gate_id"]))
        if not isinstance(gate.get("predicate_ast"), dict) or not gate["predicate_ast"].get("op"):
            _fail("UNTYPED_GATE_PREDICATE", str(gate["gate_id"]))
    for metric in metrics.values():
        if not isinstance(metric.get("formula_ast"), dict) or metric["formula_ast"].get("op") != "BUILTIN_METRIC_V1":
            _fail("UNTYPED_METRIC_FORMULA", str(metric["metric_id"]))
    fp_metric = metrics["M-FALSE-POSITIVE-CONTEXT-LOSS"]
    if fp_metric["formula"] != "lost_positive_context / max(matched_positive_context, epsilon)":
        _fail("FALSE_POSITIVE_DENOMINATOR", "primary false-positive metric denominator must be positive context")
    for required_gate in ("HG-NO-CROSS-DOMAIN-CROWDOUT", "HG-CROSS-DOMAIN-DECOMPOSITION-PRESERVED", "HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED"):
        if required_gate not in gates:
            _fail("CROSS_DOMAIN_GATE", required_gate)
    for required_metric in ("M-REVIEW-MARGINAL-CONTRIBUTION", "M-LEARN-MARGINAL-CONTRIBUTION", "M-DOMAIN-CROWDOUT", "M-DOMAIN-SHARE", "M-CROSS-DOMAIN-SENSITIVITY"):
        if required_metric not in metrics:
            _fail("CROSS_DOMAIN_METRIC", required_metric)
    marginal_gate = gates["HG-DOMAIN-MARGINAL-CONTRIBUTION-PRESERVED"]
    if marginal_gate["required_metric_ids"] != [
        "M-REVIEW-MARGINAL-CONTRIBUTION",
        "M-LEARN-MARGINAL-CONTRIBUTION",
    ]:
        _fail("DUAL_DOMAIN_MARGINALITY_LINKAGE", "both Review and Learn metrics are required")
    step_ids = [step["step_id"] for step in pipeline["steps"]]
    expected_step_ids = [step["step_id"] for step in _pipeline_steps()]
    if step_ids != expected_step_ids or len(step_ids) != 17:
        _fail("PIPELINE_ORDER", "pipeline must contain exact 17-step operator order")
    if pipeline["operator_order_resolution"]["selected"] != "NORMALIZE_COMPONENTS_SEPARATELY_AFTER_UNCERTAINTY":
        _fail("NONLINEAR_ORDER", "component-wise post-uncertainty normalization is mandatory")
    uncertainty = pipeline["uncertainty_state_machine"]
    if (
        uncertainty["affected_component"] != "POSITIVE_CONTEXT"
        or uncertainty["unaffected_components"] != ["VERIFIED_BASE", "NEGATIVE_CONTEXT"]
        or uncertainty["transition_table"] != _uncertainty_transition_table()
        or uncertainty["past_progression_mutation"]
        or uncertainty["debt_allowed"]
        or uncertainty["bonus_multiplier_allowed"]
    ):
        _fail("UNCERTAINTY_COMPONENT_SCOPE", "uncertainty state machine drifted")
    source_transition = review["source_transition"]
    if (
        source_transition["retention_transition_day"] != 60
        or source_transition["boundary_days"] != [59, 60, 61, 75, 89, 90, 91]
        or source_transition["source_component_scaled"] != "MEMORY_GAIN_POSITIVE_CONTEXT"
        or source_transition["source_identities"] != G1_SOURCE_IDENTITIES
    ):
        _fail("REVIEW_SOURCE_CONTRACT", "G1 source transition identity or boundaries drifted")
    bounded_daily = candidates["D-PER-DOMAIN-BOUNDED-MEDIUM"]
    bounded_ast = bounded_daily["formula_ast"]
    if (
        bounded_ast.get("op") != "PER_DOMAIN_BOUNDED_PIECEWISE"
        or bounded_ast.get("tail_multiplier") != 0.0
        or bounded_ast.get("review_output_cap") != 34.0
        or bounded_ast.get("learn_output_cap") != 10.0
    ):
        _fail("DAILY_FINITE_BOUND_CONTRACT", "bounded daily candidate must have exact finite caps")
    scenario_map = _unique(scenarios["scenarios"], "scenario_id", "DUPLICATE_SCENARIO_ID")
    if scenarios["scenario_count"] != len(scenario_map):
        _fail("SCENARIO_COUNT", "scenario_count mismatch")
    if scenarios["expected_outcome_source"] != "MATRIX_TYPED_IDENTITY_RULE_V1":
        _fail("EXPECTED_OUTCOME_SOURCE", "matrix typed identity rule must be sole candidate-specific source")
    for scenario in scenario_map.values():
        if "expected_hard_gate_outcomes" in scenario:
            _fail("SCENARIO_EXPECTED_OUTCOME", str(scenario["scenario_id"]))
        if not scenario["synthetic_only"] or scenario["real_user_data"] or scenario["result_status"] != "NOT_AVAILABLE":
            _fail("SCENARIO_BOUNDARY", str(scenario["scenario_id"]))
        if scenario["axis_mapping"]["review_pair_required"] and scenario["axis_mapping"]["review_members"] != list(REVIEW_MEMBERS):
            _fail("REVIEW_PAIR_REQUIRED", str(scenario["scenario_id"]))
        if scenario["axis_mapping"]["learn_candidate_id"] != LEARN_CANDIDATE:
            _fail("LEARN_INPUT", str(scenario["scenario_id"]))
        if any(gate_id not in gates for gate_id in scenario["applicable_gate_ids"]):
            _fail("SCENARIO_GATE_REFERENCE", str(scenario["scenario_id"]))
        if any(metric_id not in metrics for metric_id in scenario["metric_ids"]):
            _fail("SCENARIO_METRIC_REFERENCE", str(scenario["scenario_id"]))
        required_gate_metrics = {
            metric_id
            for gate_id in scenario["applicable_gate_ids"]
            for metric_id in gates[gate_id]["required_metric_ids"]
        }
        if not required_gate_metrics.issubset(set(scenario["metric_ids"])):
            _fail(
                "SCENARIO_GATE_METRIC_LINKAGE",
                f"{scenario['scenario_id']}: "
                f"{sorted(required_gate_metrics - set(scenario['metric_ids']))}",
            )
        sequences = [event["sequence"] for event in scenario["ordered_inputs"]]
        if sequences != list(range(1, len(sequences) + 1)):
            _fail("SCENARIO_INPUT_ORDER", str(scenario["scenario_id"]))
    if {scenario["persona_id"] for scenario in scenario_map.values()} != set(PERSONA_IDS):
        _fail("PERSONA_COVERAGE", "all nine personas must be covered")
    if {threat for scenario in scenario_map.values() for threat in scenario["threat_ids"]} != set(THREAT_IDS):
        _fail("THREAT_COVERAGE", "threat coverage mismatch")
    if {invariant for scenario in scenario_map.values() for invariant in scenario["invariant_ids"]} != set(INVARIANT_IDS):
        _fail("INVARIANT_COVERAGE", "invariant coverage mismatch")
    if {hypothesis for scenario in scenario_map.values() for hypothesis in scenario["hypothesis_ids"]} != set(_unique(protocol["hypotheses"], "hypothesis_id", "DUPLICATE_HYPOTHESIS_ID")):
        _fail("HYPOTHESIS_COVERAGE", "hypothesis coverage mismatch")
    scenario_gate_ids = {gate for scenario in scenario_map.values() for gate in scenario["applicable_gate_ids"]}
    if scenario_gate_ids != set(gates):
        _fail("GATE_COVERAGE", f"missing={sorted(set(gates) - scenario_gate_ids)} extra={sorted(scenario_gate_ids - set(gates))}")
    scenario_metric_ids = {metric for scenario in scenario_map.values() for metric in scenario["metric_ids"]}
    if scenario_metric_ids != set(metrics):
        _fail("METRIC_COVERAGE", f"missing={sorted(set(metrics) - scenario_metric_ids)} extra={sorted(scenario_metric_ids - set(metrics))}")
    declared_replay = {direction for scenario in scenario_map.values() for direction in scenario["replay_directions"]}
    if declared_replay != {"FORWARD", "REVERSE"}:
        _fail("REPLAY_DIRECTION_COVERAGE", str(sorted(declared_replay)))
    required_interactions = set(protocol["interaction_design"]["required_interactions"])
    observed_interactions: set[str] = set()
    for scenario in scenario_map.values():
        tags = set(scenario["applicable_bundle_tags"])
        if {"CROSS_DOMAIN", "DAILY"}.issubset(tags) or "XDOMAIN_DAILY" in tags:
            observed_interactions.update(
                {
                    "NORMALIZATION_X_DAILY_BOUNDING",
                    "DAILY_BOUNDING_X_CROSS_DOMAIN_CONVERSION",
                }
            )
        if "XDOMAIN_PRODUCTIVE" in tags:
            observed_interactions.add("NORMALIZATION_X_PRODUCTIVE_DAY")
        if "XDOMAIN_LEVEL" in tags:
            observed_interactions.add("NORMALIZATION_X_LEVEL_CURVE")
        if "HG-NO-CROSS-DOMAIN-CROWDOUT" in scenario["applicable_gate_ids"]:
            observed_interactions.add("DAILY_BOUNDING_X_DOMAIN_CROWDOUT")
    if observed_interactions != required_interactions:
        _fail("INTERACTION_COVERAGE", f"missing={sorted(required_interactions - observed_interactions)} extra={sorted(observed_interactions - required_interactions)}")
    row_map = _unique(matrix["rows"], "row_id", "DUPLICATE_ROW_ID")
    if matrix["row_count"] != len(row_map):
        _fail("ROW_COUNT", "row_count mismatch")
    # Validate row-local typed identities before whole-matrix completeness.
    for row in matrix["rows"]:
        identity = {key: row[key] for key in ("protocol_version", "pipeline_version", "candidate_bundle_id", "scenario_id", "review_member", "replay_direction", "replica", "seed", "expectation_rule_id")}
        expected_id = "ROW-" + canonical_digest(identity)
        if row["row_id"] != expected_id:
            _fail("ROW_ID_MISMATCH", str(row["row_id"]))
        if row["candidate_bundle_id"] not in bundles or row["scenario_id"] not in scenario_map:
            _fail("MATRIX_REFERENCE", str(row["row_id"]))
        scenario = scenario_map[row["scenario_id"]]
        if scenario["axis_mapping"]["review_pair_required"] and row["review_member"] not in REVIEW_MEMBERS:
            _fail("REVIEW_MEMBER_SOURCE_MISMATCH", str(row["row_id"]))
        if not scenario["axis_mapping"]["review_pair_required"] and row["review_member"] != "NOT_APPLICABLE":
            _fail("REVIEW_MEMBER_SOURCE_MISMATCH", str(row["row_id"]))
        if row["result_status"] != "NOT_RUN" or row["result"] != "NOT_AVAILABLE" or row["production_status"] != "RESEARCH_ONLY":
            _fail("RESULT_STATUS", str(row["row_id"]))
        if row["protocol_digest"] != protocol_digest or row["pipeline_digest"] != pipeline_digest or row["scenario_registry_digest"] != scenario_digest:
            _fail("ROW_CROSS_DIGEST_MISMATCH", str(row["row_id"]))
        expected_outcomes = [
            _expected_gate_outcome(
                bundles[row["candidate_bundle_id"]],
                scenario,
                gate_id,
                row["review_member"],
            )
            for gate_id in scenario["applicable_gate_ids"]
        ]
        if row["expected_gate_outcomes"] != expected_outcomes:
            _fail("EXPECTED_OUTCOME_IDENTITY_RULE", str(row["row_id"]))
        if row["learn_limitation"] != LEARN_LIMITATION:
            _fail("LEARN_LIMITATION_ROW", str(row["row_id"]))
        if row["review_member"] == "NOT_APPLICABLE":
            if row["review_source_trace"] is not None:
                _fail("REVIEW_SOURCE_TRACE", str(row["row_id"]))
        elif row["review_source_trace"]["review_member"] != row["review_member"]:
            _fail("REVIEW_SOURCE_TRACE", str(row["row_id"]))
    expected_rows = generate_rows(protocol, pipeline, scenarios)
    expected_by_id = {row["row_id"]: row for row in expected_rows}
    actual_by_id = {row["row_id"]: row for row in matrix["rows"]}
    missing = sorted(set(expected_by_id) - set(actual_by_id))
    extra = sorted(set(actual_by_id) - set(expected_by_id))
    if missing:
        _fail("MISSING_MATRIX_ROW", missing[0])
    if extra:
        _fail("EXTRA_MATRIX_ROW", extra[0])
    if expected_by_id != actual_by_id:
        for row_id in expected_by_id:
            if expected_by_id[row_id] != actual_by_id[row_id]:
                _fail("MATRIX_ROW_MISMATCH", row_id)
    if matrix["coverage"]["unique_rows"] != len(row_map) or matrix["coverage"]["duplicates"] != 0 or matrix["coverage"]["missing"] != 0 or matrix["coverage"]["extra"] != 0:
        _fail("MATRIX_COVERAGE", "coverage summary mismatch")
    if {row["candidate_bundle_id"] for row in matrix["rows"]} != set(bundles):
        _fail("BUNDLE_COVERAGE", "matrix bundle set mismatch")
    if {row["scenario_id"] for row in matrix["rows"]} != set(scenario_map):
        _fail("SCENARIO_COVERAGE", "matrix scenario set mismatch")
    selected_candidates = {
        candidate_id
        for row in matrix["rows"]
        for candidate_id in _bundle_candidates(bundles[row["candidate_bundle_id"]]).values()
    }
    if selected_candidates != set(candidates):
        _fail("CANDIDATE_COVERAGE", "matrix candidate set mismatch")
    matrix_gate_ids = {item["gate_id"] for row in matrix["rows"] for item in row["expected_gate_outcomes"]}
    if matrix_gate_ids != set(gates):
        _fail("MATRIX_GATE_COVERAGE", "matrix gate set mismatch")
    matrix_metric_ids = {metric_id for row in matrix["rows"] for metric_id in row["metric_set"]}
    if matrix_metric_ids != set(metrics):
        _fail("MATRIX_METRIC_COVERAGE", "matrix metric set mismatch")
    used_reason_codes = {
        str(code)
        for step in pipeline["steps"]
        for code in step["reason_codes"]
    }
    used_reason_codes.update(str(row["reason_code"]) for row in pipeline["uncertainty_state_machine"]["transition_table"])
    used_reason_codes.update(
        str(item["reason_code"])
        for row in matrix["rows"]
        for item in row["expected_gate_outcomes"]
    )
    if used_reason_codes != set(protocol["reason_code_registry"]):
        _fail("REASON_CODE_COVERAGE", f"missing={sorted(set(protocol['reason_code_registry']) - used_reason_codes)} extra={sorted(used_reason_codes - set(protocol['reason_code_registry']))}")
    for row in matrix["rows"]:
        identity = {key: row[key] for key in ("protocol_version", "pipeline_version", "candidate_bundle_id", "scenario_id", "review_member", "replay_direction", "replica", "seed", "expectation_rule_id")}
        expected_id = "ROW-" + canonical_digest(identity)
        if row["row_id"] != expected_id:
            _fail("ROW_ID_MISMATCH", str(row["row_id"]))
        if row["candidate_bundle_id"] not in bundles or row["scenario_id"] not in scenario_map:
            _fail("MATRIX_REFERENCE", str(row["row_id"]))
        if row["result_status"] != "NOT_RUN" or row["result"] != "NOT_AVAILABLE" or row["production_status"] != "RESEARCH_ONLY":
            _fail("RESULT_STATUS", str(row["row_id"]))
        scenario = scenario_map[row["scenario_id"]]
        if scenario["axis_mapping"]["review_pair_required"] and row["review_member"] not in REVIEW_MEMBERS:
            _fail("REVIEW_MEMBER_SOURCE_MISMATCH", str(row["row_id"]))
        if not scenario["axis_mapping"]["review_pair_required"] and row["review_member"] != "NOT_APPLICABLE":
            _fail("REVIEW_MEMBER_SOURCE_MISMATCH", str(row["row_id"]))
    protocol_flags = protocol["production_flags"]
    if any(protocol_flags.get(key) is True for key in ("negative_xp_allowed", "level_loss_allowed", "xp_debt_allowed", "winner_selected", "review_default_selected")):
        _fail("PROHIBITED_ECONOMY_FLAG", "negative XP, debt, level loss, winner and Review default remain prohibited")
    for flags in (protocol_flags, pipeline["production_flags"]):
        if any(flags.get(key) is True for key in ("screening_executed", "simulation_started", "g4_4_started", "production_approved", "production_integration")):
            _fail("PRODUCTION_OR_RESULTS_FLAG", "results/G4.4/production flags must remain false")
    if any(matrix[key] for key in ("screening_executed", "simulation_started", "g4_4_started", "production_approved")):
        _fail("PRODUCTION_OR_RESULTS_FLAG", "matrix flags must remain false")
    # Executable semantic differentiators.
    abrupt = evaluate_false_positive(0.32, 1.32, 0.0)
    stepped = evaluate_false_positive(0.32, 1.32, 0.75)
    if abrupt["context_loss_ratio"] != 1.0 or stepped["context_loss_ratio"] > 0.25:
        _fail("FALSE_POSITIVE_MATH", "control/pass differentiation failed")
    conversion = candidates["X-EQUALIZED-1_0-1_0"]
    daily = apply_daily(5.0, 1.0, "D-PER-DOMAIN-BOUNDED-MEDIUM")
    base = apply_cross_domain(daily["review_bounded"], 0.0, conversion, "D-PER-DOMAIN-BOUNDED-MEDIUM")["total_npu"]
    with_learn = apply_cross_domain(daily["review_bounded"], daily["learn_bounded"], conversion, "D-PER-DOMAIN-BOUNDED-MEDIUM")["total_npu"]
    if with_learn <= base:
        _fail("LEARN_MARGINAL_ZERO", "Learn marginal contribution must be positive below boundary")
    review_probe = apply_daily(1.0, 5.0, "D-PER-DOMAIN-BOUNDED-MEDIUM")
    learn_only = apply_cross_domain(0.0, review_probe["learn_bounded"], conversion, "D-PER-DOMAIN-BOUNDED-MEDIUM")["total_npu"]
    with_review = apply_cross_domain(review_probe["review_bounded"], review_probe["learn_bounded"], conversion, "D-PER-DOMAIN-BOUNDED-MEDIUM")["total_npu"]
    if with_review <= learn_only:
        _fail("REVIEW_MARGINAL_ZERO", "Review marginal contribution must be positive below boundary")
    control_daily = apply_daily(100.0, 0.0, "D-COMBINED-HARD-6-CONTROL")
    control_base = apply_cross_domain(control_daily["review_bounded"], 0.0, conversion, "D-COMBINED-HARD-6-CONTROL")
    control_plus_learn = apply_cross_domain(control_daily["review_bounded"], 1.0, conversion, "D-COMBINED-HARD-6-CONTROL")
    if control_base["total_npu"] != 6.0 or control_plus_learn["total_npu"] != 6.0 or control_plus_learn["review_component"] >= control_base["review_component"]:
        _fail("COMBINED_CONTROL_CROWDOUT", "combined-cap control must expose the prospectively expected crowdout")
    if nonlinear_componentwise_selected(1.0, 0.32, 0.75) == nonlinear_aggregate_first_prohibited(1.0, 0.32, 0.75):
        _fail("NONLINEAR_ORDER_DISTINCTION", "selected and prohibited nonlinear orders must differ")
    for scale in (1_000.0, 10_000.0, 1_000_000.0):
        bounded = apply_daily(scale, scale, "D-PER-DOMAIN-BOUNDED-MEDIUM")
        if bounded["review_bounded"] != 34.0 or bounded["learn_bounded"] != 10.0:
            _fail("DAILY_FINITE_BOUND", str(scale))
    step_60 = evaluate_review_source("P-STEP-ZERO", day=60, verified_base=1.0, positive_context=0.32)
    taper_60 = evaluate_review_source("P-TAPER-ZERO-30D", day=60, verified_base=1.0, positive_context=0.32)
    step_61 = evaluate_review_source("P-STEP-ZERO", day=61, verified_base=1.0, positive_context=0.32)
    taper_61 = evaluate_review_source("P-TAPER-ZERO-30D", day=61, verified_base=1.0, positive_context=0.32)
    if step_60["source_output"] != 1.0 or taper_60["source_output"] != 1.32:
        _fail("REVIEW_SOURCE_DAY_60", "G1 step/taper boundary drift")
    if step_61["source_output"] == taper_61["source_output"]:
        _fail("REVIEW_SOURCE_BOUNDARY_DIFFERENCE", "Review members must differ after day 60")
    uncertainty_state = "NORMAL"
    uncertainty_signals: list[str] = []
    for signal in ("CONFLICT", "CONFLICT", "NORMAL", "NORMAL"):
        transition = evaluate_uncertainty_transition(uncertainty_state, signal, uncertainty_signals)
        uncertainty_signals.append(signal)
        uncertainty_state = transition["next_state"]
    if uncertainty_state != "NORMAL":
        _fail("UNCERTAINTY_RECOVERY_SEQUENCE", uncertainty_state)
    if human_text is not None:
        required_human_tokens = [
            "G4.3 v1: `SUPERSEDED_PRE_EXECUTION`",
            "G4.3 v2: `SUPERSEDED_PRE_EXECUTION`",
            "G4.3 v3: `INVALIDATED_AFTER_SUBSTANTIVE_DEFECT`",
            "G4.3 v4: `FROZEN_PRE_SCREENING`",
            f"Primitive policies: **{len(candidates)}**",
            f"Candidate bundles: **{len(bundles)}**",
            f"Scenarios: **{len(scenario_map)}**",
            f"Matrix rows: **{len(row_map)}**",
            "M-FALSE-POSITIVE-CONTEXT-LOSS",
            "M-FALSE-POSITIVE-CUMULATIVE-LOSS",
            "NORMALIZE_COMPONENTS_SEPARATELY_AFTER_UNCERTAINTY",
            "D-PER-DOMAIN-BOUNDED-MEDIUM",
        ]
        for token in required_human_tokens:
            if token not in human_text:
                _fail("HUMAN_MACHINE_PARITY", token)


def _load_workspace(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = load_strict_json(root / PROTOCOL_PATH, max_bytes=16 * 1024 * 1024)
    pipeline = load_strict_json(root / PIPELINE_PATH, max_bytes=16 * 1024 * 1024)
    scenarios = load_strict_json(root / SCENARIOS_PATH, max_bytes=32 * 1024 * 1024)
    matrix = load_strict_json(root / MATRIX_PATH, max_bytes=64 * 1024 * 1024)
    corpus = load_strict_json(root / NEGATIVE_CORPUS_PATH, max_bytes=4 * 1024 * 1024)
    return protocol, pipeline, scenarios, matrix, corpus



def _pointer_parent(document: Any, pointer: str) -> tuple[Any, str]:
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]
    if not parts:
        _fail("NEGATIVE_POINTER", "root mutation is prohibited")
    current = document
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def _pointer_get(document: Any, pointer: str) -> Any:
    current = document
    for part in [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def apply_negative_sample(artifacts: Mapping[str, Mapping[str, Any]], human_text: str, sample: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], str]:
    mutated = {name: copy.deepcopy(dict(value)) for name, value in artifacts.items()}
    target = str(sample["target"])
    operation = str(sample["operation"])
    if target == "human":
        if operation != "replace":
            _fail("NEGATIVE_OPERATION", operation)
        return mutated, human_text.replace(str(sample["path"]), str(sample["value"]), 1)
    document = mutated[target]
    parent, key = _pointer_parent(document, str(sample["path"]))
    if operation == "set":
        if isinstance(parent, list): parent[int(key)] = copy.deepcopy(sample["value"])
        else: parent[key] = copy.deepcopy(sample["value"])
    elif operation == "delete":
        if isinstance(parent, list): del parent[int(key)]
        else: del parent[key]
    elif operation == "remove_index":
        container = _pointer_get(document, str(sample["path"]).rsplit("/", 1)[0])
        del container[int(key)]
    elif operation == "append_copy":
        container = _pointer_get(document, str(sample["path"]))
        container.append(copy.deepcopy(container[int(sample["value"])]))
    elif operation == "append_value":
        container = _pointer_get(document, str(sample["path"]))
        container.append(copy.deepcopy(sample["value"]))
    elif operation == "set_from":
        value = copy.deepcopy(_pointer_get(document, str(sample["value"])))
        if isinstance(parent, list): parent[int(key)] = value
        else: parent[key] = value
    else:
        _fail("NEGATIVE_OPERATION", operation)
    return mutated, human_text


def _refresh_negative_artifacts(
    artifacts: dict[str, dict[str, Any]],
    *,
    preserve_row_ids: bool = False,
) -> None:
    protocol = artifacts["protocol"]
    pipeline = artifacts["pipeline"]
    scenarios = artifacts["scenarios"]
    matrix = artifacts["matrix"]
    for _ in range(4):
        protocol["identity"]["artifact_digest"] = artifact_digest(protocol)
        pipeline["identity"]["artifact_digest"] = artifact_digest(pipeline)
        scenarios["protocol_digest"] = protocol["identity"]["artifact_digest"]
        scenarios["pipeline_digest"] = pipeline["identity"]["artifact_digest"]
        scenarios["identity"]["artifact_digest"] = artifact_digest(scenarios)
        matrix["protocol_digest"] = protocol["identity"]["artifact_digest"]
        matrix["pipeline_digest"] = pipeline["identity"]["artifact_digest"]
        matrix["scenario_registry_digest"] = scenarios["identity"]["artifact_digest"]
        for row in matrix["rows"]:
            row["protocol_digest"] = protocol["identity"]["artifact_digest"]
            row["pipeline_digest"] = pipeline["identity"]["artifact_digest"]
            row["scenario_registry_digest"] = scenarios["identity"]["artifact_digest"]
            if not preserve_row_ids:
                identity = {
                    key: row[key]
                    for key in (
                        "protocol_version",
                        "pipeline_version",
                        "candidate_bundle_id",
                        "scenario_id",
                        "review_member",
                        "replay_direction",
                        "replica",
                        "seed",
                        "expectation_rule_id",
                    )
                }
                row["row_id"] = "ROW-" + canonical_digest(identity)
        matrix["identity"]["artifact_digest"] = artifact_digest(matrix)
        protocol["artifact_registry"]["pipeline"]["digest"] = pipeline["identity"]["artifact_digest"]
        protocol["artifact_registry"]["scenarios"]["digest"] = scenarios["identity"]["artifact_digest"]
        protocol["artifact_registry"]["matrix"]["digest"] = matrix["identity"]["artifact_digest"]

def _validate_negative_artifacts(
    artifacts: Mapping[str, Mapping[str, Any]],
    schemas: Mapping[str, Mapping[str, Any]],
    human_text: str,
) -> None:
    for name in ("protocol", "pipeline", "scenarios", "matrix"):
        errors = sorted(
            Draft202012Validator(schemas[name]).iter_errors(artifacts[name]),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            _fail("SCHEMA_VALIDATION", f"{name}: {errors[0].message}")
    semantic_validate(
        artifacts["protocol"],
        artifacts["pipeline"],
        artifacts["scenarios"],
        artifacts["matrix"],
        human_text=human_text,
    )


def build_negative_corpus() -> dict[str, Any]:
    samples = [
        {"sample_id": "NEG-VERSION", "target": "protocol", "operation": "set", "path": "/identity/version", "value": 3, "expected_error_codes": ["V4_IDENTITY_MIX", "SCHEMA_VALIDATION"]},
        {"sample_id": "NEG-SUPERSESSION-RESULT-ACCESS", "target": "protocol", "operation": "set", "path": "/supersession/results_accessed_before_republication", "value": False, "expected_error_codes": ["SUPERSESSION_STATE"]},
        {"sample_id": "NEG-CONTROL-RECOMMENDATION", "target": "protocol", "operation": "set", "path": "/candidate_registry/2/recommendation_eligible", "value": True, "expected_error_codes": ["CONTROL_RECOMMENDATION"]},
        {"sample_id": "NEG-UNCERTAINTY-COMPONENT", "target": "pipeline", "operation": "set", "path": "/uncertainty_state_machine/affected_component", "value": "VERIFIED_BASE", "expected_error_codes": ["UNCERTAINTY_COMPONENT_SCOPE"]},
        {"sample_id": "NEG-REVIEW-BOUNDARY", "target": "protocol", "operation": "set", "path": "/review_axis/source_transition/retention_transition_day", "value": 61, "expected_error_codes": ["REVIEW_SOURCE_CONTRACT"]},
        {"sample_id": "NEG-EXPECTED-ZERO-CONTEXT", "target": "matrix", "operation": "set", "path": "/rows/0/expected_gate_outcomes/0/expected_outcome", "value": "CONTROL_EXPECTED_FAIL", "expected_error_codes": ["EXPECTED_OUTCOME_IDENTITY_RULE", "MATRIX_ROW_MISMATCH"]},
        {"sample_id": "NEG-CUMULATIVE-METRIC-COVERAGE", "target": "protocol", "operation": "delete", "path": "/metrics/2", "expected_error_codes": ["GATE_METRIC_REFERENCE", "METRIC_COVERAGE", "SCHEMA_VALIDATION"]},
        {"sample_id": "NEG-DAILY-UNBOUNDED-AST", "target": "protocol", "operation": "set", "path": "/candidate_registry/6/formula_ast/op", "value": "PER_DOMAIN_PIECEWISE", "expected_error_codes": ["DAILY_FINITE_BOUND_CONTRACT"]},
        {"sample_id": "NEG-MARGINAL-LEARN-LINK", "target": "protocol", "operation": "remove_index", "path": "/hard_gates/21/required_metric_ids/1", "value": None, "expected_error_codes": ["DUAL_DOMAIN_MARGINALITY_LINKAGE", "SCHEMA_VALIDATION"]},
        {"sample_id": "NEG-DUPLICATE-CANDIDATE", "target": "protocol", "operation": "append_copy", "path": "/candidate_registry", "value": 0, "expected_error_codes": ["DUPLICATE_CANDIDATE_ID", "SCHEMA_VALIDATION"]},
        {"sample_id": "NEG-RESULT-STATUS", "target": "matrix", "operation": "set", "path": "/rows/0/result_status", "value": "COMPLETE", "expected_error_codes": ["RESULT_STATUS"]},
        {"sample_id": "NEG-PRODUCTION-FLAG", "target": "protocol", "operation": "set", "path": "/production_flags/production_approved", "value": True, "expected_error_codes": ["PRODUCTION_OR_RESULTS_FLAG"]},
        {"sample_id": "NEG-LEARN-LIMITATION-ROW", "target": "matrix", "operation": "set", "path": "/rows/0/learn_limitation", "value": "NONE", "expected_error_codes": ["LEARN_LIMITATION_ROW", "MATRIX_ROW_MISMATCH"]},
        {"sample_id": "NEG-REVIEW-SOURCE-MEMBER", "target": "matrix", "operation": "set", "path": "/rows/0/review_source_trace/review_member", "value": "P-UNKNOWN", "expected_error_codes": ["REVIEW_SOURCE_TRACE", "MATRIX_ROW_MISMATCH"]},
        {"sample_id": "NEG-ROW-ID", "target": "matrix", "operation": "set", "path": "/rows/0/row_id", "value": "ROW-invalid", "preserve_mutated_row_ids": True, "expected_error_codes": ["ROW_ID_MISMATCH"]},
        {"sample_id": "NEG-HUMAN-PARITY", "target": "human", "operation": "replace", "path": "G4.3 v4: `FROZEN_PRE_SCREENING`", "value": "G4.3 v4: `BROKEN`", "expected_error_codes": ["HUMAN_MACHINE_PARITY"]},
        {"sample_id": "NEG-REASON-CODE-REGISTRY", "target": "protocol", "operation": "delete", "path": "/reason_code_registry/0", "expected_error_codes": ["REASON_CODE_COVERAGE", "SCHEMA_VALIDATION"]},
        {"sample_id": "NEG-HYPOTHESIS-COVERAGE", "target": "protocol", "operation": "delete", "path": "/hypotheses/0", "expected_error_codes": ["HYPOTHESIS_COVERAGE", "SCHEMA_VALIDATION"]},
    ]
    return {
        "identity": {
            "artifact_id": "core-economy-candidate-protocol-v4-negative-corpus",
            "version": 4,
            "generator_version": GENERATOR_VERSION,
        },
        "samples": samples,
    }


def run_negative_corpus(root: Path, repository_root: Path) -> dict[str, Any]:
    corpus = load_strict_json(root / NEGATIVE_CORPUS_PATH, max_bytes=4 * 1024 * 1024)
    canonical = build_all()
    schemas = build_schemas(canonical)
    human_text = (repository_root / HUMAN_PROTOCOL_REPOSITORY_PATH).read_text(encoding="utf-8")
    rejected: list[str] = []
    for sample in corpus["samples"]:
        mutated, mutated_human = apply_negative_sample(canonical, human_text, sample)
        if not bool(sample.get("preserve_mutated_digest", False)) and sample["target"] != "human":
            _refresh_negative_artifacts(
                mutated,
                preserve_row_ids=bool(sample.get("preserve_mutated_row_ids", False)),
            )
        expected_codes = set(sample["expected_error_codes"])
        try:
            _validate_negative_artifacts(mutated, schemas, mutated_human)
        except ProtocolValidationError as exc:
            if exc.code not in expected_codes:
                _fail(
                    "NEGATIVE_UNEXPECTED_ERROR",
                    f"{sample['sample_id']}: expected {sorted(expected_codes)}, got {exc.code}: {exc}",
                )
            rejected.append(str(sample["sample_id"]))
        except Exception as exc:
            _fail("NEGATIVE_UNEXPECTED_EXCEPTION", f"{sample['sample_id']}: {type(exc).__name__}: {exc}")
        else:
            _fail("NEGATIVE_SAMPLE_ACCEPTED", str(sample["sample_id"]))
    expected_count = len(build_negative_corpus()["samples"])
    if len(rejected) != expected_count:
        _fail("NEGATIVE_CORPUS_EXECUTION", f"expected {expected_count} rejections, found {len(rejected)}")
    return {"negative_samples": len(rejected), "negative_corpus": "PASS"}


def validate_historical_immutability(root: Path) -> None:
    for relative, expected in HISTORICAL_SHA256.items():
        path = root / Path(relative)
        if not path.is_file():
            _fail("HISTORICAL_ARTIFACT_MISSING", relative)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            _fail("HISTORICAL_ARTIFACT_MUTATED", f"{relative}: expected {expected}, actual {actual}")
    source_pairs = {
        G1_SOURCE_IDENTITIES["implementation_path"]: G1_SOURCE_IDENTITIES["implementation_sha256"],
        G1_SOURCE_IDENTITIES["protocol_path"]: G1_SOURCE_IDENTITIES["protocol_sha256"],
        G2_SOURCE_IDENTITIES["allocation_path"]: G2_SOURCE_IDENTITIES["allocation_sha256"],
        G2_SOURCE_IDENTITIES["candidate_protocol_path"]: G2_SOURCE_IDENTITIES["candidate_protocol_sha256"],
        G2_SOURCE_IDENTITIES["confirmatory_protocol_path"]: G2_SOURCE_IDENTITIES["confirmatory_protocol_sha256"],
    }
    for relative, expected in source_pairs.items():
        actual = hashlib.sha256((root / Path(relative)).read_bytes()).hexdigest()
        if actual != expected:
            _fail("SOURCE_CONTRACT_IDENTITY_MISMATCH", f"{relative}: expected {expected}, actual {actual}")

def validate_workspace(root: Path, *, repository_root: Path | None = None) -> dict[str, Any]:
    protocol, pipeline, scenarios, matrix, corpus = _load_workspace(root)
    schema_pairs = [
        (PROTOCOL_SCHEMA_PATH, protocol),
        (PIPELINE_SCHEMA_PATH, pipeline),
        (SCENARIOS_SCHEMA_PATH, scenarios),
        (MATRIX_SCHEMA_PATH, matrix),
    ]
    for schema_path, artifact in schema_pairs:
        schema = load_strict_json(root / schema_path, max_bytes=32 * 1024 * 1024)
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(artifact), key=lambda error: list(error.absolute_path))
        if errors:
            _fail("SCHEMA_VALIDATION", f"{schema_path}: {errors[0].message}")
    human_text = None
    if repository_root is not None:
        human_path = repository_root / HUMAN_PROTOCOL_REPOSITORY_PATH
        human_text = human_path.read_text(encoding="utf-8")
    semantic_validate(protocol, pipeline, scenarios, matrix, human_text=human_text)
    validate_historical_immutability(root)
    expected_negative_count = len(build_negative_corpus()["samples"])
    negative_summary = run_negative_corpus(root, repository_root) if repository_root is not None else {"negative_samples": expected_negative_count, "negative_corpus": "NOT_EXECUTED_WITHOUT_REPOSITORY_ROOT"}
    if corpus["identity"]["version"] != 4 or corpus != build_negative_corpus():
        _fail("NEGATIVE_CORPUS_COUNT", "v4 negative corpus must be byte-derived from generator")
    _unique(corpus["samples"], "sample_id", "DUPLICATE_NEGATIVE_SAMPLE")
    return {
        "protocol_digest": protocol["identity"]["artifact_digest"],
        "pipeline_digest": pipeline["identity"]["artifact_digest"],
        "scenario_digest": scenarios["identity"]["artifact_digest"],
        "matrix_digest": matrix["identity"]["artifact_digest"],
        "candidate_count": len(protocol["candidate_registry"]),
        "bundle_count": len(protocol["candidate_bundles"]),
        "hypothesis_count": len(protocol["hypotheses"]),
        "gate_count": len(protocol["hard_gates"]),
        "metric_count": len(protocol["metrics"]),
        "scenario_count": len(scenarios["scenarios"]),
        "row_count": len(matrix["rows"]),
        "negative_sample_count": len(corpus["samples"]),
        **negative_summary,
    }


def write_generated(root: Path) -> dict[str, Any]:
    artifacts = build_all()
    schemas = build_schemas(artifacts)
    targets = {
        PROTOCOL_PATH: artifacts["protocol"],
        PIPELINE_PATH: artifacts["pipeline"],
        SCENARIOS_PATH: artifacts["scenarios"],
        MATRIX_PATH: artifacts["matrix"],
        PROTOCOL_SCHEMA_PATH: schemas["protocol"],
        PIPELINE_SCHEMA_PATH: schemas["pipeline"],
        SCENARIOS_SCHEMA_PATH: schemas["scenarios"],
        MATRIX_SCHEMA_PATH: schemas["matrix"],
        NEGATIVE_CORPUS_PATH: build_negative_corpus(),
    }
    for relative, value in targets.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical_bytes(value))
    return {
        "protocol_digest": artifacts["protocol"]["identity"]["artifact_digest"],
        "pipeline_digest": artifacts["pipeline"]["identity"]["artifact_digest"],
        "scenario_digest": artifacts["scenarios"]["identity"]["artifact_digest"],
        "matrix_digest": artifacts["matrix"]["identity"]["artifact_digest"],
        "candidate_count": len(artifacts["protocol"]["candidate_registry"]),
        "bundle_count": len(artifacts["protocol"]["candidate_bundles"]),
        "hypothesis_count": len(artifacts["protocol"]["hypotheses"]),
        "gate_count": len(artifacts["protocol"]["hard_gates"]),
        "metric_count": len(artifacts["protocol"]["metrics"]),
        "scenario_count": len(artifacts["scenarios"]["scenarios"]),
        "row_count": len(artifacts["matrix"]["rows"]),
    }


def check_byte_identical(root: Path) -> None:
    artifacts = build_all()
    schemas = build_schemas(artifacts)
    targets = {
        PROTOCOL_PATH: artifacts["protocol"], PIPELINE_PATH: artifacts["pipeline"], SCENARIOS_PATH: artifacts["scenarios"], MATRIX_PATH: artifacts["matrix"],
        PROTOCOL_SCHEMA_PATH: schemas["protocol"], PIPELINE_SCHEMA_PATH: schemas["pipeline"], SCENARIOS_SCHEMA_PATH: schemas["scenarios"], MATRIX_SCHEMA_PATH: schemas["matrix"],
        NEGATIVE_CORPUS_PATH: build_negative_corpus(),
    }
    for relative, value in targets.items():
        expected = _canonical_bytes(value)
        actual = (root / relative).read_bytes()
        if actual != expected:
            _fail("BYTE_IDENTICAL_REGENERATION", str(relative))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate the G4.3 v4 replacement pre-screening republication")
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--check-byte-identical", action="store_true")
    args = parser.parse_args(argv)
    root = args.research_root.resolve()
    summary: dict[str, Any] = {}
    if args.regenerate:
        summary.update(write_generated(root))
    if args.check_byte_identical:
        check_byte_identical(root)
        summary["byte_identical_regeneration"] = "PASS"
    if args.validate:
        summary.update(validate_workspace(root, repository_root=args.repository_root.resolve() if args.repository_root else None))
        summary["validation"] = "PASS"
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
