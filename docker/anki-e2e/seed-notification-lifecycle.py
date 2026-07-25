#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


CARD_ANCHORS = ("cards-action-recheck", "cards-low-success")
DECK_ANCHOR = "cards-action-recheck"


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed deterministic notification lifecycle state in the isolated E2E profile.")
    parser.add_argument("--addon-dir", required=True, type=Path)
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()

    anchor, card_ids, deck_id = load_real_deck_context(args.artifacts_dir)

    module = load_store(args.addon_dir / "notification_store.py")
    data_dir = (args.profile_dir / "addon_data" / "anki_study_report_e2e").resolve()
    profile_root = args.profile_dir.resolve()
    data_dir.relative_to(profile_root)
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "notifications.sqlite3"
    for candidate in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm"), Path(f"{db_path}-journal")):
        candidate.unlink(missing_ok=True)

    store = module.NotificationStore(db_path)
    try:
        for code in module.EVIDENCE_FIELDS:
            store.reconcile(code, [], source_revision=f"e2e:normal:{code}", evaluated_at=timestamp(anchor))

        workload = signal("workload.review_pressure", "workload", "warning", "workload.review_pressure:all", "all_collection", None, {
            "currentLoad": 75, "baselineMedian": 30.0, "activeDays": 20, "ratio": 2.5, "delta": 45.0,
        })
        store.reconcile("workload.review_pressure", [workload], source_revision="e2e:workload-warning", evaluated_at=timestamp(anchor, 1))
        workload["severity"] = "critical"
        workload["evidence"] = {**workload["evidence"], "currentLoad": 150, "ratio": 5.0, "delta": 120.0}
        store.reconcile("workload.review_pressure", [workload], source_revision="e2e:workload-critical", evaluated_at=timestamp(anchor, 2))
        store.reconcile("workload.review_pressure", [], source_revision="e2e:workload-missing-1", evaluated_at=timestamp(anchor, 3))
        store.reconcile("workload.review_pressure", [], source_revision="e2e:workload-resolved", evaluated_at=timestamp(anchor, 4))

        retention = signal("retention.recent_drop", "retention", "warning", "retention.recent_drop:all", "all_collection", None, {
            "recentAnswers": 70, "baselineAnswers": 280, "recentRetention": 0.8, "baselineRetention": 0.9, "dropPoints": 10.0,
        })
        store.reconcile("retention.recent_drop", [retention], source_revision="e2e:retention-warning", evaluated_at=timestamp(anchor, 5))

        deck = signal("deck.health_decline", "deck_health", "warning", f"deck.health_decline:{deck_id}", "deck", deck_id, {
            "health": "warning", "reviews": 20, "passRate": 0.7, "failRate": 0.3, "averageAnswerSeconds": 12.0,
        })
        store.reconcile("deck.health_decline", [deck], source_revision="e2e:deck-warning", evaluated_at=timestamp(anchor, 6))

        resolved_card = signal("card.repeated_again", "card_problems", "critical", f"card.repeated_again:{card_ids[0]}", "card", card_ids[0], {
            "againCount": 5, "reviewCount": 7, "windowDays": 7, "lastReviewAt": timestamp(anchor, 7),
        })
        active_card = signal("card.repeated_again", "card_problems", "warning", f"card.repeated_again:{card_ids[1]}", "card", card_ids[1], {
            "againCount": 3, "reviewCount": 5, "windowDays": 7, "lastReviewAt": timestamp(anchor, 8),
        })
        store.reconcile("card.repeated_again", [resolved_card, active_card], source_revision="e2e:cards-created", evaluated_at=timestamp(anchor, 8))
        store.reconcile("card.repeated_again", [active_card], source_revision="e2e:card-missing-1", evaluated_at=timestamp(anchor, 9))
        store.reconcile("card.repeated_again", [active_card], source_revision="e2e:card-resolved", evaluated_at=timestamp(anchor, 10))

        history = store.list_notifications(page_limit=50)
        store.mark_toast_delivered([item["notificationId"] for item in history["items"]], delivered_at=timestamp(anchor, 11))
        store.update_preferences({"showInAppToasts": False})
        status_counts = Counter(item["signalStatus"] or "release" for item in history["items"])
        kind_counts = Counter(item["kind"] for item in history["items"])
        category_counts = Counter(item["category"] for item in history["items"])
        proof = {
            "ok": True,
            "fixtureSchemaVersion": 2,
            "contentSource": "committed-real-apkg-anchors",
            "anchorIds": list(CARD_ANCHORS),
            "deckAnchorId": DECK_ANCHOR,
            "normalEvaluationWasEmpty": True,
            "notificationCount": history["total"],
            "activeSignalCount": store.summary()["activeSignalCount"],
            "statusCounts": dict(sorted(status_counts.items())),
            "kindCounts": dict(sorted(kind_counts.items())),
            "categoryCounts": dict(sorted(category_counts.items())),
            "lifecycle": {"warning": True, "critical": True, "missingOnce": True, "resolved": True, "reactivationDeferredToSession": True, "severityEscalated": True},
        }
        (args.artifacts_dir / "notification-fixture-proof.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        store.close()
    print("Seeded isolated notification lifecycle state from real-deck anchors.")
    return 0


def load_real_deck_context(artifacts_dir: Path) -> tuple[datetime, list[int], int]:
    anchors_report = read_pass_report(artifacts_dir / "anchor-resolution-report.json")
    scenarios_report = read_pass_report(artifacts_dir / "scenario-application-report.json")
    anchors = anchors_report.get("anchors")
    if not isinstance(anchors, dict):
        raise RuntimeError("Real-deck anchor report must contain an anchors object.")

    card_ids = [positive_int(anchor_row(anchors, anchor_id).get("cardId"), f"{anchor_id}.cardId") for anchor_id in CARD_ANCHORS]
    if len(set(card_ids)) != len(card_ids):
        raise RuntimeError("Notification E2E requires two distinct manifest card anchors.")
    deck_id = positive_int(anchor_row(anchors, DECK_ANCHOR).get("deckId"), f"{DECK_ANCHOR}.deckId")

    scheduler_day = scenarios_report.get("schedulerDay")
    if not isinstance(scheduler_day, dict):
        raise RuntimeError("Scenario report must contain schedulerDay evidence.")
    start_ms = positive_int(scheduler_day.get("startMs"), "schedulerDay.startMs")
    cutoff_ms = positive_int(scheduler_day.get("cutoffMs"), "schedulerDay.cutoffMs")
    if start_ms >= cutoff_ms:
        raise RuntimeError("Scheduler-day start must be earlier than its cutoff.")
    anchor = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).replace(microsecond=0)
    return anchor, card_ids, deck_id


def read_pass_report(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read required real-deck report {path.name}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schemaVersion") != 1 or value.get("status") != "PASS":
        raise RuntimeError(f"Required real-deck report is not a schema-v1 PASS: {path.name}")
    return value


def anchor_row(anchors: dict[str, Any], anchor_id: str) -> dict[str, Any]:
    row = anchors.get(anchor_id)
    if not isinstance(row, dict) or row.get("status") != "PASS":
        raise RuntimeError(f"Required notification anchor is unavailable: {anchor_id}")
    return row


def positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{label} must be a positive integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} must be a positive integer.") from exc
    if parsed <= 0:
        raise RuntimeError(f"{label} must be a positive integer.")
    return parsed


def load_store(path: Path):
    spec = importlib.util.spec_from_file_location("anki_study_report_notification_store_e2e", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load installed notification store.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def signal(code, category, severity, dedupe_key, entity_type, entity_id, evidence):
    return {"code": code, "category": category, "severity": severity, "dedupeKey": dedupe_key, "entityType": entity_type, "entityId": entity_id, "evidence": evidence, "detectorVersion": "signals-v1.0"}


def timestamp(anchor: datetime, seconds: int = 0) -> str:
    return (anchor + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
