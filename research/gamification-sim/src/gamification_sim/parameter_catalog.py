from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any

from .canonical_json import canonical_digest
from .models import ConfidenceLevel
from .parameters import CURRENT_PARAMETERS, RewardParameterSet
from .validation import dataclass_to_dict


@dataclass(frozen=True, slots=True)
class ParameterCandidate:
    parameter_set_id: str
    rule_version: str
    family: str
    base_parameter_set_id: str | None
    rationale: str
    changed_fields: tuple[str, ...]
    parameters: RewardParameterSet
    digest: str


def _candidate(
    parameter_set_id: str,
    family: str,
    base_parameter_set_id: str | None,
    rationale: str,
    **changes: Any,
) -> ParameterCandidate:
    rule_version = (
        CURRENT_PARAMETERS.rule_version
        if parameter_set_id == "R-CURRENT"
        else f"{CURRENT_PARAMETERS.rule_version}+{parameter_set_id.lower()}"
    )
    parameters = replace(CURRENT_PARAMETERS, rule_version=rule_version, **changes)
    changed_fields = tuple(sorted(changes))
    payload = {
        "parameter_set_id": parameter_set_id,
        "rule_version": rule_version,
        "family": family,
        "base_parameter_set_id": base_parameter_set_id,
        "rationale": rationale,
        "changed_fields": list(changed_fields),
        "parameter_snapshot": dataclass_to_dict(parameters),
    }
    return ParameterCandidate(
        parameter_set_id=parameter_set_id,
        rule_version=rule_version,
        family=family,
        base_parameter_set_id=base_parameter_set_id,
        rationale=rationale,
        changed_fields=changed_fields,
        parameters=parameters,
        digest=canonical_digest(payload),
    )


def _scaled_challenge(maximum: float) -> tuple[tuple[float, float], ...]:
    current_max = max(value for _, value in CURRENT_PARAMETERS.challenge_anchors)
    return tuple(
        (point, value * maximum / current_max)
        for point, value in CURRENT_PARAMETERS.challenge_anchors
    )


PARAMETER_CANDIDATES: tuple[ParameterCandidate, ...] = (
    _candidate(
        "R-CURRENT",
        "reward",
        None,
        "Immutable review-v0.1 baseline.",
    ),
    _candidate(
        "R-NO-GAIN",
        "reward",
        "R-CURRENT",
        "Remove MemoryGainCredit while preserving challenge and baseline.",
        memory_gain_cap=0.0,
    ),
    _candidate(
        "R-LOW-CHALLENGE",
        "reward",
        "R-CURRENT",
        "Reduce retrieval challenge amplitude to test backlog sensitivity.",
        challenge_anchors=_scaled_challenge(0.20),
        low_retrievability_credit=0.07,
    ),
    _candidate(
        "R-NEUTRAL-CONTEXT",
        "reward",
        "R-CURRENT",
        "Use the neutral context benchmark without FSRS-driven variation.",
        confidence_values=tuple((level, 0.0) for level in ConfidenceLevel),
        memory_gain_cap=0.0,
    ),
    _candidate("V-CURRENT", "volume", "R-CURRENT", "Keep current volume tiers and cap."),
    _candidate(
        "V-LOW-CAP",
        "volume",
        "V-CURRENT",
        "Keep current volume tiers with a lower maximum bonus.",
        volume_cap=10.0,
    ),
    _candidate(
        "V-SOFT",
        "volume",
        "V-CURRENT",
        "Use lower marginal volume rates while preserving thresholds.",
        volume_tiers=((10.0, 0.03, 25.0), (25.0, 0.05, 50.0), (50.0, 0.07, 100.0), (100.0, 0.08, None)),
    ),
    _candidate(
        "V-NONE",
        "volume",
        "V-CURRENT",
        "Disable numeric VolumeCredit for a no-volume benchmark.",
        volume_tiers=tuple((start, 0.0, end) for start, _, end in CURRENT_PARAMETERS.volume_tiers),
        volume_cap=0.0,
    ),
    _candidate("C-CURRENT", "completion", "R-CURRENT", "Keep current completion reward."),
    _candidate(
        "C-LOW",
        "completion",
        "C-CURRENT",
        "Reduce completion rate and cap.",
        completion_rate=0.02,
        completion_cap=2.0,
    ),
    _candidate(
        "C-SYMBOLIC",
        "completion",
        "C-CURRENT",
        "Retain completion status while removing numeric reward.",
        completion_rate=0.0,
        completion_cap=0.0,
    ),
    _candidate("S-CURRENT", "support", "R-CURRENT", "Keep current support caps."),
    _candidate(
        "S-LOW",
        "support",
        "S-CURRENT",
        "Lower the daily support allowance.",
        support_day_floor=0.25,
        support_day_rate=0.075,
        support_day_cap=2.0,
    ),
    _candidate(
        "S-EPISODE-ONLY",
        "support",
        "S-CURRENT",
        "Limit support to approximately one episode cap per day.",
        support_day_floor=0.12,
        support_day_rate=0.0,
        support_day_cap=0.12,
    ),
    _candidate("P-CURRENT", "supplemental", "R-CURRENT", "Keep current supplemental caps."),
    _candidate(
        "P-LOW",
        "supplemental",
        "P-CURRENT",
        "Reduce supplemental rate and cap.",
        supplemental_day_rate=0.015,
        supplemental_day_cap=1.0,
    ),
    _candidate(
        "P-METRIC-ONLY",
        "supplemental",
        "P-CURRENT",
        "Track supplemental activity without permanent Review Units.",
        supplemental_day_rate=0.0,
        supplemental_day_cap=0.0,
    ),
)


CORRECTED_PARETO_PARAMETER_SET_IDS = (
    "R-CURRENT",
    "R-CURRENT+V-CURRENT+C-CURRENT+S-EPISODE-ONLY",
    "R-CURRENT+V-CURRENT+C-LOW",
    "R-CURRENT+V-CURRENT+C-LOW+S-EPISODE-ONLY",
    "R-CURRENT+V-CURRENT+C-SYMBOLIC",
    "R-CURRENT+V-NONE",
    "R-CURRENT+V-NONE+C-LOW",
    "R-CURRENT+V-NONE+C-SYMBOLIC",
    "R-CURRENT+V-SOFT",
    "R-LOW-CHALLENGE",
    "R-LOW-CHALLENGE+V-NONE",
    "R-LOW-CHALLENGE+V-SOFT",
    "R-NEUTRAL-CONTEXT",
    "R-NO-GAIN",
)


_BY_ID = {candidate.parameter_set_id: candidate for candidate in PARAMETER_CANDIDATES}
if len(_BY_ID) != len(PARAMETER_CANDIDATES):  # pragma: no cover - import-time contract
    raise RuntimeError("parameter candidate IDs must be unique")


def parameter_candidate(parameter_set_id: str) -> ParameterCandidate:
    try:
        return _BY_ID[parameter_set_id]
    except KeyError as exc:
        raise ValueError(f"unknown parameter set: {parameter_set_id}") from exc


def candidate_payload(candidate: ParameterCandidate) -> dict[str, Any]:
    return {
        "parameter_set_id": candidate.parameter_set_id,
        "rule_version": candidate.rule_version,
        "family": candidate.family,
        "base_parameter_set_id": candidate.base_parameter_set_id,
        "rationale": candidate.rationale,
        "changed_fields": list(candidate.changed_fields),
        "parameter_snapshot": dataclass_to_dict(candidate.parameters),
        "digest": candidate.digest,
        "normalized_parameter_digest": normalized_parameter_digest(candidate.parameters),
    }


def normalized_parameter_digest(params: RewardParameterSet) -> str:
    payload = dataclass_to_dict(params)
    payload.pop("rule_version", None)
    return canonical_digest(payload)


def compose_parameter_candidates(
    candidates: tuple[ParameterCandidate, ...],
) -> ParameterCandidate:
    if not candidates:
        raise ValueError("at least one parameter candidate is required")
    identifiers = tuple(candidate.parameter_set_id for candidate in candidates)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("composite parameter candidate IDs must be unique")
    params = CURRENT_PARAMETERS
    changed: set[str] = set()
    for candidate in candidates:
        changes = {
            field.name: getattr(candidate.parameters, field.name)
            for field in fields(RewardParameterSet)
            if field.name in candidate.changed_fields
        }
        params = replace(params, **changes)
        changed.update(changes)
    parameter_set_id = "+".join(identifiers)
    rule_version = f"{CURRENT_PARAMETERS.rule_version}+{parameter_set_id.lower()}"
    params = replace(params, rule_version=rule_version)
    payload = {
        "parameter_set_id": parameter_set_id,
        "rule_version": rule_version,
        "family": "composite",
        "base_parameter_set_id": "R-CURRENT",
        "rationale": "Sequential family overlay: " + ", ".join(identifiers),
        "changed_fields": sorted(changed),
        "parameter_snapshot": dataclass_to_dict(params),
    }
    return ParameterCandidate(
        parameter_set_id=parameter_set_id,
        rule_version=rule_version,
        family="composite",
        base_parameter_set_id="R-CURRENT",
        rationale=payload["rationale"],
        changed_fields=tuple(sorted(changed)),
        parameters=params,
        digest=canonical_digest(payload),
    )
