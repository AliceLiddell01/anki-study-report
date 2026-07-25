"""Independent bounded candidate sources for canonical Cards triage.

Learning candidates are period-bound and read review history only. Current-content
candidates are period-independent, profile-authoritative, note-keyset paged, and
use a constant number of collection DB calls per request.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .inspection_profile_service import (
    content_reason_from_failure,
    effective_profile_state,
    evaluate_inspection_profile,
    read_note_type_structures,
)
from .inspection_profile_store import MAX_PROFILES
from .metrics import (
    ANSWER_TIME_CAP_MS,
    ATTENTION_CARD_LEECH_LAPSE_THRESHOLD,
    ATTENTION_CARD_LIMIT,
    ATTENTION_CARD_LOW_PASS_MIN_REVIEWS,
    ATTENTION_CARD_LOW_PASS_RATE,
    ATTENTION_CARD_REPEATED_AGAIN_MIN,
    ATTENTION_CARD_SLOW_SECONDS,
    REVLOG_REVIEW_FILTER_SQL,
    expand_deck_ids,
)

CONTENT_SCAN_NOTE_LIMIT = 500
CONTENT_MAX_TEMPLATE_ORDINAL = 31
CONTENT_CARD_FETCH_LIMIT = CONTENT_SCAN_NOTE_LIMIT * (CONTENT_MAX_TEMPLATE_ORDINAL + 1)
MAX_SIGNED_ID = 9_223_372_036_854_775_807


def collect_learning_triage_candidates_with_status(
    col: Any,
    period_start_ms: int,
    period_end_ms: int,
    deck_ids: list[int],
    *,
    max_results: int = ATTENTION_CARD_LIMIT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read bounded period learning candidates without note fields or rendering."""

    if col is None or getattr(col, "db", None) is None:
        return [], source_status("unavailable", error_code="collection_unavailable")
    limit = max(1, min(ATTENTION_CARD_LIMIT, int(max_results)))
    try:
        expanded = expand_deck_ids(col, deck_ids) if deck_ids else None
        deck_sql, deck_params = _deck_filter(expanded)
        rows = col.db.all(
            f"""
            select
                c.id,
                c.nid,
                c.lapses,
                n.mid,
                c.ord,
                n.tags,
                count(*) as total_reviews,
                coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
                coalesce(sum(case when r.time < 0 then 0 when r.time > ? then ? else r.time end), 0) as total_ms,
                max(r.id) as last_reviewed_ms
            from revlog r
            join cards c on c.id = r.cid
            join notes n on n.id = c.nid
            where r.id >= ? and r.id < ?
              {REVLOG_REVIEW_FILTER_SQL}
              {deck_sql}
            group by c.id, c.nid, c.lapses, n.mid, c.ord, n.tags
            order by max(r.id) desc, c.id asc
            limit ?
            """,
            ANSWER_TIME_CAP_MS,
            ANSWER_TIME_CAP_MS,
            period_start_ms,
            period_end_ms,
            *deck_params,
            limit + 1,
        )
    except Exception:
        return [], source_status("error", error_code="learning_source_failed")

    truncated = len(rows) > limit
    result: list[dict[str, Any]] = []
    skipped = 0
    for row in rows[:limit]:
        payload = _learning_payload(row)
        if payload is None:
            skipped += 1
        elif payload["issues"]:
            result.append(payload)
    state = "partial" if skipped or truncated else ("available" if result else "empty")
    return result, source_status(
        state,
        item_count=len(result),
        skipped_count=skipped,
        truncated=truncated,
        error_code="learning_rows_skipped" if skipped else None,
    )


def collect_exact_learning_triage_candidate_with_status(
    col: Any,
    card_id: int,
    period_start_ms: int,
    period_end_ms: int,
    deck_ids: list[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Evaluate the canonical learning detectors for one exact current card."""

    if col is None or getattr(col, "db", None) is None:
        return [], source_status("unavailable", error_code="collection_unavailable")
    exact_card_id = _positive_int(card_id)
    if not exact_card_id:
        return [], source_status("error", error_code="learning_card_invalid")
    try:
        expanded = expand_deck_ids(col, deck_ids) if deck_ids else None
        deck_sql, deck_params = _deck_filter(expanded)
        rows = col.db.all(
            f"""
            select
                c.id,
                c.nid,
                c.lapses,
                n.mid,
                c.ord,
                n.tags,
                count(*) as total_reviews,
                coalesce(sum(case when r.ease = 1 then 1 else 0 end), 0) as again_count,
                coalesce(sum(case when r.time < 0 then 0 when r.time > ? then ? else r.time end), 0) as total_ms,
                max(r.id) as last_reviewed_ms
            from cards c
            join notes n on n.id = c.nid
            join revlog r on r.cid = c.id
                and r.id >= ? and r.id < ?
                {REVLOG_REVIEW_FILTER_SQL}
            where c.id = ?
              {deck_sql}
            group by c.id, c.nid, c.lapses, n.mid, c.ord, n.tags
            """,
            ANSWER_TIME_CAP_MS,
            ANSWER_TIME_CAP_MS,
            period_start_ms,
            period_end_ms,
            exact_card_id,
            *deck_params,
        )
    except Exception:
        return [], source_status("error", error_code="learning_source_failed")

    if not rows:
        return [], source_status("empty")
    payload = _learning_payload(rows[0])
    if payload is None:
        return [], source_status(
            "partial",
            skipped_count=1,
            error_code="learning_rows_skipped",
        )
    result = [payload] if payload["issues"] else []
    return result, source_status(
        "available" if result else "empty",
        item_count=len(result),
    )


def collect_current_content_candidates(
    col: Any,
    deck_ids: list[int],
    content_cursor: int | None,
    store_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Read and evaluate one bounded current-content note batch."""

    inventory = _authoritative_profile_inventory(col, store_snapshot)
    if inventory["terminal"]:
        return {
            "reasons": [],
            "sourceStatus": content_source_status(
                inventory["sourceState"],
                error_code=inventory["errorCode"],
            ),
            "profileSourceStatus": source_status(
                inventory["profileState"],
                error_code=inventory["errorCode"],
            ),
            "contentChecks": _content_checks(
                inventory["contentStatus"],
                inventory,
                error_code=inventory["errorCode"],
            ),
        }

    profiles: dict[str, dict[str, Any]] = inventory["confirmedProfiles"]
    structures: dict[str, dict[str, Any]] = inventory["structures"]
    note_type_ids = sorted(int(value) for value in profiles)
    cursor = content_cursor or 0
    try:
        expanded = expand_deck_ids(col, deck_ids) if deck_ids else None
        deck_sql, deck_params = _deck_filter(expanded)
        type_placeholders = ",".join("?" for _ in note_type_ids)
        note_rows = col.db.all(
            f"""
            select distinct n.id
            from notes n
            join cards c on c.nid = n.id
            where n.mid in ({type_placeholders})
              and n.id > ?
              {deck_sql}
            order by n.id asc
            limit ?
            """,
            *note_type_ids,
            cursor,
            *deck_params,
            CONTENT_SCAN_NOTE_LIMIT + 1,
        )
        note_ids = [_positive_int(row[0]) for row in note_rows if isinstance(row, (list, tuple)) and row]
        note_ids = [value for value in note_ids if value > 0]
        has_more = len(note_ids) > CONTENT_SCAN_NOTE_LIMIT
        selected_note_ids = note_ids[:CONTENT_SCAN_NOTE_LIMIT]
        if not selected_note_ids:
            status = "partial" if inventory["degraded"] else "empty"
            return {
                "reasons": [],
                "sourceStatus": content_source_status(
                    status,
                    scanned_note_count=0,
                    error_code=inventory["errorCode"],
                ),
                "profileSourceStatus": source_status(
                    "partial" if inventory["degraded"] else "empty",
                    error_code=inventory["errorCode"],
                ),
                "contentChecks": _content_checks(
                    "partial" if inventory["degraded"] else "available",
                    inventory,
                    error_code=inventory["errorCode"],
                ),
            }

        note_placeholders = ",".join("?" for _ in selected_note_ids)
        card_rows = col.db.all(
            f"""
            with sibling_counts as (
                select nid, count(*) as sibling_count
                from cards
                where nid in ({note_placeholders})
                group by nid
            )
            select
                c.id,
                c.nid,
                c.did,
                c.ord,
                n.mid,
                n.flds,
                coalesce(s.sibling_count, 1)
            from cards c
            join notes n on n.id = c.nid
            left join sibling_counts s on s.nid = c.nid
            where n.id in ({note_placeholders})
              {deck_sql}
            order by c.nid asc, c.id asc
            limit ?
            """,
            *selected_note_ids,
            *selected_note_ids,
            *deck_params,
            CONTENT_CARD_FETCH_LIMIT + 1,
        )
    except Exception:
        return {
            "reasons": [],
            "sourceStatus": content_source_status("error", error_code="content_candidate_failed"),
            "profileSourceStatus": source_status("error", error_code="content_candidate_failed"),
            "contentChecks": _content_checks(
                "unavailable",
                inventory,
                error_code="content_candidate_failed",
            ),
        }

    card_overflow = len(card_rows) > CONTENT_CARD_FETCH_LIMIT
    grouped: dict[int, list[dict[str, Any]]] = {}
    malformed = 0
    for row in card_rows[:CONTENT_CARD_FETCH_LIMIT]:
        candidate = _content_candidate(row)
        if candidate is None:
            malformed += 1
            continue
        grouped.setdefault(candidate["noteId"], []).append(candidate)

    reasons: list[dict[str, Any]] = []
    evaluated = 0
    skipped = malformed
    revision = max(0, _non_negative_int(store_snapshot.get("revision")))
    for note_id in selected_note_ids:
        note_candidates = grouped.get(note_id, [])
        if not note_candidates:
            skipped += 1
            continue
        profile = profiles.get(str(note_candidates[0]["noteTypeId"]))
        structure = structures.get(str(note_candidates[0]["noteTypeId"]))
        if profile is None or structure is None:
            skipped += 1
            continue
        ordinals = profile["appliesTo"]["templateOrdinals"]
        applicable = [
            item for item in note_candidates
            if not ordinals or item["templateOrdinal"] in ordinals
        ]
        if not applicable:
            continue
        representative = min(applicable, key=lambda item: item["cardId"])
        evaluated += 1
        for failure in evaluate_inspection_profile(
            profile,
            structure,
            representative,
            profile_revision=revision,
        ):
            reasons.append({
                "cardId": representative["cardId"],
                "noteId": note_id,
                "reason": content_reason_from_failure(failure),
            })

    next_cursor = str(selected_note_ids[-1]) if has_more else None
    degraded = inventory["degraded"] or skipped > 0 or has_more or card_overflow
    content_state = "partial" if degraded else "available"
    profile_state = "partial" if degraded else ("available" if evaluated else "empty")
    error_code = (
        "content_card_fetch_truncated" if card_overflow
        else "content_rows_skipped" if skipped
        else inventory["errorCode"]
    )
    return {
        "reasons": reasons,
        "sourceStatus": content_source_status(
            content_state,
            item_count=len(reasons),
            skipped_count=skipped,
            truncated=has_more,
            error_code=error_code,
            scanned_note_count=len(selected_note_ids),
            next_cursor=next_cursor,
        ),
        "profileSourceStatus": source_status(
            profile_state,
            item_count=len(reasons),
            skipped_count=skipped,
            truncated=has_more,
            error_code=error_code,
        ),
        "contentChecks": _content_checks(
            "partial" if degraded else "available",
            inventory,
            scanned_note_count=len(selected_note_ids),
            evaluated_note_count=evaluated,
            failed_check_count=len(reasons),
            skipped_count=skipped,
            truncated=has_more,
            next_cursor=next_cursor,
            error_code=error_code,
        ),
    }


def source_status(
    status: str,
    *,
    item_count: int = 0,
    skipped_count: int = 0,
    truncated: bool = False,
    error_code: str | None = None,
) -> dict[str, Any]:
    allowed = {"available", "empty", "partial", "unavailable", "error", "not_applicable"}
    return {
        "status": status if status in allowed else "error",
        "itemCount": max(0, int(item_count)),
        "skippedCount": max(0, int(skipped_count)),
        "truncated": bool(truncated),
        "errorCode": str(error_code)[:80] if error_code else None,
    }


def content_source_status(
    status: str,
    *,
    item_count: int = 0,
    skipped_count: int = 0,
    truncated: bool = False,
    error_code: str | None = None,
    scanned_note_count: int = 0,
    next_cursor: str | None = None,
) -> dict[str, Any]:
    value = source_status(
        status,
        item_count=item_count,
        skipped_count=skipped_count,
        truncated=truncated,
        error_code=error_code,
    )
    value["scannedNoteCount"] = max(0, int(scanned_note_count))
    value["nextCursor"] = next_cursor if truncated else None
    return value


def _authoritative_profile_inventory(col: Any, snapshot: dict[str, Any]) -> dict[str, Any]:
    base = {
        "confirmedProfileCount": 0,
        "needsReviewProfileCount": 0,
        "disabledProfileCount": 0,
        "suggestedProfileCount": 0,
        "confirmedProfiles": {},
        "structures": {},
        "degraded": False,
        "errorCode": None,
        "sourceState": "empty",
        "profileState": "empty",
        "contentStatus": "no_confirmed_profiles",
        "terminal": True,
    }
    status = str(snapshot.get("status") or "unavailable")
    if status in {"future_schema", "unavailable", "corrupt"}:
        base.update({
            "sourceState": "error" if status == "corrupt" else "unavailable",
            "profileState": "error" if status == "corrupt" else "unavailable",
            "contentStatus": "unavailable",
            "errorCode": str(snapshot.get("errorCode") or "profile_store_unavailable"),
        })
        return base
    if col is None or getattr(col, "db", None) is None:
        base.update({
            "sourceState": "unavailable",
            "profileState": "unavailable",
            "contentStatus": "unavailable",
            "errorCode": "collection_unavailable",
        })
        return base

    profiles = [item for item in snapshot.get("profiles", []) if isinstance(item, dict)]
    model_ids = {int(item["noteTypeId"]) for item in profiles if str(item.get("noteTypeId", "")).isdigit()}
    catalog = read_note_type_structures(col, model_ids, limit=MAX_PROFILES)
    structures = {str(item["noteTypeId"]): item for item in catalog.get("items", []) if isinstance(item, dict)}
    lifecycle = [
        effective_profile_state(profile, structures.get(str(profile.get("noteTypeId"))))
        for profile in profiles
    ]
    confirmed = {
        str(profile["noteTypeId"]): profile
        for profile, state in zip(profiles, lifecycle)
        if state["state"] == "confirmed" and state["authoritative"] and profile.get("checks")
    }
    needs = sum(state["state"] == "needs_review" for state in lifecycle)
    disabled = sum(state["state"] == "disabled" for state in lifecycle)
    suggested = sum(state["state"] == "suggested" for state in lifecycle)
    base.update({
        "confirmedProfileCount": len(confirmed),
        "needsReviewProfileCount": needs,
        "disabledProfileCount": disabled,
        "suggestedProfileCount": suggested,
        "confirmedProfiles": confirmed,
        "structures": structures,
        "degraded": needs > 0 or catalog.get("status") == "partial",
        "errorCode": "profile_structures_partial" if catalog.get("status") == "partial" else None,
    })
    if not confirmed:
        base["contentStatus"] = (
            "profiles_need_review" if needs
            else "disabled" if profiles and disabled == len(profiles)
            else "no_confirmed_profiles"
        )
        base["errorCode"] = "no_confirmed_profiles"
        return base
    base.update({
        "sourceState": "partial" if base["degraded"] else "available",
        "profileState": "partial" if base["degraded"] else "available",
        "contentStatus": "partial" if base["degraded"] else "available",
        "terminal": False,
    })
    return base


def _content_checks(
    status: str,
    inventory: dict[str, Any],
    *,
    scanned_note_count: int = 0,
    evaluated_note_count: int = 0,
    failed_check_count: int = 0,
    skipped_count: int = 0,
    truncated: bool = False,
    next_cursor: str | None = None,
    error_code: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "confirmedProfileCount": inventory["confirmedProfileCount"],
        "needsReviewProfileCount": inventory["needsReviewProfileCount"],
        "disabledProfileCount": inventory["disabledProfileCount"],
        "suggestedProfileCount": inventory["suggestedProfileCount"],
        "scannedNoteCount": max(0, int(scanned_note_count)),
        "evaluatedNoteCount": max(0, int(evaluated_note_count)),
        "failedCheckCount": max(0, int(failed_check_count)),
        "skippedCount": max(0, int(skipped_count)),
        "truncated": bool(truncated),
        "nextCursor": next_cursor if truncated else None,
        "errorCode": str(error_code)[:80] if error_code else None,
    }


def _learning_payload(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, (list, tuple)) or len(row) < 10:
        return None
    card_id, note_id, lapses, note_type_id, template_ordinal, tags, reviews, again, total_ms, last_ms = row[:10]
    card_id = _positive_int(card_id)
    note_id = _positive_int(note_id)
    if not card_id or not note_id:
        return None
    reviews = _non_negative_int(reviews)
    again = _non_negative_int(again)
    lapses = _non_negative_int(lapses)
    average_seconds = round((_non_negative_int(total_ms) / 1000) / reviews, 3) if reviews else 0.0
    pass_rate = round(max(0.0, (reviews - again) / reviews), 4) if reviews else 0.0
    tag_set = {value.casefold() for value in str(tags or "").split()}
    issues: list[str] = []
    if "leech" in tag_set or lapses >= ATTENTION_CARD_LEECH_LAPSE_THRESHOLD:
        issues.append("leech")
    if again >= ATTENTION_CARD_REPEATED_AGAIN_MIN:
        issues.append("repeated_again")
    if reviews >= ATTENTION_CARD_LOW_PASS_MIN_REVIEWS and pass_rate < ATTENTION_CARD_LOW_PASS_RATE:
        issues.append("low_pass_rate")
    if average_seconds > ATTENTION_CARD_SLOW_SECONDS:
        issues.append("slow_answer")
    return {
        "cardId": card_id,
        "noteId": note_id,
        "noteTypeId": _positive_int(note_type_id),
        "cardTemplateName": "",
        "issues": issues,
        "againCount": again,
        "lapses": lapses,
        "averageAnswerSeconds": average_seconds,
        "passRate": pass_rate,
        "lastReviewedAt": _iso_ms(last_ms),
    }


def _content_candidate(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, (list, tuple)) or len(row) < 7:
        return None
    card_id, note_id, _deck_id, ordinal, note_type_id, raw_fields, sibling_count = row[:7]
    card_id = _positive_int(card_id)
    note_id = _positive_int(note_id)
    note_type_id = _positive_int(note_type_id)
    ordinal = _non_negative_int(ordinal)
    if not card_id or not note_id or not note_type_id or ordinal > CONTENT_MAX_TEMPLATE_ORDINAL:
        return None
    return {
        "cardId": card_id,
        "noteId": note_id,
        "noteTypeId": note_type_id,
        "templateOrdinal": ordinal,
        "rawFields": str(raw_fields or ""),
        "siblingCount": max(1, _non_negative_int(sibling_count)),
    }


def _deck_filter(deck_ids: list[int] | None) -> tuple[str, list[int]]:
    if not deck_ids:
        return "", []
    normalized = [value for value in dict.fromkeys(_positive_int(value) for value in deck_ids) if value > 0]
    if not normalized:
        return "", []
    placeholders = ",".join("?" for _ in normalized)
    return f"and (case when c.odid > 0 then c.odid else c.did end) in ({placeholders})", normalized


def _iso_ms(value: Any) -> str | None:
    parsed = _positive_int(value)
    if not parsed:
        return None
    try:
        return datetime.fromtimestamp(parsed / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def _positive_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return result if 0 < result <= MAX_SIGNED_ID else 0


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, result)
