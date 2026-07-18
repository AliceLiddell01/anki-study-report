from __future__ import annotations

import json
from dataclasses import replace

import pytest
from hypothesis import given, settings, strategies as st

from gamification_sim.canonical_json import canonical_digest, canonical_dumps
from gamification_sim.day_aggregation import aggregate_day
from gamification_sim.episode_reward import evaluate_episode
from gamification_sim.models import (
    CompletionStatus,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    Source,
    SupplementalInput,
    SupportEventInput,
    SupportKind,
    WorkloadSnapshot,
)
from gamification_sim.parameter_catalog import (
    CORRECTED_PARETO_PARAMETER_SET_IDS,
    PARAMETER_CANDIDATES,
    candidate_payload,
    compose_parameter_candidates,
    normalized_parameter_digest,
    parameter_candidate,
)
from gamification_sim.parameters import CURRENT_PARAMETERS, RewardParameterSet
from gamification_sim.scenario_loader import ScenarioDomainError, validate_definition
from gamification_sim.scenario_models import ScenarioCategory, ScenarioDay, ScenarioDefinition
from gamification_sim.strict_json import StrictJsonError, loads_strict
from gamification_sim.sweep import SENSITIVITY_GRIDS, _sensitivity_variant
from gamification_sim.validation import close, require_non_negative_int


PROPERTY_SETTINGS = settings(
    max_examples=40,
    database=None,
    derandomize=True,
    deadline=None,
    print_blob=True,
)

def _composite(identifier: str) -> RewardParameterSet:
    parts = tuple(parameter_candidate(item) for item in identifier.split("+"))
    return parts[0].parameters if len(parts) == 1 else compose_parameter_candidates(parts).parameters


def _verified_parameter_cases():
    candidates = [(item.parameter_set_id, item.parameters) for item in PARAMETER_CANDIDATES]
    candidates.extend(
        (identifier, _composite(identifier))
        for identifier in CORRECTED_PARETO_PARAMETER_SET_IDS
    )
    for name, values in SENSITIVITY_GRIDS.items():
        for value in (values[0], values[-1]):
            candidates.append((f"sensitivity-{name}-{value:g}", _sensitivity_variant(CURRENT_PARAMETERS, name, value)))
    unique = {}
    for identifier, params in candidates:
        unique.setdefault(normalized_parameter_digest(params), (identifier, params))
    return tuple(pytest.param(params, id=identifier) for identifier, params in unique.values())


VERIFIED_PARAMETERS = _verified_parameter_cases()


def episode(index: int, *, outcome: Outcome = Outcome.GOOD) -> ReviewEpisodeInput:
    return ReviewEpisodeInput(
        source_event_key=f"event-{index}",
        card_lineage=f"card-{index}",
        anki_day="2026-01-01",
        outcome=outcome,
    )


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(first=st.integers(min_value=0, max_value=40), extra=st.integers(min_value=0, max_value=40))
def test_h01_h10_unique_core_baseline_is_monotonic_without_daily_diminishing_returns(params, first, extra):
    before = aggregate_day(ReviewDayInput("2026-01-01", tuple(episode(i) for i in range(first))), params)
    after = aggregate_day(ReviewDayInput("2026-01-01", tuple(episode(i) for i in range(first + extra))), params)
    expected_increment = extra * (params.attempt_credit + params.outcome_credit)
    assert close(after.core_baseline - before.core_baseline, expected_increment)


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(boundary=st.integers(min_value=0, max_value=30), count=st.integers(min_value=0, max_value=60))
def test_h05_session_partition_is_analytical_only(params, boundary, count):
    episodes = tuple(episode(i) for i in range(count))
    one = aggregate_day(ReviewDayInput("2026-01-01", episodes, session_ids=("one",)), params)
    split_ids = ("first", "second") if boundary < count else ("first",)
    split = aggregate_day(ReviewDayInput("2026-01-01", episodes, session_ids=split_ids), params)
    assert one.total == split.total


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(replays=st.integers(min_value=1, max_value=25), same_card=st.integers(min_value=1, max_value=25))
def test_h02_h03_source_replay_and_card_day_are_idempotent(params, replays, same_card):
    base = episode(0)
    events = (base,) * replays + tuple(
        replace(base, source_event_key=f"alias-{index}") for index in range(same_card)
    )
    result = aggregate_day(ReviewDayInput("2026-01-01", events), params)
    assert len(result.episode_breakdowns) == 1
    assert close(result.total, evaluate_episode(base, params).total)


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(count=st.integers(min_value=1, max_value=50))
def test_h04_undo_reverses_exact_selected_events(params, count):
    episodes = tuple(episode(i) for i in range(count))
    undone = frozenset(item.source_event_key for item in episodes)
    result = aggregate_day(ReviewDayInput("2026-01-01", episodes, undone_source_event_keys=undone), params)
    assert result.total == 0


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(outcome=st.sampled_from((Outcome.HARD, Outcome.GOOD, Outcome.EASY)))
def test_h06_h07_success_buttons_are_neutral_and_validity_cannot_add_reward(params, outcome):
    base = episode(0, outcome=outcome)
    totals = [evaluate_episode(replace(base, outcome=item), params).total for item in (Outcome.HARD, Outcome.GOOD, Outcome.EASY)]
    assert totals[0] == totals[1] == totals[2]
    assert evaluate_episode(replace(base, response_validity=0.0), params).total <= totals[0]


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(preview=st.booleans())
def test_h08_h09_manual_and_preview_operations_are_zero(params, preview):
    base = episode(0)
    changed = replace(
        base,
        administrative=not preview,
        source=Source.MANUAL_OPERATION if not preview else base.source,
        preview_without_rescheduling=preview,
    )
    assert aggregate_day(ReviewDayInput("2026-01-01", (changed,)), params).total == 0


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(count=st.integers(min_value=0, max_value=100))
def test_h11_support_episode_and_day_caps_hold(params, count):
    parent = episode(0)
    support = tuple(
        SupportEventInput(f"support-{index}", parent.source_event_key, SupportKind.INTERDAY_RECOVERY)
        for index in range(count)
    )
    result = aggregate_day(ReviewDayInput("2026-01-01", (parent,), support_events=support), params)
    assert result.capped_support <= result.support_cap + 1e-9
    assert result.capped_support <= params.support_day_cap + 1e-9


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(count=st.integers(min_value=0, max_value=100), units=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False))
def test_h12_supplemental_cap_holds(params, count, units):
    supplemental = tuple(SupplementalInput(f"supp-{index}", units) for index in range(count))
    result = aggregate_day(ReviewDayInput("2026-01-01", (episode(0),), supplemental_events=supplemental), params)
    assert result.capped_supplemental <= params.supplemental_day_cap + 1e-9


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(count=st.integers(min_value=0, max_value=350), status=st.sampled_from(tuple(CompletionStatus)))
def test_h13_h14_volume_and_completion_caps_hold(params, count, status):
    result = aggregate_day(
        ReviewDayInput(
            "2026-01-01",
            tuple(episode(i) for i in range(count)),
            workload=WorkloadSnapshot(status=status, natural_due_at_start=count),
        ),
        params,
    )
    assert result.volume_credit <= params.volume_cap + 1e-9
    assert result.completion_credit <= params.completion_cap + 1e-9
    if status is CompletionStatus.ZERO_DUE:
        assert result.completion_credit == 0


@pytest.mark.parametrize("params", VERIFIED_PARAMETERS)
@PROPERTY_SETTINGS
@given(count=st.integers(min_value=0, max_value=80))
def test_h16_h17_h18_totals_are_nonnegative_explainable_and_deterministic(params, count):
    day = ReviewDayInput("2026-01-01", tuple(episode(i) for i in range(count)))
    first = aggregate_day(day, params)
    second = aggregate_day(day, params)
    assert first == second
    assert first.total >= 0
    assert close(
        first.total,
        first.core_baseline + first.core_context + first.capped_support
        + first.capped_supplemental + first.volume_credit + first.completion_credit,
    )


@PROPERTY_SETTINGS
@given(candidate=st.sampled_from(PARAMETER_CANDIDATES))
def test_candidate_serialization_roundtrip_and_canonical_digest_are_stable(candidate):
    payload = candidate_payload(candidate)
    roundtrip = json.loads(json.dumps(payload, sort_keys=True, allow_nan=False))
    assert roundtrip == payload
    assert canonical_dumps(payload) == canonical_dumps(roundtrip)
    assert canonical_digest(payload) == canonical_digest(roundtrip)


@PROPERTY_SETTINGS
@given(value=st.sampled_from((float("nan"), float("inf"), float("-inf"), -1.0, True)))
def test_invalid_numeric_parameter_ranges_are_rejected(value):
    with pytest.raises((TypeError, ValueError)):
        RewardParameterSet(volume_cap=value)


@PROPERTY_SETTINGS
@given(points=st.lists(st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False), min_size=2, max_size=8))
def test_non_monotonic_parameter_anchors_are_rejected(points):
    anchors = tuple((point, 0.1) for point in sorted(points, reverse=True))
    with pytest.raises((TypeError, ValueError)):
        RewardParameterSet(challenge_anchors=anchors)


@PROPERTY_SETTINGS
@given(value=st.sampled_from((True, False, -1, -100, 1.5)))
def test_bool_as_int_and_negative_counts_are_rejected(value):
    with pytest.raises(ValueError):
        require_non_negative_int("count", value)


@PROPERTY_SETTINGS
@given(key=st.text(alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=12))
def test_duplicate_json_keys_are_rejected(key):
    encoded = json.dumps(key)
    with pytest.raises(StrictJsonError, match="duplicate object key"):
        loads_strict("{" + f"{encoded}:1,{encoded}:2" + "}")


def test_unknown_enums_unsorted_days_and_duplicate_scenario_ids_are_rejected():
    with pytest.raises(ValueError):
        Outcome("unknown")
    day_late = ScenarioDay("2026-01-02", (), ReviewDayInput("2026-01-02"))
    day_early = ScenarioDay("2026-01-01", (), ReviewDayInput("2026-01-01"))
    definition = ScenarioDefinition(
        "review-scenario-v0.2", "unsorted", "Unsorted", ScenarioCategory.EDGE,
        "review-v0.1", "Unsorted days", (), (day_late, day_early), (),
    )
    with pytest.raises(ScenarioDomainError, match="strictly increasing"):
        validate_definition(definition)
