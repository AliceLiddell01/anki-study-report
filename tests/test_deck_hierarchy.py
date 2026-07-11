from __future__ import annotations

from conftest import fresh_import_addon_module


def catalog(*rows):
    return [
        {
            "deck_id": deck_id,
            "deck_name": name,
            "filtered": filtered,
            "direct_card_count": cards,
            **extra,
        }
        for deck_id, name, filtered, cards, extra in rows
    ]


def direct(deck_id, reviews, passed, failed, *, new=0, average=10.0, dates=None):
    return {
        "deck_id": deck_id,
        "total_reviews": reviews,
        "pass_count": passed,
        "fail_count": failed,
        "new_cards": new,
        "average_answer_seconds": average,
        "total_answer_seconds": average * reviews,
        "_active_dates": dates or [],
    }


def build(deck_catalog, rows=(), **kwargs):
    module = fresh_import_addon_module("deck_hub")
    return module.build_deck_hub(deck_catalog, list(rows), **kwargs)


def test_single_root_and_empty_default_handling():
    hub = build(catalog((10, "Japanese", False, 12, {})), [direct(10, 20, 18, 2)])
    assert hub["rootIds"] == [10]
    assert hub["nodes"]["10"]["directMetrics"] == hub["nodes"]["10"]["subtreeMetrics"]

    empty = build(catalog((1, "Default", False, 0, {})))
    assert empty["rootIds"] == []
    assert empty["summary"]["totalDecks"] == 0

    mixed = build(catalog((1, "Default", False, 0, {}), (2, "Japanese", False, 1, {})))
    assert mixed["rootIds"] == [2]
    assert set(mixed["nodes"]) == {"2"}


def test_deep_hierarchy_uses_stable_ids_and_sorts_only_siblings():
    hub = build(
        catalog(
            (1, "Root", False, 0, {}),
            (2, "Root::10", False, 1, {}),
            (3, "Root::2", False, 1, {}),
            (4, "Root::2::文法", False, 1, {}),
            (5, "Root::2::文法::L1", False, 1, {}),
            (6, "Other::2", False, 1, {}),
            (7, "Other", False, 0, {}),
        )
    )
    assert hub["rootIds"] == [7, 1]
    assert hub["nodes"]["1"]["childIds"] == [2, 3]
    assert hub["nodes"]["3"]["childIds"] == [4]
    assert hub["nodes"]["4"]["childIds"] == [5]
    assert hub["nodes"]["3"]["shortName"] == hub["nodes"]["6"]["shortName"] == "2"
    assert hub["nodes"]["3"]["fullName"] != hub["nodes"]["6"]["fullName"]


def test_parent_subtree_sums_direct_rows_once_with_weighted_values_and_active_day_union():
    hub = build(
        catalog(
            (1, "Words", False, 2, {}),
            (2, "Words::N3", False, 4, {}),
            (3, "Words::N2", False, 3, {}),
        ),
        [
            direct(1, 10, 9, 1, new=1, average=10, dates=["2026-07-01"]),
            direct(2, 30, 15, 15, new=2, average=20, dates=["2026-07-01", "2026-07-02"]),
            direct(3, 60, 54, 6, new=3, average=5, dates=["2026-07-02"]),
        ],
        active_dates_available=True,
    )
    parent = hub["nodes"]["1"]
    assert parent["directMetrics"]["reviews"] == 10
    assert parent["subtreeMetrics"]["reviews"] == 100
    assert parent["subtreeMetrics"]["newCards"] == 6
    assert parent["subtreeMetrics"]["passRate"] == 0.78
    assert parent["subtreeMetrics"]["averageAnswerSeconds"] == 10.0
    assert parent["subtreeMetrics"]["activeDays"] == 2
    assert parent["subtreeMetrics"]["directCardCount"] == 9


def test_parent_health_uses_subtree_and_does_not_inherit_worst_child():
    hub = build(
        catalog(
            (1, "Words", False, 0, {}),
            (2, "Words::Healthy", False, 20, {}),
            (3, "Words::Danger", False, 10, {}),
        ),
        [direct(2, 90, 90, 0), direct(3, 10, 3, 7)],
    )
    parent = hub["nodes"]["1"]
    danger = hub["nodes"]["3"]
    assert parent["aggregateHealth"] == "good"
    assert danger["aggregateHealth"] == "danger"
    assert parent["descendantIssueCount"] == 1
    assert parent["descendantIssues"][0]["deckId"] == 3
    assert hub["summary"]["attentionDecks"] == 1
    assert hub["summary"]["dangerDecks"] == 1
    assert hub["summary"]["groupsWithDescendantIssues"] == 1


def test_confidence_is_independent_and_preliminary_high_rate_is_not_good():
    hub = build(
        catalog((1, "Tiny", False, 1, {}), (2, "Empty", False, 1, {})),
        [direct(1, 1, 1, 0)],
    )
    assert hub["nodes"]["1"]["dataConfidence"] == "preliminary"
    assert hub["nodes"]["1"]["aggregateHealth"] == "neutral"
    assert hub["nodes"]["2"]["dataConfidence"] == "insufficient"


def test_filtered_decks_are_excluded_without_polluting_totals():
    hub = build(
        catalog(
            (1, "Normal", False, 10, {}),
            (2, "Filtered", True, 0, {}),
        ),
        [direct(1, 20, 18, 2), direct(2, 99, 0, 99)],
    )
    assert set(hub["nodes"]) == {"1"}
    assert hub["summary"]["totalDecks"] == 1
    assert hub["summary"]["aggregatePassRate"] == 0.9
    assert hub["summary"]["filteredDecksExcluded"] == 1


def test_selected_scope_keeps_real_ancestors_as_structural_context_only():
    hub = build(
        catalog(
            (1, "Root", False, 5, {}),
            (2, "Root::Shown", False, 5, {}),
            (3, "Root::Hidden", False, 5, {}),
        ),
        [direct(1, 100, 0, 100), direct(2, 20, 18, 2), direct(3, 50, 0, 50)],
        selected_deck_ids=[2],
    )
    assert set(hub["nodes"]) == {"1", "2"}
    assert hub["nodes"]["1"]["structuralOnly"] is True
    assert hub["nodes"]["1"]["subtreeMetrics"]["reviews"] == 20
    assert hub["summary"]["totalDecks"] == 1
    assert hub["summary"]["aggregatePassRate"] == 0.9


def test_missing_parent_and_cyclic_parent_data_fall_back_safely():
    missing = build(catalog((2, "Missing::Child", False, 1, {})))
    assert missing["rootIds"] == [2]

    cyclic = build(
        catalog(
            (1, "One", False, 1, {"parent_id": 2}),
            (2, "Two", False, 1, {"parent_id": 1}),
        )
    )
    assert cyclic["rootIds"]
    assert set(cyclic["nodes"]) == {"1", "2"}


def test_output_is_deterministic_and_public_json_contains_no_private_rows():
    deck_catalog = catalog((1, "Root", False, 1, {}), (2, "Root::Child", False, 1, {}))
    rows = [direct(2, 10, 8, 2, dates=["2026-07-01"])]
    first = build(deck_catalog, rows, active_dates_available=True)
    second = build(list(reversed(deck_catalog)), list(reversed(rows)), active_dates_available=True)
    assert first == second
    text = repr(first)
    for forbidden in ("token=", "collection.anki2", "frontHtml", "revlog", "_activeDates"):
        assert forbidden not in text


def test_collect_catalog_uses_home_deck_card_counts_and_dyn_flag():
    module = fresh_import_addon_module("deck_hub")

    class Db:
        def all(self, query):
            assert "odid > 0" in query
            return [(10, 3), (20, 2)]

    class Decks:
        def all(self):
            return [
                {"id": 10, "name": "Root", "dyn": 0},
                {"id": 20, "name": "Filtered", "dyn": 1},
            ]

    col = type("Col", (), {"db": Db(), "decks": Decks()})()
    result = module.collect_deck_catalog(col)
    assert result == [
        {"deck_id": 20, "deck_name": "Filtered", "filtered": True, "direct_card_count": 2},
        {"deck_id": 10, "deck_name": "Root", "filtered": False, "direct_card_count": 3},
    ]


def test_large_collection_stays_normalized_and_counts_each_node_once():
    deck_catalog = catalog((1, "Root", False, 0, {}))
    rows = []
    for deck_id in range(2, 162):
        deck_catalog.extend(catalog((deck_id, f"Root::Deck {deck_id:03d}", False, 1, {})))
        rows.append(direct(deck_id, 10, 9, 1))
    hub = build(deck_catalog, rows)
    assert hub["summary"]["totalDecks"] == 161
    assert hub["nodes"]["1"]["subtreeMetrics"]["reviews"] == 1600
    assert len(hub["nodes"]) == 161
    assert hub["nodes"]["1"]["childIds"] == list(range(2, 162))
