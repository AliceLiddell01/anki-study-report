from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

from .canonical_json import canonical_digest
from .longitudinal_models import LongitudinalCardState


def derive_cohort_seed(master_seed: int, replica: int) -> int:
    material = f"{master_seed}:{replica}:longitudinal-cohort-v1"
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def latent_draw(
    master_seed: int,
    replica: int,
    card_lineage_id: str,
    review_ordinal: int,
    channel: str,
) -> float:
    material = (
        f"{master_seed}:{replica}:{card_lineage_id}:{review_ordinal}:{channel}:"
        "longitudinal-common-random-v1"
    )
    seed = int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")
    return random.Random(seed).random()


def initial_cohort(
    *,
    master_seed: int,
    replica: int,
    cohort_size: int,
    start_date: str,
    policy_id: str,
    scheduler: str,
) -> tuple[LongitudinalCardState, ...]:
    start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    rng = random.Random(derive_cohort_seed(master_seed, replica))
    cards = []
    for index in range(cohort_size):
        lineage = f"card-{replica:02d}-{index:05d}"
        difficulty = 4.25 + 1.5 * rng.random()
        stability = 3.5 + 3.0 * rng.random()
        serialized = None
        if scheduler == "py-fsrs":
            from fsrs import Card, State

            card = Card(
                card_id=replica * 1_000_000 + index + 1,
                state=State.Review,
                step=None,
                stability=stability,
                difficulty=difficulty,
                due=start,
                last_review=start - timedelta(days=5),
            )
            serialized = tuple(sorted(card.to_dict().items()))
        cards.append(
            LongitudinalCardState(
                card_lineage_id=lineage,
                created_day=0,
                state_kind="review",
                last_review_day=None,
                next_due_day=0,
                review_count=0,
                lapse_count=0,
                stability=stability,
                difficulty=difficulty,
                retrievability_at_last_update=0.9,
                scheduled_interval=0,
                desired_retention_policy=policy_id,
                preset_id="synthetic-default",
                active=True,
                fsrs_card=serialized,
            )
        )
    return tuple(cards)


def cohort_digest(cards: tuple[LongitudinalCardState, ...]) -> str:
    return canonical_digest(
        [
            {
                "card_lineage_id": card.card_lineage_id,
                "created_day": card.created_day,
                "state_kind": card.state_kind,
                "next_due_day": card.next_due_day,
                "stability": card.stability,
                "difficulty": card.difficulty,
                "preset_id": card.preset_id,
                "active": card.active,
            }
            for card in cards
        ]
    )
