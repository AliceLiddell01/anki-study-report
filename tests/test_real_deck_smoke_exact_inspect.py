from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "docker" / "anki-e2e"


def test_real_deck_smokes_use_exact_search_inspect_for_preview_anchors() -> None:
    api = (E2E / "smoke-api.py").read_text(encoding="utf-8")
    browser = (E2E / "smoke-browser.mjs").read_text(encoding="utf-8")

    for source in (api, browser):
        assert "/api/search/inspect" in source
        assert '"mode": "cards"' in source or 'mode: "cards"' in source
        assert "pageSize: 200" not in source
        assert '"pageSize": 200' not in source
        assert "collect_card_candidates" not in source
        assert "collectCardCandidates" not in source


def test_exact_inspect_requests_are_bound_to_manifest_card_ids() -> None:
    api = (E2E / "smoke-api.py").read_text(encoding="utf-8")
    browser = (E2E / "smoke-browser.mjs").read_text(encoding="utf-8")

    assert '"cardId": card_id' in api
    assert 'str(card.get("cardId")) == card_id' in api
    assert "cardId: String(selectedAnchor.cardId)" in browser
    assert "String(details.cardId) !== String(selectedAnchor.cardId)" in browser
