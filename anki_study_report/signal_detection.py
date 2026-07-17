"""Bounded pure detectors and revision-gated signal reconciliation."""

from __future__ import annotations

from datetime import date, datetime, time as datetime_time, timedelta, timezone
import math
from statistics import median
import threading
import time
from typing import Any, Callable

from .notification_store import NotificationStore


DETECTOR_VERSION = "signals-v1.0"
DETECTOR_CODES = (
    "workload.review_pressure",
    "retention.recent_drop",
    "deck.health_decline",
    "card.repeated_again",
)
CARD_RESULT_LIMIT = 50


def detect_review_pressure(snapshot: Any, current: Any, today_key: str) -> list[dict[str, Any]]:
    rows = _daily_rows(snapshot, today_key)
    previous = [row for row in rows if row["date"] < today_key][-28:]
    active = [row for row in previous if _int(row.get("reviews")) > 0]
    if len(active) < 14:
        return []
    baseline = float(median(_int(row.get("reviews")) for row in active))
    due_rows = current.get("due") if isinstance(current, dict) and isinstance(current.get("due"), list) else []
    load = sum(_int(row.get("count")) for row in due_rows if isinstance(row, dict) and _int(row.get("dayOffset")) <= 0)
    critical = max(baseline * 2.0, baseline + 100)
    warning = max(baseline * 1.5, baseline + 30)
    severity = "critical" if load >= critical else "warning" if load >= warning else None
    if severity is None:
        return []
    return [_candidate(
        "workload.review_pressure", "workload", severity, "workload.review_pressure:all",
        "all_collection", None,
        {
            "currentLoad": load,
            "baselineMedian": round(baseline, 2),
            "activeDays": len(active),
            "ratio": round(load / baseline, 3) if baseline > 0 else None,
            "delta": round(load - baseline, 2),
        },
    )]


def detect_recent_retention_drop(snapshot: Any, _current: Any, today_key: str) -> list[dict[str, Any]]:
    rows = _daily_rows(snapshot, today_key)
    active = [row for row in rows if _retention_answers(row) > 0]
    recent = active[-7:]
    baseline = active[:-7][-28:]
    recent_answers = sum(_retention_answers(row) for row in recent)
    baseline_answers = sum(_retention_answers(row) for row in baseline)
    if len(recent) < 7 or len(baseline) < 1 or recent_answers < 50 or baseline_answers < 200:
        return []
    recent_pass = sum(_int(row.get("retention_pass_count")) for row in recent)
    baseline_pass = sum(_int(row.get("retention_pass_count")) for row in baseline)
    recent_rate = recent_pass / recent_answers
    baseline_rate = baseline_pass / baseline_answers
    drop_points = (baseline_rate - recent_rate) * 100
    severity = "critical" if drop_points >= 15 else "warning" if drop_points >= 8 else None
    if severity is None:
        return []
    return [_candidate(
        "retention.recent_drop", "retention", severity, "retention.recent_drop:all",
        "all_collection", None,
        {
            "recentAnswers": recent_answers,
            "baselineAnswers": baseline_answers,
            "recentRetention": round(recent_rate, 4),
            "baselineRetention": round(baseline_rate, 4),
            "dropPoints": round(drop_points, 2),
        },
    )]


def detect_deck_health_decline(_snapshot: Any, current: Any, _today_key: str) -> list[dict[str, Any]]:
    hub = current.get("deckHub") if isinstance(current, dict) else None
    nodes = hub.get("nodes") if isinstance(hub, dict) and isinstance(hub.get("nodes"), dict) else {}
    candidates = []
    for key, node in nodes.items():
        if not isinstance(node, dict) or node.get("structuralOnly") is True:
            continue
        health = str(node.get("aggregateHealth") or "neutral")
        if health not in {"warning", "danger"}:
            continue
        metrics = node.get("subtreeMetrics") if isinstance(node.get("subtreeMetrics"), dict) else {}
        deck_id = _int(node.get("deckId", key))
        if deck_id <= 0:
            continue
        candidates.append(_candidate(
            "deck.health_decline", "deck_health", "critical" if health == "danger" else "warning",
            f"deck.health_decline:{deck_id}", "deck", deck_id,
            {
                "health": health,
                "reviews": _int(metrics.get("reviews")),
                "passRate": _optional_number(metrics.get("passRate")),
                "failRate": _optional_number(metrics.get("failRate")),
                "averageAnswerSeconds": _optional_number(metrics.get("averageAnswerSeconds")),
            },
        ))
    return sorted(candidates, key=lambda item: (-_severity_rank(item["severity"]), int(item["entityId"])))


def detect_repeated_again_cards(_snapshot: Any, current: Any, _today_key: str) -> list[dict[str, Any]]:
    rows = current.get("repeatedAgainCards") if isinstance(current, dict) and isinstance(current.get("repeatedAgainCards"), list) else []
    candidates = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        again = _int(row.get("againCount"))
        reviews = _int(row.get("reviewCount"))
        card_id = _int(row.get("cardId"))
        if card_id <= 0 or reviews < 4 or again < 3:
            continue
        candidates.append(_candidate(
            "card.repeated_again", "card_problems", "critical" if again >= 5 else "warning",
            f"card.repeated_again:{card_id}", "card", card_id,
            {
                "againCount": again,
                "reviewCount": reviews,
                "windowDays": 7,
                "lastReviewAt": str(row.get("lastReviewAt") or "")[:40],
            },
        ))
    return sorted(
        candidates,
        key=lambda item: (_severity_rank(item["severity"]), int(item["evidence"]["againCount"]), item["evidence"]["lastReviewAt"]),
        reverse=True,
    )[:CARD_RESULT_LIMIT]


DETECTORS: dict[str, Callable[[Any, Any, str], list[dict[str, Any]]]] = {
    "workload.review_pressure": detect_review_pressure,
    "retention.recent_drop": detect_recent_retention_drop,
    "deck.health_decline": detect_deck_health_decline,
    "card.repeated_again": detect_repeated_again_cards,
}


class SignalEvaluator:
    """Run each detector independently and reconcile a source revision once."""

    def __init__(self, store: NotificationStore, *, diagnostic_logger: Callable[..., None] | None = None) -> None:
        self.store = store
        self._diagnostic_logger = diagnostic_logger
        self._lock = threading.Lock()

    def evaluate(self, snapshot: Any, current: Any, today_key: str, *, source_revision: str, evaluated_at: str | None = None) -> dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            return {"ok": True, "skipped": "evaluation_in_progress", "detectors": {}}
        results = {}
        try:
            failures = set(current.get("detectorFailures", [])) if isinstance(current, dict) else set()
            for code in DETECTOR_CODES:
                if code in failures:
                    results[code] = {"status": "failed", "diagnosticCode": "signal_detector_source_failed"}
                    self._log(code, "lt_10ms", 0, 0, diagnostic_code="signal_detector_source_failed")
                    continue
                if self.store.detector_revision(code) == source_revision:
                    results[code] = {"status": "unchanged_revision"}
                    continue
                started = time.perf_counter()
                try:
                    candidates = DETECTORS[code](snapshot, current, today_key)
                    reconciled = self.store.reconcile(code, candidates, source_revision=source_revision, evaluated_at=evaluated_at)
                    duration_ms = (time.perf_counter() - started) * 1000
                    results[code] = {"status": "ok", "candidateCount": len(candidates), **reconciled}
                    self._log(code, _duration_bucket(duration_ms), len(candidates), len(candidates))
                except Exception:
                    duration_ms = (time.perf_counter() - started) * 1000
                    results[code] = {"status": "failed", "diagnosticCode": "signal_detector_failed"}
                    self._log(code, _duration_bucket(duration_ms), 0, 0, diagnostic_code="signal_detector_failed")
            return {"ok": True, "detectors": results}
        finally:
            self._lock.release()

    def _log(self, code: str, bucket: str, candidates: int, results: int, *, diagnostic_code: str | None = None) -> None:
        if self._diagnostic_logger is not None:
            self._diagnostic_logger(
                "signals.detector",
                "Signal detector evaluated",
                detector_code=code,
                duration_bucket=bucket,
                candidate_count=max(0, int(candidates)),
                result_count=max(0, int(results)),
                diagnostic_code=diagnostic_code,
            )


def collect_repeated_again_cards(col: Any, today_key: str) -> list[dict[str, Any]]:
    """One bounded grouped revlog query; returns no card content."""
    cutoff_ms = _seven_day_review_cutoff_ms(col, today_key)
    rows = col.db.all(
        """
        SELECT cid,
          SUM(CASE WHEN ease = 1 THEN 1 ELSE 0 END) AS again_count,
          COUNT(*) AS review_count,
          MAX(id) AS last_review_id
        FROM revlog
        WHERE id >= ?
        GROUP BY cid
        HAVING COUNT(*) >= 4 AND SUM(CASE WHEN ease = 1 THEN 1 ELSE 0 END) >= 3
        ORDER BY again_count DESC, last_review_id DESC, cid
        LIMIT 50
        """,
        cutoff_ms,
    )
    result = []
    for card_id, again, reviews, last_id in rows:
        last = datetime.fromtimestamp(_int(last_id) / 1000, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        result.append({"cardId": _int(card_id), "againCount": _int(again), "reviewCount": _int(reviews), "lastReviewAt": last})
    return result[:CARD_RESULT_LIMIT]


def _seven_day_review_cutoff_ms(col: Any, today_key: str) -> int:
    try:
        next_day_at = int(col.sched.day_cutoff)
        if next_day_at > 7 * 86400:
            return (next_day_at - 7 * 86400) * 1000
    except (AttributeError, TypeError, ValueError):
        pass
    today = date.fromisoformat(today_key)
    cutoff = datetime.combine(today - timedelta(days=6), datetime_time.min, tzinfo=timezone.utc)
    return int(cutoff.timestamp() * 1000)


def source_revision(snapshot: Any, today_key: str) -> str:
    status = snapshot.get("status") if isinstance(snapshot, dict) and isinstance(snapshot.get("status"), dict) else {}
    return f"cache:{_int(status.get('updatedAt'))}:revlog:{_int(status.get('lastRevlogId'))}:day:{today_key}"


def _daily_rows(snapshot: Any, today_key: str) -> list[dict[str, Any]]:
    source = snapshot.get("daily") if isinstance(snapshot, dict) and isinstance(snapshot.get("daily"), list) else []
    rows = [dict(row) for row in source if isinstance(row, dict) and str(row.get("date") or "") <= today_key]
    return sorted(rows, key=lambda row: str(row.get("date") or ""))


def _retention_answers(row: dict[str, Any]) -> int:
    return _int(row.get("retention_pass_count")) + _int(row.get("retention_fail_count"))


def _candidate(code: str, category: str, severity: str, dedupe_key: str, entity_type: str, entity_id: int | None, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": code,
        "category": category,
        "severity": severity,
        "dedupeKey": dedupe_key,
        "entityType": entity_type,
        "entityId": entity_id,
        "evidence": evidence,
        "detectorVersion": DETECTOR_VERSION,
    }


def _duration_bucket(duration_ms: float) -> str:
    return "lt_10ms" if duration_ms < 10 else "lt_50ms" if duration_ms < 50 else "lt_250ms" if duration_ms < 250 else "gte_250ms"


def _severity_rank(value: str) -> int:
    return {"info": 0, "warning": 1, "critical": 2}.get(value, 0)


def _optional_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 4) if math.isfinite(number) else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
