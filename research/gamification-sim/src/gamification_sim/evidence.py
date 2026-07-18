from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class MetricStatus(StrEnum):
    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    UNSUPPORTED = "UNSUPPORTED"
    DEFERRED = "DEFERRED"


class CandidateStatus(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"
    INCOMPLETE_EVIDENCE = "INCOMPLETE_EVIDENCE"


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric_id: str
    status: MetricStatus
    value: float | None
    unit: str
    sample_count: int
    source_ids: tuple[str, ...]
    method: str
    warnings: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.metric_id or not self.unit or not self.method:
            raise ValueError("metric_id, unit, and method are required")
        if type(self.sample_count) is not int or self.sample_count < 0:
            raise ValueError("metric sample_count must be a non-negative integer")
        missing = self.status in {MetricStatus.UNSUPPORTED, MetricStatus.DEFERRED}
        if missing:
            if self.value is not None or not self.reason:
                raise ValueError("unsupported/deferred metric requires null value and reason")
        elif self.value is None or not math.isfinite(self.value) or self.reason is not None:
            raise ValueError("measured/derived metric requires a finite value and no reason")

    @property
    def supported(self) -> bool:
        return self.status in {MetricStatus.MEASURED, MetricStatus.DERIVED}

    def payload(self) -> dict[str, object]:
        return {
            "metric_id": self.metric_id,
            "status": self.status.value,
            "value": self.value,
            "unit": self.unit,
            "sample_count": self.sample_count,
            "source_ids": list(self.source_ids),
            "method": self.method,
            "warnings": list(self.warnings),
            "reason": self.reason,
        }


def measured(
    metric_id: str,
    value: float,
    *,
    unit: str,
    sample_count: int,
    source_ids: tuple[str, ...],
    method: str,
    warnings: tuple[str, ...] = (),
) -> MetricResult:
    return MetricResult(
        metric_id,
        MetricStatus.MEASURED,
        float(value),
        unit,
        sample_count,
        source_ids,
        method,
        warnings,
    )


def derived(
    metric_id: str,
    value: float,
    *,
    unit: str,
    sample_count: int,
    source_ids: tuple[str, ...],
    method: str,
    warnings: tuple[str, ...] = (),
) -> MetricResult:
    return MetricResult(
        metric_id,
        MetricStatus.DERIVED,
        float(value),
        unit,
        sample_count,
        source_ids,
        method,
        warnings,
    )


def unavailable(
    metric_id: str,
    status: MetricStatus,
    *,
    unit: str,
    source_ids: tuple[str, ...],
    method: str,
    reason: str,
) -> MetricResult:
    if status not in {MetricStatus.UNSUPPORTED, MetricStatus.DEFERRED}:
        raise ValueError("unavailable metric status must be UNSUPPORTED or DEFERRED")
    return MetricResult(metric_id, status, None, unit, 0, source_ids, method, reason=reason)
