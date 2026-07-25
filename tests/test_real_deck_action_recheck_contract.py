from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "docker" / "anki-e2e"


def load_smoke_api():
    artifact_paths = types.ModuleType("artifact_paths")
    artifact_paths.ArtifactPaths = object
    sys.modules["artifact_paths"] = artifact_paths
    path = E2E / "smoke-api.py"
    spec = importlib.util.spec_from_file_location("asr_smoke_api_action_recheck", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_action_recheck_uses_automatic_triage_contract() -> None:
    smoke_api = load_smoke_api()
    assert smoke_api.automatic_triage_request() == {
        "schemaVersion": 4,
        "dataset": "automatic",
        "scope": {"periodStartMs": 0, "periodEndMs": 9_007_199_254_740_991, "deckIds": []},
        "limit": 100,
        "contentCursor": None,
    }


def test_action_recheck_passes_authoritative_learning_reasons(monkeypatch) -> None:
    smoke_api = load_smoke_api()
    calls: list[tuple[str, dict]] = []

    def fake_post_json(_base_url: str, path: str, _token: str, payload: dict):
        calls.append((path, payload))
        if path == "/api/triage/query":
            return {
                "schemaVersion": 4,
                "dataset": "automatic",
                "items": [
                    {
                        "cardId": "999",
                        "noteId": "998",
                        "reasons": [{"reasonId": "learning:learning.repeated_again"}],
                    },
                    {
                        "cardId": "11",
                        "noteId": "12",
                        "reasons": [
                            {"reasonId": "learning:learning.low_pass_rate"},
                            {"reasonId": "learning:learning.repeated_again"},
                        ],
                    },
                ],
            }
        if path == "/api/triage/recheck":
            assert payload["cardId"] == "11"
            assert payload["expectedNoteId"] == "12"
            assert payload["reasonIds"] == [
                "learning:learning.low_pass_rate",
                "learning:learning.repeated_again",
            ]
            return {
                "schemaVersion": 1,
                "cardId": "11",
                "status": "confirmed",
                "entityStatus": "available",
            }
        raise AssertionError(path)

    monkeypatch.setattr(smoke_api, "post_json", fake_post_json)
    result = smoke_api.assert_action_recheck(
        "http://127.0.0.1:8766",
        "token",
        {"cardId": 11, "noteId": 12},
    )

    assert [path for path, _payload in calls] == ["/api/triage/query", "/api/triage/recheck"]
    assert result == {
        "cardId": 11,
        "reasonIds": ["learning:learning.low_pass_rate", "learning:learning.repeated_again"],
        "sourceDataset": "automatic",
        "status": "confirmed",
        "entityStatus": "available",
    }
