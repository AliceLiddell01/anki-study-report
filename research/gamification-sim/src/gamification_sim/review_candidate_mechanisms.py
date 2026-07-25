from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from .canonical_json import canonical_digest


PROTOCOL_ID: Final = "review-xp-candidate-protocol"
PROTOCOL_VERSION: Final = 1
PROTOCOL_STATUS: Final = "FROZEN_PRE_SCREENING"
REFERENCE_PARAMETERIZATION_ID: Final = "R-CURRENT"

STEP_FAMILY_ID: Final = "F-POST-TRANSITION-MG-STEP"
TAPER_FAMILY_ID: Final = "F-POST-TRANSITION-MG-TAPER"

STEP_MECHANISM_CLASS: Final = "POST_TRANSITION_MEMORY_GAIN_STEP_SCALING"
TAPER_MECHANISM_CLASS: Final = "POST_TRANSITION_MEMORY_GAIN_LINEAR_TAPER"

_FAMILY_MECHANISMS: Final[Mapping[str, str]] = MappingProxyType(
    {
        STEP_FAMILY_ID: STEP_MECHANISM_CLASS,
        TAPER_FAMILY_ID: TAPER_MECHANISM_CLASS,
    }
)


def _require_non_empty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_exact_int(name: str, value: int, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _require_multiplier(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{name} must be within [0.0, 1.0]")
    return numeric


@dataclass(frozen=True, slots=True)
class FrozenReviewCandidate:
    parameterization_id: str
    family_id: str
    mechanism_class: str
    base_parameter_set_id: str
    bound_refs: tuple[str, ...]
    endpoint_multiplier: float
    post_transition_start_day: int
    transition_taper_days: int | None
    construction_rule: str

    def __post_init__(self) -> None:
        _require_non_empty("parameterization_id", self.parameterization_id)
        _require_non_empty("family_id", self.family_id)
        _require_non_empty("mechanism_class", self.mechanism_class)
        _require_non_empty("base_parameter_set_id", self.base_parameter_set_id)
        _require_non_empty("construction_rule", self.construction_rule)

        if self.base_parameter_set_id != REFERENCE_PARAMETERIZATION_ID:
            raise ValueError(
                "frozen Review candidates may only use R-CURRENT as their base"
            )

        expected_mechanism = _FAMILY_MECHANISMS.get(self.family_id)
        if expected_mechanism is None:
            raise ValueError(f"unknown frozen Review candidate family: {self.family_id}")
        if self.mechanism_class != expected_mechanism:
            raise ValueError(
                f"{self.family_id} requires mechanism class {expected_mechanism}"
            )

        if (
            not isinstance(self.bound_refs, tuple)
            or not self.bound_refs
            or any(
                not isinstance(item, str) or not item.strip()
                for item in self.bound_refs
            )
            or len(set(self.bound_refs)) != len(self.bound_refs)
        ):
            raise ValueError("bound_refs must be a non-empty unique string tuple")

        _require_multiplier("endpoint_multiplier", self.endpoint_multiplier)
        _require_exact_int(
            "post_transition_start_day",
            self.post_transition_start_day,
        )

        if self.mechanism_class == STEP_MECHANISM_CLASS:
            if self.transition_taper_days is not None:
                raise ValueError("step candidates must not define transition_taper_days")
        else:
            if self.transition_taper_days is None:
                raise ValueError("taper candidates require transition_taper_days")
            _require_exact_int(
                "transition_taper_days",
                self.transition_taper_days,
                minimum=1,
            )

    def parameter_values(self) -> dict[str, int | float]:
        values: dict[str, int | float] = {
            "post_transition_memory_gain_multiplier": self.endpoint_multiplier,
            "post_transition_start_day": self.post_transition_start_day,
        }
        if self.transition_taper_days is not None:
            values["transition_taper_days"] = self.transition_taper_days
        return values

    def identity_payload(self) -> dict[str, Any]:
        return {
            "protocol_id": PROTOCOL_ID,
            "protocol_version": PROTOCOL_VERSION,
            "protocol_status": PROTOCOL_STATUS,
            "parameterization_id": self.parameterization_id,
            "candidate_id": self.family_id,
            "mechanism_class": self.mechanism_class,
            "base_parameter_set_id": self.base_parameter_set_id,
            "bound_refs": list(self.bound_refs),
            "parameter_values": self.parameter_values(),
            "construction_rule": self.construction_rule,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.identity_payload())


@dataclass(frozen=True, slots=True)
class RewardExecutionContext:
    day: int
    retention_transition_days: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        _require_exact_int("day", self.day)

        if not isinstance(self.retention_transition_days, tuple):
            raise ValueError("retention_transition_days must be a tuple")

        for index, transition_day in enumerate(self.retention_transition_days):
            _require_exact_int(
                f"retention_transition_days[{index}]",
                transition_day,
                minimum=1,
            )

        if self.retention_transition_days != tuple(
            sorted(set(self.retention_transition_days))
        ):
            raise ValueError(
                "retention_transition_days must be strictly increasing and unique"
            )

    @property
    def final_retention_transition_day(self) -> int | None:
        if not self.retention_transition_days:
            return None
        return self.retention_transition_days[-1]


FROZEN_REVIEW_CANDIDATES: Final[tuple[FrozenReviewCandidate, ...]] = (
    FrozenReviewCandidate(
        parameterization_id="P-STEP-ZERO",
        family_id=STEP_FAMILY_ID,
        mechanism_class=STEP_MECHANISM_CLASS,
        base_parameter_set_id=REFERENCE_PARAMETERIZATION_ID,
        bound_refs=(
            "post_transition_memory_gain_multiplier",
            "post_transition_start_day",
        ),
        endpoint_multiplier=0.0,
        post_transition_start_day=60,
        transition_taper_days=None,
        construction_rule=(
            "For eligible successful episodes on or after day 60, multiply "
            "MemoryGainCredit by 0.0; all other reward terms remain unchanged."
        ),
    ),
    FrozenReviewCandidate(
        parameterization_id="P-STEP-NEUTRAL-RATIO",
        family_id=STEP_FAMILY_ID,
        mechanism_class=STEP_MECHANISM_CLASS,
        base_parameter_set_id=REFERENCE_PARAMETERIZATION_ID,
        bound_refs=(
            "post_transition_memory_gain_multiplier",
            "post_transition_start_day",
        ),
        endpoint_multiplier=0.8333333333333334,
        post_transition_start_day=60,
        transition_taper_days=None,
        construction_rule=(
            "For eligible successful episodes on or after day 60, multiply "
            "MemoryGainCredit by neutral_context_credit / memory_gain_cap = "
            "0.10 / 0.12."
        ),
    ),
    FrozenReviewCandidate(
        parameterization_id="P-TAPER-ZERO-30D",
        family_id=TAPER_FAMILY_ID,
        mechanism_class=TAPER_MECHANISM_CLASS,
        base_parameter_set_id=REFERENCE_PARAMETERIZATION_ID,
        bound_refs=(
            "post_transition_memory_gain_multiplier",
            "post_transition_start_day",
            "transition_taper_days",
        ),
        endpoint_multiplier=0.0,
        post_transition_start_day=60,
        transition_taper_days=30,
        construction_rule=(
            "From day 60 through day 90, linearly interpolate the multiplier "
            "from 1.0 to 0.0; after day 90 use 0.0."
        ),
    ),
    FrozenReviewCandidate(
        parameterization_id="P-TAPER-NEUTRAL-RATIO-30D",
        family_id=TAPER_FAMILY_ID,
        mechanism_class=TAPER_MECHANISM_CLASS,
        base_parameter_set_id=REFERENCE_PARAMETERIZATION_ID,
        bound_refs=(
            "post_transition_memory_gain_multiplier",
            "post_transition_start_day",
            "transition_taper_days",
        ),
        endpoint_multiplier=0.8333333333333334,
        post_transition_start_day=60,
        transition_taper_days=30,
        construction_rule=(
            "From day 60 through day 90, linearly interpolate the multiplier "
            "from 1.0 to 0.10 / 0.12; after day 90 use that endpoint."
        ),
    ),
)

_BY_ID_MUTABLE = {
    candidate.parameterization_id: candidate
    for candidate in FROZEN_REVIEW_CANDIDATES
}
if len(_BY_ID_MUTABLE) != len(FROZEN_REVIEW_CANDIDATES):
    raise RuntimeError("frozen Review candidate IDs must be unique")

_BY_ID: Final[Mapping[str, FrozenReviewCandidate]] = MappingProxyType(
    _BY_ID_MUTABLE
)
del _BY_ID_MUTABLE


def frozen_review_candidate(
    parameterization_id: str,
) -> FrozenReviewCandidate:
    try:
        return _BY_ID[parameterization_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown frozen Review parameterization: {parameterization_id}"
        ) from exc


def frozen_review_candidate_payload(
    parameterization_id: str,
) -> dict[str, Any]:
    candidate = frozen_review_candidate(parameterization_id)
    return {
        **candidate.identity_payload(),
        "digest": candidate.digest,
    }


def frozen_review_candidate_trace(
    parameterization_id: str,
) -> dict[str, Any]:
    candidate = frozen_review_candidate(parameterization_id)
    return {
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_status": PROTOCOL_STATUS,
        "candidate_parameterization_id": candidate.parameterization_id,
        "family_id": candidate.family_id,
        "mechanism_class": candidate.mechanism_class,
        "base_parameter_set_id": candidate.base_parameter_set_id,
        "candidate_identity_digest": candidate.digest,
    }


def memory_gain_multiplier(
    parameterization_id: str | None,
    context: RewardExecutionContext | None = None,
) -> float:
    if parameterization_id is None or parameterization_id == REFERENCE_PARAMETERIZATION_ID:
        return 1.0

    candidate = frozen_review_candidate(parameterization_id)

    if context is None:
        raise ValueError(
            "candidate-enabled MemoryGain evaluation requires an execution context"
        )
    if not isinstance(context, RewardExecutionContext):
        raise TypeError("context must be a RewardExecutionContext")

    if (
        context.final_retention_transition_day
        != candidate.post_transition_start_day
    ):
        return 1.0

    start = candidate.post_transition_start_day
    if candidate.mechanism_class == STEP_MECHANISM_CLASS:
        return (
            1.0
            if context.day < start
            else candidate.endpoint_multiplier
        )

    taper_days = candidate.transition_taper_days
    if taper_days is None:  # pragma: no cover - constructor invariant
        raise RuntimeError("taper candidate is missing transition_taper_days")

    if context.day <= start:
        return 1.0

    end = start + taper_days
    if context.day >= end:
        return candidate.endpoint_multiplier

    progress = (context.day - start) / taper_days
    return 1.0 + progress * (candidate.endpoint_multiplier - 1.0)


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    return value


def validate_frozen_review_candidate_protocol(
    payload: Mapping[str, Any],
) -> None:
    root = _require_mapping(payload, "protocol")

    identity = _require_mapping(root.get("identity"), "identity")
    actual_identity = (
        identity.get("protocol_id"),
        identity.get("protocol_version"),
        identity.get("protocol_status"),
    )
    expected_identity = (
        PROTOCOL_ID,
        PROTOCOL_VERSION,
        PROTOCOL_STATUS,
    )
    if actual_identity != expected_identity:
        raise ValueError("frozen Review protocol identity drifted")

    reference = _require_mapping(
        root.get("reference_candidate"),
        "reference_candidate",
    )
    actual_reference = (
        reference.get("candidate_id"),
        reference.get("parameterization_id"),
        reference.get("survivor_eligible"),
    )
    expected_reference = (
        REFERENCE_PARAMETERIZATION_ID,
        REFERENCE_PARAMETERIZATION_ID,
        False,
    )
    if actual_reference != expected_reference:
        raise ValueError("frozen Review reference candidate drifted")

    family_rows = _require_list(
        root.get("candidate_families"),
        "candidate_families",
    )
    actual_families = tuple(
        (
            _require_mapping(item, "candidate_families[]").get("candidate_id"),
            _require_mapping(item, "candidate_families[]").get(
                "mechanism_class"
            ),
        )
        for item in family_rows
    )
    expected_families = tuple(_FAMILY_MECHANISMS.items())
    if actual_families != expected_families:
        raise ValueError("frozen Review candidate families drifted")

    bound_rows = _require_list(
        root.get("parameter_bounds"),
        "parameter_bounds",
    )
    actual_bounds = tuple(
        (
            _require_mapping(item, "parameter_bounds[]").get("parameter_id"),
            _require_mapping(item, "parameter_bounds[]").get("minimum"),
            _require_mapping(item, "parameter_bounds[]").get("maximum"),
            _require_mapping(item, "parameter_bounds[]").get(
                "minimum_inclusive"
            ),
            _require_mapping(item, "parameter_bounds[]").get(
                "maximum_inclusive"
            ),
            _require_mapping(item, "parameter_bounds[]").get("adaptive"),
        )
        for item in bound_rows
    )
    expected_bounds = (
        (
            "post_transition_memory_gain_multiplier",
            0.0,
            1.0,
            True,
            True,
            False,
        ),
        (
            "post_transition_start_day",
            60,
            60,
            True,
            True,
            False,
        ),
        (
            "transition_taper_days",
            30,
            30,
            True,
            True,
            False,
        ),
    )
    if actual_bounds != expected_bounds:
        raise ValueError("frozen Review parameter bounds drifted")

    parameterization_rows = _require_list(
        root.get("parameterizations"),
        "parameterizations",
    )
    actual_parameterizations = []
    for item in parameterization_rows:
        row = _require_mapping(item, "parameterizations[]")
        values = _require_mapping(
            row.get("parameter_values"),
            "parameter_values",
        )
        actual_parameterizations.append(
            (
                row.get("parameterization_id"),
                row.get("candidate_id"),
                tuple(
                    _require_list(
                        row.get("bound_refs"),
                        "bound_refs",
                    )
                ),
                tuple(sorted(values.items())),
                row.get("construction_rule"),
            )
        )

    expected_parameterizations = tuple(
        (
            candidate.parameterization_id,
            candidate.family_id,
            candidate.bound_refs,
            tuple(sorted(candidate.parameter_values().items())),
            candidate.construction_rule,
        )
        for candidate in FROZEN_REVIEW_CANDIDATES
    )
    if tuple(actual_parameterizations) != expected_parameterizations:
        raise ValueError("frozen Review parameterizations drifted")

    dimensions = _require_mapping(
        root.get("screening_dimensions"),
        "screening_dimensions",
    )
    candidate_or_reference = tuple(
        _require_list(
            dimensions.get("candidate_or_reference"),
            "screening_dimensions.candidate_or_reference",
        )
    )
    expected_candidate_or_reference = (
        REFERENCE_PARAMETERIZATION_ID,
        *(
            candidate.parameterization_id
            for candidate in FROZEN_REVIEW_CANDIDATES
        ),
    )
    if candidate_or_reference != expected_candidate_or_reference:
        raise ValueError("frozen Review screening candidate order drifted")
