from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "anki_study_report"


def load_publication_module():
    package = types.ModuleType("anki_study_report")
    package.__path__ = [str(ADDON)]
    sys.modules["anki_study_report"] = package
    spec = importlib.util.spec_from_file_location(
        "anki_study_report.report_publication",
        ADDON / "report_publication.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["anki_study_report.report_publication"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ready_status(**overrides: Any) -> dict[str, Any]:
    status = {
        "status": "ready",
        "version": 2,
        "updatedAt": 1_782_823_899,
        "cachedDays": 899,
        "cachedDeckDays": 36_644,
        "lastRevlogId": 1_782_823_899_925,
    }
    status.update(overrides)
    return status


def main() -> None:
    publication = load_publication_module()
    base = (("last_30_days", None), "pass_fail", True, False)
    legacy_key = publication.report_metrics_cache_key(
        *base,
        False,
        ready_status(),
    )
    mixed_key = publication.report_metrics_cache_key(
        *base,
        True,
        ready_status(),
    )
    assert legacy_key != mixed_key, (legacy_key, mixed_key)

    refreshed_key = publication.report_metrics_cache_key(
        *base,
        True,
        ready_status(lastRevlogId=1_782_900_000_001),
    )
    assert mixed_key != refreshed_key, (mixed_key, refreshed_key)

    rebuilt_key = publication.report_metrics_cache_key(
        *base,
        True,
        ready_status(updatedAt=1_782_900_000, cachedDays=900),
    )
    assert mixed_key != rebuilt_key, (mixed_key, rebuilt_key)

    empty_key = publication.report_metrics_cache_key(
        *base,
        True,
        ready_status(status="empty", cachedDays=0, cachedDeckDays=0, lastRevlogId=0),
    )
    assert mixed_key != empty_key, (mixed_key, empty_key)

    same_status = publication.report_cache_state_key(ready_status())
    same_status_again = publication.report_cache_state_key(dict(ready_status()))
    assert same_status == same_status_again, (same_status, same_status_again)

    print("REPORT_PUBLICATION_INVALIDATION_SMOKE_OK")


if __name__ == "__main__":
    main()
