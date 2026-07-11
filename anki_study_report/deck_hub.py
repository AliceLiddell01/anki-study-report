"""Pure hierarchy and aggregation model for the Decks v2 dashboard."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


MIN_REVIEWS_FOR_STRONG_STATUS = 10
SLOW_ANSWER_SECONDS = 18.0
PROBLEM_STATUSES = {"warning", "danger"}
STATUS_ORDER = {"danger": 0, "warning": 1, "neutral": 2, "good": 3}


def collect_deck_catalog(col: Any) -> list[dict[str, Any]]:
    """Collect one compact current-deck snapshot without per-deck queries."""

    try:
        raw_decks = col.decks.all()
    except Exception:
        raw_decks = []

    direct_counts: dict[int, int] = {}
    try:
        rows = col.db.all(
            """
            select case when odid > 0 then odid else did end as home_did, count(*)
            from cards
            group by home_did
            """
        )
        direct_counts = {_as_int(deck_id): max(0, _as_int(count)) for deck_id, count in rows}
    except Exception:
        direct_counts = {}

    catalog: list[dict[str, Any]] = []
    for raw in raw_decks if isinstance(raw_decks, list) else []:
        if not isinstance(raw, dict):
            continue
        deck_id = _as_int(raw.get("id"))
        name = str(raw.get("name") or "").strip()
        if deck_id <= 0 or not name:
            continue
        catalog.append(
            {
                "deck_id": deck_id,
                "deck_name": name,
                "filtered": bool(raw.get("dyn")),
                "direct_card_count": direct_counts.get(deck_id, 0),
            }
        )
    return sorted(catalog, key=lambda row: (_name_key(row["deck_name"]), row["deck_id"]))


def build_deck_hub(
    deck_catalog: object,
    direct_rows: object,
    *,
    selected_deck_ids: Sequence[int] | None = None,
    include_child_decks: bool = True,
    active_dates_available: bool = False,
) -> dict[str, Any] | None:
    """Build a normalized, cycle-safe Decks v2 public model.

    ``direct_rows`` must contain direct-only metrics. Subtree metrics are
    calculated exactly once from those rows after the hierarchy is normalized.
    """

    catalog_rows = _catalog_rows(deck_catalog)
    if not catalog_rows:
        return None

    catalog_by_id = {row["deckId"]: row for row in catalog_rows}
    normal_ids = {row["deckId"] for row in catalog_rows if not row["filtered"]}
    filtered_count = sum(1 for row in catalog_rows if row["filtered"])
    requested_ids = None if selected_deck_ids is None else {_as_int(value) for value in selected_deck_ids}
    included_ids = set(normal_ids) if requested_ids is None else normal_ids & requested_ids

    name_to_id = {
        row["fullName"]: row["deckId"]
        for row in catalog_rows
        if row["deckId"] in normal_ids
    }
    structural_ids: set[int] = set()
    if requested_ids is not None:
        for deck_id in list(included_ids):
            for parent_name in _parent_names(catalog_by_id[deck_id]["fullName"]):
                parent_id = name_to_id.get(parent_name)
                if parent_id is not None and parent_id not in included_ids:
                    structural_ids.add(parent_id)

    visible_ids = included_ids | structural_ids
    metrics_by_id = _direct_metrics_by_id(direct_rows)
    nodes: dict[int, dict[str, Any]] = {}
    for deck_id in sorted(visible_ids):
        catalog = catalog_by_id[deck_id]
        explicit_parent = catalog.get("explicitParentId")
        derived_parent = name_to_id.get(_immediate_parent_name(catalog["fullName"]))
        parent_id = explicit_parent if explicit_parent in visible_ids else derived_parent
        if parent_id not in visible_ids or parent_id == deck_id:
            parent_id = None
        structural_only = deck_id in structural_ids
        direct = _public_metrics(
            None if structural_only else metrics_by_id.get(deck_id),
            direct_card_count=0 if structural_only else catalog["directCardCount"],
            active_dates_available=active_dates_available,
        )
        nodes[deck_id] = {
            "deckId": deck_id,
            "fullName": catalog["fullName"],
            "shortName": catalog["shortName"],
            "parentId": parent_id,
            "depth": max(0, len(catalog["fullName"].split("::")) - 1),
            "childIds": [],
            "filtered": False,
            "structuralOnly": structural_only,
            "directMetrics": direct,
            "subtreeMetrics": dict(direct),
            "aggregateHealth": "neutral",
            "dataConfidence": "insufficient",
            "descendantIssueCount": 0,
            "descendantIssues": [],
            "reasons": [],
            "recommendations": [],
            "actions": {"includeDescendants": True, "directOnly": False},
        }

    _break_parent_cycles(nodes)
    for node in nodes.values():
        parent_id = node["parentId"]
        if parent_id in nodes:
            nodes[parent_id]["childIds"].append(node["deckId"])
    for node in nodes.values():
        node["childIds"].sort(key=lambda child_id: _node_sort_key(nodes[child_id]))

    root_ids = sorted(
        [deck_id for deck_id, node in nodes.items() if node["parentId"] not in nodes],
        key=lambda deck_id: _node_sort_key(nodes[deck_id]),
    )
    _aggregate_subtrees(nodes, root_ids, active_dates_available)

    _drop_empty_default(nodes, root_ids)
    actual_nodes = [node for node in nodes.values() if not node["structuralOnly"]]

    for node in nodes.values():
        health, confidence, reasons, recommendations = _health_model(
            node["subtreeMetrics"],
            structural_only=node["structuralOnly"],
        )
        node["aggregateHealth"] = health
        node["dataConfidence"] = confidence
        node["reasons"] = reasons
        node["recommendations"] = recommendations
        node["actions"] = {
            "includeDescendants": not node["structuralOnly"],
            "directOnly": not node["structuralOnly"] and bool(node["childIds"]),
        }

    for node in nodes.values():
        issues = _descendant_issues(node["deckId"], nodes)
        node["descendantIssues"] = issues
        node["descendantIssueCount"] = len(issues)

    total_reviews = sum(node["directMetrics"]["reviews"] for node in actual_nodes)
    total_pass = sum(node["directMetrics"]["passCount"] for node in actual_nodes)
    aggregate_pass_rate = round(total_pass / total_reviews, 4) if total_reviews else None
    attention_decks = sum(1 for node in actual_nodes if node["aggregateHealth"] in PROBLEM_STATUSES)
    danger_decks = sum(1 for node in actual_nodes if node["aggregateHealth"] == "danger")
    groups_with_issues = sum(
        1 for node in actual_nodes if node["childIds"] and node["descendantIssueCount"] > 0
    )

    public_nodes = {str(deck_id): _without_internal_metrics(node) for deck_id, node in sorted(nodes.items())}
    return {
        "schemaVersion": 1,
        "scope": {
            "kind": "all" if requested_ids is None else "selected",
            "selectedDeckIds": sorted(included_ids) if requested_ids is not None else [],
            "includeChildDecks": bool(include_child_decks),
        },
        "summary": {
            "totalDecks": len(actual_nodes),
            "attentionDecks": attention_decks,
            "dangerDecks": danger_decks,
            "groupsWithDescendantIssues": groups_with_issues,
            "aggregatePassRate": aggregate_pass_rate,
            "filteredDecksExcluded": filtered_count,
        },
        "nodes": public_nodes,
        "rootIds": root_ids,
    }


def _catalog_rows(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for raw in value if isinstance(value, list) else []:
        if not isinstance(raw, dict):
            continue
        deck_id = _as_int(raw.get("deck_id") if raw.get("deck_id") is not None else raw.get("deckId"))
        name = str(raw.get("deck_name") or raw.get("fullName") or raw.get("name") or "").strip()
        if deck_id <= 0 or not name or deck_id in seen_ids:
            continue
        seen_ids.add(deck_id)
        explicit_parent = raw.get("parent_id") if raw.get("parent_id") is not None else raw.get("parentId")
        rows.append(
            {
                "deckId": deck_id,
                "fullName": name,
                "shortName": name.split("::")[-1] or name,
                "filtered": bool(raw.get("filtered") or raw.get("dyn")),
                "directCardCount": max(0, _as_int(raw.get("direct_card_count") or raw.get("directCardCount"))),
                "explicitParentId": _as_int(explicit_parent) if explicit_parent is not None else None,
            }
        )
    return sorted(rows, key=lambda row: (_name_key(row["fullName"]), row["deckId"]))


def _direct_metrics_by_id(value: object) -> dict[int, dict[str, Any]]:
    metrics: dict[int, dict[str, Any]] = {}
    for raw in value if isinstance(value, list) else []:
        if not isinstance(raw, dict):
            continue
        deck_id = _as_int(raw.get("deck_id") if raw.get("deck_id") is not None else raw.get("deckId"))
        if deck_id <= 0:
            continue
        total = max(0, _as_int(raw.get("total_reviews") if raw.get("total_reviews") is not None else raw.get("reviews")))
        fail = max(0, _as_int(raw.get("fail_count") if raw.get("fail_count") is not None else raw.get("again_count")))
        passed = max(0, _as_int(raw.get("pass_count")))
        if passed <= 0 and total > 0:
            passed = max(0, total - fail)
        average = _optional_float(raw.get("average_answer_seconds"))
        total_answer = _optional_float(raw.get("total_answer_seconds"))
        if total_answer is None and average is not None:
            total_answer = average * total
        active_dates = raw.get("_active_dates")
        metrics[deck_id] = {
            "reviews": total,
            "newCards": max(0, _as_int(raw.get("new_cards"))),
            "passCount": passed,
            "failCount": fail,
            "hardCount": max(0, _as_int(raw.get("hard_count"))),
            "easyCount": max(0, _as_int(raw.get("easy_count"))),
            "studySeconds": max(0, _as_int(raw.get("total_seconds"))),
            "totalAnswerSeconds": max(0.0, total_answer or 0.0),
            "activeDates": {str(item) for item in active_dates} if isinstance(active_dates, list) else set(),
        }
    return metrics


def _public_metrics(
    value: dict[str, Any] | None,
    *,
    direct_card_count: int,
    active_dates_available: bool,
) -> dict[str, Any]:
    source = value or {}
    reviews = max(0, _as_int(source.get("reviews")))
    passed = max(0, _as_int(source.get("passCount")))
    failed = max(0, _as_int(source.get("failCount")))
    total_answer = max(0.0, _as_float(source.get("totalAnswerSeconds")))
    active_dates = source.get("activeDates") if isinstance(source.get("activeDates"), set) else set()
    return {
        "reviews": reviews,
        "newCards": max(0, _as_int(source.get("newCards"))),
        "passCount": passed,
        "failCount": failed,
        "hardCount": max(0, _as_int(source.get("hardCount"))),
        "easyCount": max(0, _as_int(source.get("easyCount"))),
        "passRate": round(passed / reviews, 4) if reviews else None,
        "failRate": round(failed / reviews, 4) if reviews else None,
        "averageAnswerSeconds": round(total_answer / reviews, 2) if reviews else None,
        "studySeconds": max(0, _as_int(source.get("studySeconds"))),
        "activeDays": len(active_dates) if active_dates_available else None,
        "directCardCount": max(0, direct_card_count),
        "_totalAnswerSeconds": total_answer,
        "_activeDates": active_dates,
    }


def _aggregate_subtrees(nodes: dict[int, dict[str, Any]], root_ids: list[int], active_dates_available: bool) -> None:
    def visit(deck_id: int) -> dict[str, Any]:
        node = nodes[deck_id]
        direct = node["directMetrics"]
        aggregate = {
            key: direct[key]
            for key in ("reviews", "newCards", "passCount", "failCount", "hardCount", "easyCount", "studySeconds", "directCardCount")
        }
        aggregate["_totalAnswerSeconds"] = direct["_totalAnswerSeconds"]
        aggregate["_activeDates"] = set(direct["_activeDates"])
        for child_id in node["childIds"]:
            child = visit(child_id)
            for key in ("reviews", "newCards", "passCount", "failCount", "hardCount", "easyCount", "studySeconds", "directCardCount"):
                aggregate[key] += child[key]
            aggregate["_totalAnswerSeconds"] += child["_totalAnswerSeconds"]
            aggregate["_activeDates"].update(child["_activeDates"])
        reviews = aggregate["reviews"]
        aggregate["passRate"] = round(aggregate["passCount"] / reviews, 4) if reviews else None
        aggregate["failRate"] = round(aggregate["failCount"] / reviews, 4) if reviews else None
        aggregate["averageAnswerSeconds"] = round(aggregate["_totalAnswerSeconds"] / reviews, 2) if reviews else None
        aggregate["activeDays"] = len(aggregate["_activeDates"]) if active_dates_available else None
        node["subtreeMetrics"] = aggregate
        return aggregate

    for root_id in root_ids:
        visit(root_id)


def _health_model(metrics: dict[str, Any], *, structural_only: bool) -> tuple[str, str, list[str], list[str]]:
    if structural_only:
        return "neutral", "insufficient", ["Узел показан только как контекст выбранной ветки."], []
    reviews = _as_int(metrics.get("reviews"))
    pass_rate = _optional_float(metrics.get("passRate"))
    fail_rate = _optional_float(metrics.get("failRate"))
    average = _optional_float(metrics.get("averageAnswerSeconds"))
    if reviews <= 0:
        return "neutral", "insufficient", ["За выбранный период данных для оценки нет."], ["Продолжать в обычном режиме."]
    if reviews < MIN_REVIEWS_FOR_STRONG_STATUS:
        return "neutral", "preliminary", ["Данных мало, вывод предварительный."], ["Нужно больше данных для оценки."]

    slow = average is not None and average >= SLOW_ANSWER_SECONDS
    if pass_rate is not None and pass_rate < 0.7 or fail_rate is not None and fail_rate >= 0.32:
        status = "danger"
    elif pass_rate is not None and pass_rate < 0.8 or fail_rate is not None and fail_rate >= 0.2 or slow:
        status = "warning"
    elif pass_rate is not None and pass_rate >= 0.9 and (fail_rate is None or fail_rate <= 0.1) and not slow:
        status = "good"
    else:
        status = "neutral"

    reasons: list[str] = []
    if pass_rate is not None and pass_rate < 0.8:
        reasons.append(f"Успешность {round(pass_rate * 100)}% ниже рабочего диапазона.")
    if fail_rate is not None and fail_rate >= 0.2:
        reasons.append(f"Fail составляют {round(fail_rate * 100)}% ответов.")
    if slow:
        reasons.append("Средний ответ заметно медленнее рабочего ориентира.")
    if not reasons:
        reasons.append("По текущим данным явных проблем не видно.")

    if status == "danger":
        recommendations = ["Временно не добавлять новые карточки.", "Разобрать ошибки в Anki Browser."]
    elif status == "warning":
        recommendations = ["Разобрать ошибки перед добавлением новых."]
        if slow:
            recommendations.append("Проверить медленные карточки вручную.")
    else:
        recommendations = ["Продолжать в обычном режиме."]
    return status, "sufficient", reasons[:3], recommendations[:2]


def _descendant_issues(deck_id: int, nodes: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    pending = list(nodes[deck_id]["childIds"])
    while pending:
        child_id = pending.pop()
        child = nodes[child_id]
        pending.extend(child["childIds"])
        if not child["structuralOnly"] and child["aggregateHealth"] in PROBLEM_STATUSES:
            issues.append(
                {
                    "deckId": child_id,
                    "fullName": child["fullName"],
                    "shortName": child["shortName"],
                    "status": child["aggregateHealth"],
                    "reason": child["reasons"][0] if child["reasons"] else "Требует внимания.",
                }
            )
    return sorted(issues, key=lambda item: (STATUS_ORDER[item["status"]], _name_key(item["fullName"]), item["deckId"]))


def _break_parent_cycles(nodes: dict[int, dict[str, Any]]) -> None:
    for start_id in sorted(nodes):
        seen: set[int] = set()
        current_id: int | None = start_id
        while current_id in nodes:
            if current_id in seen:
                nodes[start_id]["parentId"] = None
                break
            seen.add(current_id)
            current_id = nodes[current_id]["parentId"]


def _drop_empty_default(nodes: dict[int, dict[str, Any]], root_ids: list[int]) -> None:
    for deck_id, node in list(nodes.items()):
        if (
            node["fullName"] == "Default"
            and not node["structuralOnly"]
            and not node["childIds"]
            and node["directMetrics"]["directCardCount"] == 0
            and node["directMetrics"]["reviews"] == 0
        ):
            nodes.pop(deck_id, None)
            if deck_id in root_ids:
                root_ids.remove(deck_id)


def _without_internal_metrics(node: dict[str, Any]) -> dict[str, Any]:
    clean = dict(node)
    clean["directMetrics"] = {key: value for key, value in node["directMetrics"].items() if not key.startswith("_")}
    clean["subtreeMetrics"] = {key: value for key, value in node["subtreeMetrics"].items() if not key.startswith("_")}
    return clean


def _parent_names(full_name: str) -> Iterable[str]:
    parts = full_name.split("::")
    for index in range(1, len(parts)):
        yield "::".join(parts[:index])


def _immediate_parent_name(full_name: str) -> str:
    parts = full_name.split("::")
    return "::".join(parts[:-1]) if len(parts) > 1 else ""


def _node_sort_key(node: dict[str, Any]) -> tuple[str, int]:
    return _name_key(node["shortName"]), node["deckId"]


def _name_key(value: object) -> str:
    return str(value or "").casefold()


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _as_float(value: object) -> float:
    return _optional_float(value) or 0.0


def _as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
