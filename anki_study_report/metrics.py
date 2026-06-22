"""Read-only study metrics for Anki Study Report."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


ANSWER_TIME_CAP_MS = 120_000
SECONDS_IN_DAY = 86_400
PROBLEM_DECK_PASS_RATE = 0.80
PROBLEM_DECK_MIN_REVIEWS = 5


def collect_metrics(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Collect read-only study metrics from an Anki collection.

    Args:
        col: Anki collection object.
        start_ts: Inclusive period start as Unix seconds or milliseconds.
        end_ts: Exclusive period end as Unix seconds or milliseconds.
        deck_ids: Optional deck ids. When provided, descendants are included
            when the current Anki deck API exposes enough information.

    Returns:
        A dictionary with safe zero values when no matching data exists.
    """

    start_ms = _to_revlog_ms(start_ts)
    end_ms = _to_revlog_ms(end_ts)
    if end_ms <= start_ms:
        return _empty_metrics()

    expanded_deck_ids = _expand_deck_ids(col, deck_ids)

    total_reviews, again_count, total_seconds = _review_summary(
        col,
        start_ms,
        end_ms,
        expanded_deck_ids,
    )
    new_cards = _new_cards(col, start_ms, end_ms, expanded_deck_ids)
    answer_distribution = _answer_distribution(col, start_ms, end_ms, expanded_deck_ids)
    deck_breakdown = _deck_breakdown(col, start_ms, end_ms, expanded_deck_ids)
    due_tomorrow = _due_tomorrow(col, expanded_deck_ids)

    return {
        "total_reviews": total_reviews,
        "new_cards": new_cards,
        "again_count": again_count,
        "pass_rate": _pass_rate(total_reviews, again_count),
        "total_seconds": total_seconds,
        "average_answer_seconds": _average_seconds(total_seconds, total_reviews),
        "estimated_minutes": _minutes(total_seconds),
        "answer_distribution": answer_distribution,
        "deck_breakdown": deck_breakdown,
        "due_tomorrow": due_tomorrow,
    }


def expand_deck_ids(
    col: Any,
    deck_ids: Sequence[int] | None,
) -> list[int] | None:
    """Return selected deck ids plus descendants when Anki exposes them."""

    return _expand_deck_ids(col, deck_ids)


def collect_action_card_ids(
    col: Any,
    start_ts: int | float,
    end_ts: int | float,
    deck_ids: Sequence[int] | None = None,
    action: str = "again",
) -> list[int]:
    """Return card ids for Browser actions without modifying the collection."""

    start_ms = _to_revlog_ms(start_ts)
    end_ms = _to_revlog_ms(end_ts)
    if end_ms <= start_ms:
        return []

    expanded_deck_ids = _expand_deck_ids(col, deck_ids)
    if action == "again":
        return _review_card_ids(
            col,
            start_ms,
            end_ms,
            expanded_deck_ids,
            extra_where="and r.ease = 1",
        )
    if action == "new":
        return _new_card_ids(col, start_ms, end_ms, expanded_deck_ids)
    if action == "problem_decks":
        return _problem_deck_card_ids(col, start_ms, end_ms, expanded_deck_ids)
    raise ValueError(f"Unknown Browser action: {action}")


def _empty_metrics() -> dict[str, Any]:
    return {
        "total_reviews": 0,
        "new_cards": 0,
        "again_count": 0,
        "pass_rate": 0.0,
        "total_seconds": 0,
        "average_answer_seconds": 0.0,
        "estimated_minutes": 0.0,
        "answer_distribution": _empty_answer_distribution(),
        "deck_breakdown": [],
        "due_tomorrow": 0,
    }


def _to_revlog_ms(ts: int | float) -> int:
    value = int(ts)
    if abs(value) < 10_000_000_000:
        return value * 1000
    return value


def _review_summary(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> tuple[int, int, int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    row = col.db.first(
        f"""
        select
            count(*) as total_reviews,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
            coalesce(sum(
                case
                    when r.time < 0 then 0
                    when r.time > ? then ?
                    else r.time
                end
            ), 0) as total_ms
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {deck_sql}
        """,
        ANSWER_TIME_CAP_MS,
        ANSWER_TIME_CAP_MS,
        start_ms,
        end_ms,
        *deck_params,
    )
    if not row:
        return 0, 0, 0

    total_reviews = _as_int(row[0])
    again_count = _as_int(row[1])
    total_seconds = _as_int(round(_as_int(row[2]) / 1000))
    return total_reviews, again_count, total_seconds


def _new_cards(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> int:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    return _as_int(
        col.db.scalar(
            f"""
            select count(distinct r.cid)
            from revlog r
            left join cards c on c.id = r.cid
            where r.id >= ?
              and r.id < ?
              and r.type = 0
              and not exists (
                  select 1
                  from revlog earlier
                  where earlier.cid = r.cid
                    and earlier.id < r.id
                  limit 1
              )
              {deck_sql}
            """,
            start_ms,
            end_ms,
            *deck_params,
        )
    )


def _answer_distribution(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> dict[str, int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    rows = col.db.all(
        f"""
        select r.ease, count(*)
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {deck_sql}
        group by r.ease
        """,
        start_ms,
        end_ms,
        *deck_params,
    )

    distribution = _empty_answer_distribution()
    for ease, count in rows:
        key = _ease_key(ease)
        if key:
            distribution[key] += _as_int(count)
    return distribution


def _empty_answer_distribution() -> dict[str, int]:
    return {
        "again": 0,
        "hard": 0,
        "good": 0,
        "easy": 0,
    }


def _ease_key(ease: Any) -> str | None:
    try:
        ease_int = _as_int(ease)
    except (TypeError, ValueError):
        return None
    return {
        1: "again",
        2: "hard",
        3: "good",
        4: "easy",
    }.get(ease_int)


def _review_card_ids(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
    extra_where: str = "",
) -> list[int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    rows = col.db.all(
        f"""
        select distinct r.cid
        from revlog r
        join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {extra_where}
          {deck_sql}
        order by r.cid
        """,
        start_ms,
        end_ms,
        *deck_params,
    )
    return [_as_int(row[0]) for row in rows if row and row[0] is not None]


def _new_card_ids(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> list[int]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    rows = col.db.all(
        f"""
        select distinct r.cid
        from revlog r
        join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          and r.type = 0
          and not exists (
              select 1
              from revlog earlier
              where earlier.cid = r.cid
                and earlier.id < r.id
              limit 1
          )
          {deck_sql}
        order by r.cid
        """,
        start_ms,
        end_ms,
        *deck_params,
    )
    return [_as_int(row[0]) for row in rows if row and row[0] is not None]


def _problem_deck_card_ids(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> list[int]:
    problem_deck_ids = [
        _as_int(deck["deck_id"])
        for deck in _deck_breakdown(col, start_ms, end_ms, deck_ids)
        if deck.get("deck_id") is not None
        and _as_int(deck.get("total_reviews")) >= PROBLEM_DECK_MIN_REVIEWS
        and float(deck.get("pass_rate") or 0) < PROBLEM_DECK_PASS_RATE
    ]
    if not problem_deck_ids:
        return []

    return _review_card_ids(col, start_ms, end_ms, problem_deck_ids)


def _deck_breakdown(
    col: Any,
    start_ms: int,
    end_ms: int,
    deck_ids: Sequence[int] | None,
) -> list[dict[str, Any]]:
    deck_sql, deck_params = _deck_filter_sql(deck_ids)
    rows = col.db.all(
        f"""
        select
            c.did,
            count(*) as total_reviews,
            coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
            coalesce(sum(case when r.ease = 2 then 1 else 0 end), 0) as hard_count,
            coalesce(sum(case when r.ease = 3 then 1 else 0 end), 0) as good_count,
            coalesce(sum(case when r.ease = 4 then 1 else 0 end), 0) as easy_count,
            coalesce(sum(
                case
                    when r.time < 0 then 0
                    when r.time > ? then ?
                    else r.time
                end
            ), 0) as total_ms,
            count(distinct case
                when r.type = 0
                  and not exists (
                      select 1
                      from revlog earlier
                      where earlier.cid = r.cid
                        and earlier.id < r.id
                      limit 1
                  )
                then r.cid
            end) as new_cards
        from revlog r
        left join cards c on c.id = r.cid
        where r.id >= ?
          and r.id < ?
          {deck_sql}
        group by c.did
        order by total_reviews desc, c.did asc
        """,
        ANSWER_TIME_CAP_MS,
        ANSWER_TIME_CAP_MS,
        start_ms,
        end_ms,
        *deck_params,
    )

    names = _deck_names_by_id(col)
    breakdown: list[dict[str, Any]] = []
    for did, total_reviews, again_count, hard_count, good_count, easy_count, total_ms, new_cards in rows:
        deck_id = _as_int(did) if did is not None else None
        total_reviews_int = _as_int(total_reviews)
        again_count_int = _as_int(again_count)
        total_seconds = _as_int(round(_as_int(total_ms) / 1000))
        breakdown.append(
            {
                "deck_id": deck_id,
                "deck_name": _deck_name_for_breakdown(deck_id, names),
                "total_reviews": total_reviews_int,
                "new_cards": _as_int(new_cards),
                "again_count": again_count_int,
                "hard_count": _as_int(hard_count),
                "good_count": _as_int(good_count),
                "easy_count": _as_int(easy_count),
                "pass_rate": _pass_rate(total_reviews_int, again_count_int),
                "total_seconds": total_seconds,
                "average_answer_seconds": _average_seconds(
                    total_seconds,
                    total_reviews_int,
                ),
                "estimated_minutes": _minutes(total_seconds),
            }
        )
    return breakdown


def _deck_name_for_breakdown(deck_id: int | None, names: dict[int, str]) -> str:
    if deck_id is None:
        return "Удалённые карточки"
    return names.get(deck_id, f"Колода {deck_id}")


def _due_tomorrow(col: Any, deck_ids: Sequence[int] | None) -> int:
    try:
        today = int(col.sched.today)
        day_cutoff = int(col.sched.day_cutoff)
    except Exception:
        return 0

    deck_sql, deck_params = _deck_filter_sql(deck_ids, table_alias=None)
    tomorrow = today + 1
    tomorrow_start = day_cutoff
    tomorrow_end = day_cutoff + SECONDS_IN_DAY

    return _as_int(
        col.db.scalar(
            f"""
            select count(*)
            from cards
            where (
                (queue in (2, 3) and due = ?)
                or (queue = 1 and due >= ? and due < ?)
            )
            {deck_sql}
            """,
            tomorrow,
            tomorrow_start,
            tomorrow_end,
            *deck_params,
        )
    )


def _expand_deck_ids(
    col: Any,
    deck_ids: Sequence[int] | None,
) -> list[int] | None:
    if deck_ids is None:
        return None

    selected = _normalized_deck_ids(deck_ids)
    if not selected:
        return []

    names = _deck_names_by_id(col)
    if names:
        selected = {deck_id for deck_id in selected if deck_id in names}
        if not selected:
            return []

    expanded_via_api = _expand_deck_ids_via_children(col, selected)
    if expanded_via_api is not None:
        if names:
            expanded_via_api = {
                deck_id for deck_id in expanded_via_api if deck_id in names
            }
        return sorted(expanded_via_api)

    if names:
        return sorted(_expand_deck_ids_by_names(names, selected))

    return sorted(selected)


def _normalized_deck_ids(deck_ids: Sequence[int]) -> set[int]:
    normalized: set[int] = set()
    for deck_id in deck_ids:
        try:
            normalized.add(_as_int(deck_id))
        except (TypeError, ValueError):
            continue
    return normalized


def _expand_deck_ids_via_children(col: Any, selected: set[int]) -> set[int] | None:
    try:
        children_method = col.decks.children
    except Exception:
        return None

    if not callable(children_method):
        return None

    expanded = set(selected)
    pending = list(selected)

    while pending:
        deck_id = pending.pop()
        try:
            children = children_method(deck_id)
        except Exception:
            return None

        for child in _iter_child_deck_ids(children):
            if child not in expanded:
                expanded.add(child)
                pending.append(child)

    return expanded


def _iter_child_deck_ids(children: Iterable[Any]) -> Iterable[int]:
    for child in children:
        child_id = None
        if isinstance(child, int):
            child_id = child
        elif hasattr(child, "id"):
            child_id = child.id
        elif isinstance(child, dict):
            child_id = child.get("id")
        elif isinstance(child, (tuple, list)) and child:
            child_id = _child_id_from_sequence(child)

        if child_id is not None:
            try:
                yield _as_int(child_id)
            except (TypeError, ValueError):
                continue


def _child_id_from_sequence(child: Sequence[Any]) -> Any:
    for value in reversed(child):
        try:
            return _as_int(value)
        except (TypeError, ValueError):
            continue
    return None


def _expand_deck_ids_by_names(names: dict[int, str], selected: set[int]) -> set[int]:
    selected_names = {names[deck_id] for deck_id in selected if deck_id in names}
    if not selected_names:
        return set(selected)

    expanded = set(selected)
    for deck_id, name in names.items():
        if any(name == parent or name.startswith(parent + "::") for parent in selected_names):
            expanded.add(deck_id)
    return expanded


def _deck_names_by_id(col: Any) -> dict[int, str]:
    try:
        return {
            _as_int(deck.id): str(deck.name)
            for deck in col.decks.all_names_and_ids()
        }
    except Exception:
        pass

    try:
        decks = col.decks.all()
    except Exception:
        return {}

    names: dict[int, str] = {}
    for deck in decks:
        try:
            names[_as_int(deck["id"])] = str(deck["name"])
        except Exception:
            continue
    return names


def _deck_filter_sql(
    deck_ids: Sequence[int] | None,
    table_alias: str | None = "c",
) -> tuple[str, list[int]]:
    if deck_ids is None:
        return "", []

    normalized = [_as_int(deck_id) for deck_id in deck_ids]
    if not normalized:
        return "and 0", []

    column = "did" if table_alias is None else f"{table_alias}.did"
    placeholders = ", ".join("?" for _ in normalized)
    return f"and {column} in ({placeholders})", normalized


def _pass_rate(total_reviews: int, again_count: int) -> float:
    if total_reviews <= 0:
        return 0.0
    return round((total_reviews - again_count) / total_reviews, 4)


def _minutes(total_seconds: int) -> float:
    if total_seconds <= 0:
        return 0.0
    return round(total_seconds / 60, 1)


def _average_seconds(total_seconds: int, total_reviews: int) -> float:
    if total_reviews <= 0 or total_seconds <= 0:
        return 0.0
    return round(total_seconds / total_reviews, 1)


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)
