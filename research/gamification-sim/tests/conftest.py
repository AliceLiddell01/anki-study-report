from __future__ import annotations

import pytest

from gamification_sim.models import MemoryContext, Outcome, ReviewEpisodeInput


@pytest.fixture
def normal_memory() -> MemoryContext:
    return MemoryContext(
        retrievability_actual=0.90,
        retrievability_natural_due=0.90,
        stability_before=1.0,
        stability_good_counterfactual=1.5168967963882134,
        confidence="high",  # StrEnum accepts equality with the string value.
    )


@pytest.fixture
def episode_factory():
    def make(index: int = 0, **overrides):
        values = {
            "source_event_key": f"event-{index}",
            "card_lineage": f"card-{index}",
            "anki_day": "2026-07-16",
            "outcome": Outcome.GOOD,
        }
        values.update(overrides)
        return ReviewEpisodeInput(**values)
    return make
