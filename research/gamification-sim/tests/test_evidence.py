from __future__ import annotations

import pytest

from gamification_sim.evidence import MetricResult, MetricStatus, measured, unavailable


def test_unsupported_metric_serializes_null_with_reason():
    metric = unavailable(
        "retention",
        MetricStatus.UNSUPPORTED,
        unit="ratio",
        source_ids=("matched-policy",),
        method="longitudinal comparison",
        reason="scheduler unavailable",
    )
    assert metric.payload()["value"] is None
    assert metric.payload()["reason"] == "scheduler unavailable"


def test_missing_evidence_cannot_use_an_ideal_placeholder():
    with pytest.raises(ValueError, match="null value"):
        MetricResult(
            "missing",
            MetricStatus.UNSUPPORTED,
            0.0,
            "ratio",
            0,
            ("missing-source",),
            "not measured",
            reason="not available",
        )


def test_measured_metric_requires_finite_value():
    with pytest.raises(ValueError, match="finite value"):
        measured(
            "bad",
            float("nan"),
            unit="ratio",
            sample_count=1,
            source_ids=("test",),
            method="constructed",
        )
