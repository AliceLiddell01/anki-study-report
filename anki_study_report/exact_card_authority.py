"""Pure scoping policy for exact-card Inspection Profile authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


_PROFILE_REASON_PREFIX = "profile:"
_TRUSTED_STORE_STATUSES = {"available", "empty"}


@dataclass(frozen=True)
class ExactCardProfileScope:
    """The only profile inventory that may affect one exact-card recheck."""

    profile: dict[str, Any] | None
    requires_profile_authority: bool
    blocking_error_code: str | None


def reason_requires_profile_authority(reason_id: object) -> bool:
    """Return whether a stable prior reason was emitted by profile checks."""

    return isinstance(reason_id, str) and reason_id.startswith(_PROFILE_REASON_PREFIX)


def scope_exact_card_profile(
    store_snapshot: object,
    *,
    note_type_id: object,
    previous_reason_ids: Iterable[object] = (),
) -> ExactCardProfileScope:
    """Select local profile authority without inheriting aggregate inventory health.

    An unreadable global inventory only blocks a recheck that previously depended
    on profile evidence. Learning, signal, and search reasons remain independent.
    """

    target = _positive_id(note_type_id)
    requires_authority = any(reason_requires_profile_authority(value) for value in previous_reason_ids)
    snapshot = store_snapshot if isinstance(store_snapshot, dict) else {}
    store_status = str(snapshot.get("status") or "unavailable")
    if target <= 0 or store_status not in _TRUSTED_STORE_STATUSES:
        return ExactCardProfileScope(
            profile=None,
            requires_profile_authority=requires_authority,
            blocking_error_code="profile_authority_changed" if requires_authority else None,
        )

    raw_profiles = snapshot.get("profiles")
    profiles = raw_profiles if isinstance(raw_profiles, list) else []
    profile = next(
        (
            value
            for value in profiles
            if isinstance(value, dict) and _positive_id(value.get("noteTypeId")) == target
        ),
        None,
    )
    return ExactCardProfileScope(
        profile=profile,
        requires_profile_authority=requires_authority,
        blocking_error_code=(
            "profile_authority_changed"
            if requires_authority and profile is None
            else None
        ),
    )


def _positive_id(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return parsed if 0 < parsed <= 9_223_372_036_854_775_807 else 0
