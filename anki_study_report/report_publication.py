"""Helpers for identifying report publication/cache freshness."""

from __future__ import annotations

from typing import Any


_CACHE_STATUS_KEY_FIELDS = (
    "status",
    "version",
    "updatedAt",
    "cachedDays",
    "cachedDeckDays",
    "lastRevlogId",
)


def report_cache_state_key(cache_status: dict[str, Any] | None) -> tuple[tuple[str, object], ...]:
    """Return stable cache metadata that affects mixed report publication."""
    status = cache_status if isinstance(cache_status, dict) else {}
    return tuple((field, _json_scalar(status.get(field))) for field in _CACHE_STATUS_KEY_FIELDS)


def report_metrics_cache_key(
    base_cache_key: object,
    answer_mode: str,
    use_study_time_stats: bool,
    track_reviewer_sessions: bool,
    use_stats_cache_for_report: bool,
    cache_status: dict[str, Any] | None,
) -> tuple[object, ...]:
    """Build the memo key for metrics that later publish /api/report."""
    return (
        base_cache_key,
        answer_mode,
        bool(use_study_time_stats),
        bool(track_reviewer_sessions),
        bool(use_stats_cache_for_report),
        report_cache_state_key(cache_status),
    )


def _json_scalar(value: object) -> object:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        return value
    return str(value)
