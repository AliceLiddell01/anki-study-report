from __future__ import annotations

import copy
import inspect
import json
import math
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from gamification_sim.review_candidate_mechanisms import (
    FROZEN_REVIEW_CANDIDATES,
    REFERENCE_PARAMETERIZATION_ID,
    RewardExecutionContext,
    frozen_review_candidate,
    frozen_review_candidate_payload,
    memory_gain_multiplier,
    validate_frozen_review_candidate_protocol,
)


ROOT = Path(__file__).parents[1]
CONTRACT = (
    ROOT
    / "contracts"
    / "review-xp-candidate-protocol-v1.json"
)

CANDIDATE_IDS = (
    "P-STEP-ZERO",
    "P-STEP-NEUTRAL-RATIO",
    "P-TAPER-ZERO-30D",
    "P-TAPER-NEUTRAL-RATIO-30D",
)


def cycling_context(day: int) -> RewardExecutionContext:
    return RewardExecutionContext(
        day=day,
        retention_transition_days=(30, 60),
    )


def test_registry_contains_exact_frozen_parameterizations_in_order():
    assert tuple(
        candidate.parameterization_id
        for candidate in FROZEN_REVIEW_CANDIDATES
    ) == CANDIDATE_IDS
    assert len({item.parameterization_id for item in FROZEN_REVIEW_CANDIDATES}) == 4


def test_registry_contains_two_families_with_two_parameterizations_each():
    counts: dict[str, int] = {}
    for candidate in FROZEN_REVIEW_CANDIDATES:
        counts[candidate.family_id] = counts.get(candidate.family_id, 0) + 1
        assert candidate.base_parameter_set_id == REFERENCE_PARAMETERIZATION_ID

    assert counts == {
        "F-POST-TRANSITION-MG-STEP": 2,
        "F-POST-TRANSITION-MG-TAPER": 2,
    }


def test_registry_uses_exact_frozen_values():
    expected = {
        "P-STEP-ZERO": (0.0, 60, None),
        "P-STEP-NEUTRAL-RATIO": (
            0.8333333333333334,
            60,
            None,
        ),
        "P-TAPER-ZERO-30D": (0.0, 60, 30),
        "P-TAPER-NEUTRAL-RATIO-30D": (
            0.8333333333333334,
            60,
            30,
        ),
    }

    assert {
        item.parameterization_id: (
            item.endpoint_multiplier,
            item.post_transition_start_day,
            item.transition_taper_days,
        )
        for item in FROZEN_REVIEW_CANDIDATES
    } == expected


def test_candidate_identity_is_deterministic_and_unique():
    first = tuple(
        frozen_review_candidate_payload(identifier)
        for identifier in CANDIDATE_IDS
    )
    second = tuple(
        frozen_review_candidate_payload(identifier)
        for identifier in CANDIDATE_IDS
    )

    assert first == second
    assert len({item["digest"] for item in first}) == 4


def test_candidate_instances_are_frozen():
    candidate = frozen_review_candidate("P-STEP-ZERO")

    with pytest.raises(FrozenInstanceError):
        candidate.endpoint_multiplier = 0.5  # type: ignore[misc]


@pytest.mark.parametrize(
    "bad",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        -0.01,
        1.01,
        True,
    ],
)
def test_candidate_rejects_invalid_endpoint_multiplier(bad):
    candidate = frozen_review_candidate("P-STEP-ZERO")

    with pytest.raises(ValueError):
        replace(candidate, endpoint_multiplier=bad)


def test_unknown_candidate_is_rejected():
    with pytest.raises(
        ValueError,
        match="unknown frozen Review parameterization",
    ):
        frozen_review_candidate("P-UNREGISTERED")


def test_multiplier_api_has_no_numeric_override_argument():
    assert tuple(inspect.signature(memory_gain_multiplier).parameters) == (
        "parameterization_id",
        "context",
    )


def test_machine_contract_matches_registry():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    validate_frozen_review_candidate_protocol(payload)


def test_relevant_machine_contract_drift_fails_closed():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    drifted = copy.deepcopy(payload)
    drifted["parameterizations"][0]["parameter_values"][
        "post_transition_memory_gain_multiplier"
    ] = 0.5

    with pytest.raises(
        ValueError,
        match="parameterizations drifted",
    ):
        validate_frozen_review_candidate_protocol(drifted)


@pytest.mark.parametrize(
    ("candidate_id", "endpoint"),
    [
        ("P-STEP-ZERO", 0.0),
        (
            "P-STEP-NEUTRAL-RATIO",
            0.8333333333333334,
        ),
    ],
)
@pytest.mark.parametrize("day", [60, 61, 75, 89, 90, 91, 365])
def test_step_uses_endpoint_on_and_after_day_60(
    candidate_id,
    endpoint,
    day,
):
    assert memory_gain_multiplier(
        candidate_id,
        cycling_context(day),
    ) == pytest.approx(endpoint)


@pytest.mark.parametrize(
    "candidate_id",
    [
        "P-STEP-ZERO",
        "P-STEP-NEUTRAL-RATIO",
    ],
)
def test_step_is_identity_before_day_60(candidate_id):
    assert memory_gain_multiplier(
        candidate_id,
        cycling_context(59),
    ) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("candidate_id", "endpoint"),
    [
        ("P-TAPER-ZERO-30D", 0.0),
        (
            "P-TAPER-NEUTRAL-RATIO-30D",
            0.8333333333333334,
        ),
    ],
)
@pytest.mark.parametrize("day", [59, 60, 61, 75, 89, 90, 91, 365])
def test_taper_uses_frozen_linear_boundary_semantics(
    candidate_id,
    endpoint,
    day,
):
    if day <= 60:
        expected = 1.0
    elif day >= 90:
        expected = endpoint
    else:
        progress = (day - 60) / 30
        expected = 1.0 + progress * (endpoint - 1.0)

    assert memory_gain_multiplier(
        candidate_id,
        cycling_context(day),
    ) == pytest.approx(expected)


@pytest.mark.parametrize("candidate_id", CANDIDATE_IDS)
@pytest.mark.parametrize(
    "context",
    [
        RewardExecutionContext(day=365),
        RewardExecutionContext(
            day=365,
            retention_transition_days=(30,),
        ),
    ],
)
def test_non_applicable_policy_is_identity(candidate_id, context):
    assert memory_gain_multiplier(
        candidate_id,
        context,
    ) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "parameterization_id",
    [None, REFERENCE_PARAMETERIZATION_ID],
)
def test_reference_path_is_identity_without_context(parameterization_id):
    assert memory_gain_multiplier(parameterization_id) == pytest.approx(1.0)


def test_candidate_requires_execution_context():
    with pytest.raises(
        ValueError,
        match="requires an execution context",
    ):
        memory_gain_multiplier("P-STEP-ZERO")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"day": -1},
        {"day": True},
        {
            "day": 60,
            "retention_transition_days": [30, 60],
        },
        {
            "day": 60,
            "retention_transition_days": (60, 30),
        },
        {
            "day": 60,
            "retention_transition_days": (30, 30),
        },
        {
            "day": 60,
            "retention_transition_days": (0, 60),
        },
    ],
)
def test_execution_context_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        RewardExecutionContext(**kwargs)


def test_neutral_ratio_is_exact_source_derived_value():
    expected = 0.10 / 0.12

    assert frozen_review_candidate(
        "P-STEP-NEUTRAL-RATIO"
    ).endpoint_multiplier == expected
    assert math.isfinite(expected)
