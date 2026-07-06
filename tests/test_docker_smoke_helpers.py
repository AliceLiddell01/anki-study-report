from __future__ import annotations

import importlib.util
from pathlib import Path


def load_smoke_api_module():
    path = Path(__file__).resolve().parents[1] / "docker" / "anki-e2e" / "smoke-api.py"
    spec = importlib.util.spec_from_file_location("anki_study_report_smoke_api", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(label: str) -> dict[str, str]:
    return {"source": label}


def test_smoke_api_card_rows_prefer_canonical_attention_cards():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report(
        {
            "attentionCards": [row("attentionCards")],
            "cards": [row("cards")],
        }
    ) == [row("attentionCards")]


def test_smoke_api_card_rows_keep_empty_canonical_result():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report(
        {
            "attentionCards": [],
            "cards": [row("cards")],
        }
    ) == []


def test_smoke_api_card_rows_fall_back_to_cards_alias():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report({"cards": [row("cards")]}) == [row("cards")]


def test_smoke_api_card_rows_ignore_removed_card_issues_alias():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report({"cardIssues": [row("cardIssues")]}) == []


def test_smoke_api_card_rows_ignore_removed_problem_cards_alias():
    smoke_api = load_smoke_api_module()

    assert smoke_api._card_rows_from_report({"problemCards": [row("problemCards")]}) == []
