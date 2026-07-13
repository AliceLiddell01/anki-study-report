"""Read-only FSRS analytics built on Anki 26.05 collection/backend surfaces.

Public responses contain aggregates only. The adapter never exposes searches,
parameter vectors, card IDs, revlog rows, paths, or mutating commands.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json
import math
from statistics import median
from typing import Any, Iterable


FSRS_SCHEMA_VERSION = 1
CALCULATION_VERSION = "fsrs-analytics-v1.0"
OPERATIONS = {"overview", "memory", "calibration", "steps", "simulate"}
SCOPE_KINDS = {"dashboard", "all_collection", "configuration", "deck"}
PERIODS = {"30d": 30, "90d": 90, "180d": 180, "1y": 365}
HORIZONS = {90, 180, 365}
MAX_RESPONSE_BYTES = {"overview": 100_000, "memory": 200_000, "calibration": 150_000, "steps": 150_000, "simulate": 300_000}
RETRIEVABILITY_BUCKETS = ((0.0, 0.7, "<70%"), (0.7, 0.8, "70–80%"), (0.8, 0.9, "80–90%"), (0.9, 0.95, "90–95%"), (0.95, 1.000001, ">95%"))
STABILITY_BUCKETS = ((0, 1, "До 1 дня"), (1, 7, "1–7 дней"), (7, 28, "1–4 недели"), (28, 90, "1–3 месяца"), (90, 365, "3–12 месяцев"), (365, 1095, "1–3 года"), (1095, math.inf, "Более 3 лет"))
DIFFICULTY_BUCKETS = ((1, 3, "1–3"), (3, 5, "3–5"), (5, 7, "5–7"), (7, 9, "7–9"), (9, 10.0001, "9–10"))


class FsrsValidationError(ValueError):
    def __init__(self, field_errors: dict[str, str]) -> None:
        super().__init__("Invalid FSRS query.")
        self.field_errors = field_errors


def compact_json_size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def parameter_fingerprint(params: Iterable[object]) -> str:
    normalized = [round(float(value), 7) for value in params]
    body = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("ascii")).hexdigest()[:16]


def discover_configuration_groups(col: Any) -> list[dict[str, Any]]:
    try:
        raw_decks = col.decks.all()
    except Exception:
        raw_decks = []
    groups: dict[tuple[int, str, str], dict[str, Any]] = {}
    for deck in raw_decks if isinstance(raw_decks, list) else []:
        if not isinstance(deck, dict) or deck.get("dyn"):
            continue
        deck_id = _int(deck.get("id"))
        if deck_id <= 0:
            continue
        config = _config_for_deck(col, deck_id, deck)
        preset_id = _int(config.get("id") or deck.get("conf") or 1)
        params, version = _params(config, col, deck_id)
        fingerprint = parameter_fingerprint(params) if params else "unavailable"
        learn = _steps(config, "new", "delays")
        relearn = _steps(config, "lapse", "delays")
        scheduler_fingerprint = hashlib.sha256(json.dumps({"learn": learn, "relearn": relearn, "max": _nested(config, "rev", "maxIvl")}, sort_keys=True).encode()).hexdigest()[:12]
        key = (preset_id, fingerprint, scheduler_fingerprint)
        target = _retention(deck.get("desiredRetention"), config.get("desiredRetention"))
        group = groups.setdefault(key, {
            "id": f"cfg-{preset_id}-{fingerprint}-{scheduler_fingerprint[:6]}",
            "presetId": preset_id,
            "presetName": str(config.get("name") or f"Набор {preset_id}"),
            "parameterFingerprint": fingerprint,
            "parameterVersion": version,
            "defaultDesiredRetention": _retention(None, config.get("desiredRetention")),
            "deckDesiredRetentionOverrides": [],
            "learningStepsSeconds": learn,
            "relearningStepsSeconds": relearn,
            "shortTermMode": "fsrs" if not learn and not relearn else "configured_steps",
            "deckIds": [],
            "deckNames": [],
            "cardCount": 0,
            "reviewedCardCount": 0,
            "qualifyingReviewCount": 0,
            "_params": params,
            "_config": config,
        })
        group["deckIds"].append(deck_id)
        group["deckNames"].append(str(deck.get("name") or f"Колода {deck_id}"))
        default_target = group["defaultDesiredRetention"]
        if target is not None and target != default_target:
            group["deckDesiredRetentionOverrides"].append({"deckId": deck_id, "desiredRetention": target})
    _fill_all_group_counts(col, list(groups.values()))
    for group in groups.values():
        group["deckIds"].sort()
        group["coverage"] = "available" if group["reviewedCardCount"] else "insufficient_data"
        group["dataSufficiency"] = _sufficiency(group["qualifyingReviewCount"], 100, 400)
    return sorted((group for group in groups.values() if group["cardCount"] > 0), key=lambda group: (group["presetName"].casefold(), group["id"]))


def public_group(group: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in group.items() if not key.startswith("_")}


def build_fsrs_capability(col: Any) -> dict[str, Any]:
    enabled = _enabled(col)
    groups = discover_configuration_groups(col) if enabled else []
    reviewed = sum(group["reviewedCardCount"] for group in groups)
    qualifying = sum(group["qualifyingReviewCount"] for group in groups)
    state = "disabled" if not enabled else "insufficient_data" if reviewed == 0 else "mixed_configuration" if len(groups) > 1 else "enabled"
    return {
        "schemaVersion": FSRS_SCHEMA_VERSION,
        "enabled": enabled,
        "availability": state,
        "configurationCount": len(groups),
        "reviewedCardCount": reviewed,
        "qualifyingReviewCount": qualifying,
        "mixedConfiguration": len(groups) > 1,
        "defaultConfigurationId": groups[0]["id"] if groups else None,
        "supportedFeatures": ["overview", "memory", "calibration", "steps", "simulator"] if enabled else [],
        "limitations": ["current_memory_snapshot", "compatible_configuration_required", "read_only"],
        "configurations": [public_group(group) for group in groups],
    }


def normalize_fsrs_request(raw: object, groups: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise FsrsValidationError({"query": "Expected a JSON object."})
    allowed = {"operation", "scope", "period", "simulation"}
    errors = {key: "Unexpected field." for key in raw if key not in allowed}
    operation = raw.get("operation")
    if operation not in OPERATIONS:
        errors["operation"] = "Unsupported operation."
    scope_raw = raw.get("scope", {"kind": "all_collection"})
    scope = _normalize_scope(scope_raw, groups, errors)
    period = raw.get("period", "90d")
    if period not in PERIODS:
        errors["period"] = "Unsupported period."
    simulation = None
    if operation == "simulate":
        simulation = _normalize_simulation(raw.get("simulation"), errors)
    elif "simulation" in raw:
        errors["simulation"] = "Only valid for simulate."
    if operation in {"calibration", "simulate"} and scope.get("kind") in {"dashboard", "all_collection"} and len(_scope_groups(scope, groups)) != 1:
        errors["scope"] = "Select one compatible configuration."
    selected = _scope_groups(scope, groups)
    if operation == "simulate" and selected:
        targets = {selected[0]["defaultDesiredRetention"], *[item["desiredRetention"] for item in selected[0]["deckDesiredRetentionOverrides"]]}
        if len({target for target in targets if target is not None}) > 1 and scope.get("kind") != "deck":
            errors["scope"] = "Select one deck when desired retention differs inside the preset."
        if not selected[0].get("_params"):
            errors["scope"] = "Native FSRS parameters are unavailable."
    if errors:
        raise FsrsValidationError(errors)
    return {"operation": operation, "scope": scope, "period": period, "simulation": simulation}


def execute_fsrs_query(col: Any, raw: object, *, dashboard_deck_ids: list[int] | None = None) -> dict[str, Any]:
    groups = discover_configuration_groups(col)
    query = normalize_fsrs_request(raw, groups)
    selected = _scope_groups(query["scope"], groups, dashboard_deck_ids)
    deck_ids = _scope_deck_ids(query["scope"], selected, dashboard_deck_ids)
    operation = query["operation"]
    if operation in {"overview", "memory"}:
        memory = build_memory_snapshot(col, selected, deck_ids)
        result = build_overview(col, selected, deck_ids, memory) if operation == "overview" else memory
    elif operation == "calibration":
        result = build_calibration(col, selected[0], query["period"])
    elif operation == "steps":
        if query["scope"]["kind"] == "deck":
            selected = [next(group for group in groups if query["scope"]["deckId"] in group["deckIds"])]
        result = build_steps(col, selected, query["period"])
    else:
        simulation_group = _simulation_group(col, selected[0], query["scope"])
        result = run_native_simulation(col, simulation_group, query["simulation"])
    response = {"schemaVersion": FSRS_SCHEMA_VERSION, "operation": operation, "query": query, "result": result, "calculationVersion": CALCULATION_VERSION}
    if compact_json_size(response) > MAX_RESPONSE_BYTES[operation]:
        raise RuntimeError("FSRS response exceeded its bounded contract.")
    return response


def build_memory_snapshot(col: Any, groups: list[dict[str, Any]], deck_ids: list[int]) -> dict[str, Any]:
    targets = {}
    for group in groups:
        overrides = {item["deckId"]: item["desiredRetention"] for item in group["deckDesiredRetentionOverrides"]}
        for deck_id in group["deckIds"]:
            targets[deck_id] = overrides.get(deck_id, group["defaultDesiredRetention"] or 0.9)
    rows = _memory_rows(col, deck_ids)
    recalls = [row["retrievability"] for row in rows]
    stabilities = [row["stability"] for row in rows]
    difficulties = [row["difficulty"] for row in rows if row["difficulty"] is not None]
    studied = len(rows)
    return {
        "availability": "available" if studied else "insufficient_data",
        "snapshotAt": datetime.now().isoformat(timespec="seconds"),
        "studiedCards": studied,
        "estimatedRemembered": round(sum(recalls), 1),
        "averageRetrievability": _mean(recalls),
        "medianRetrievability": _median(recalls),
        "medianStabilityDays": _median(stabilities),
        "stabilityQuartilesDays": _quartiles(stabilities),
        "medianDifficulty": _median(difficulties),
        "cardsBelowOwnTarget": sum(1 for row in rows if row["retrievability"] < targets.get(row["deckId"], 0.9)),
        "overdueCards": sum(1 for row in rows if row["overdue"]),
        "retrievabilityDistribution": _distribution(recalls, RETRIEVABILITY_BUCKETS),
        "stabilityDistribution": _distribution(stabilities, STABILITY_BUCKETS),
        "difficultyDistribution": _distribution(difficulties, DIFFICULTY_BUCKETS),
        "limitations": ["snapshot_not_history", "expected_not_guaranteed", "no_card_list"],
    }


def build_overview(col: Any, groups: list[dict[str, Any]], deck_ids: list[int], memory: dict[str, Any]) -> dict[str, Any]:
    targets = sorted({target for group in groups for target in ([group["defaultDesiredRetention"]] + [item["desiredRetention"] for item in group["deckDesiredRetentionOverrides"]]) if target is not None})
    actual, actual_sample = _actual_retention(col, deck_ids)
    return {
        "availability": memory["availability"],
        "configurations": [public_group(group) for group in groups],
        "mixedConfiguration": len(groups) > 1,
        "targetRetentionRange": {"min": min(targets), "max": max(targets)} if targets else None,
        "estimatedRemembered": memory["estimatedRemembered"],
        "studiedCards": memory["studiedCards"],
        "averageRetrievability": memory["averageRetrievability"],
        "medianStabilityDays": memory["medianStabilityDays"],
        "actualRetention": actual,
        "actualRetentionSample": actual_sample,
        "dataSufficiency": _sufficiency(actual_sample, 100, 400),
        "insight": "Пока недостаточно ответов для устойчивого сравнения." if actual is None else "Фактическое удержание рассчитано по последним 30 дням; сравнивайте его с диапазоном собственных целей.",
    }


def build_calibration(col: Any, group: dict[str, Any], period: str) -> dict[str, Any]:
    days = PERIODS[period]
    cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
    placeholders = ",".join("?" for _ in group["deckIds"])
    try:
        card_ids = col.db.list(f"select id from cards where reps>1 and (case when odid>0 then odid else did end) in ({placeholders}) order by id limit 2000", *group["deckIds"])
    except Exception:
        card_ids = []
    bins = [{"from": start, "to": end, "label": label, "predictedSum": 0.0, "success": 0, "sample": 0} for start, end, label in RETRIEVABILITY_BUCKETS]
    for card_id in card_ids:
        try:
            response = col._backend.card_stats(_int(card_id))
            entries = sorted(response.revlog, key=lambda entry: entry.time)
        except Exception:
            continue
        for previous, current in zip(entries, entries[1:]):
            if current.time < cutoff or current.button_chosen not in {1, 2, 3, 4} or not previous.HasField("memory_state"):
                continue
            stability = float(previous.memory_state.stability)
            if stability <= 0:
                continue
            elapsed = max(0.0, (float(current.time) - float(previous.time)) / 86_400)
            predicted = _retrievability(elapsed, stability, 0.5)
            for bucket, (start, end, _label) in zip(bins, RETRIEVABILITY_BUCKETS):
                if start <= predicted < end:
                    bucket["predictedSum"] += predicted
                    bucket["success"] += 0 if int(current.button_chosen) == 1 else 1
                    bucket["sample"] += 1
                    break
    public_bins = []
    for bucket in bins:
        sample = bucket.pop("sample")
        predicted_sum = bucket.pop("predictedSum")
        success = bucket.pop("success")
        predicted = round(predicted_sum / sample, 4) if sample else None
        actual = round(success / sample, 4) if sample else None
        public_bins.append({**bucket, "predicted": predicted, "actual": actual, "sampleSize": sample, "sufficiency": _sufficiency(sample, 30, 100)})
    total = sum(item["sampleSize"] for item in public_bins)
    rmse = math.sqrt(sum(item["sampleSize"] * (item["actual"] - item["predicted"]) ** 2 for item in public_bins if item["actual"] is not None) / total) if total else None
    return {"configuration": public_group(group), "period": period, "sampleSize": total, "sufficiency": _sufficiency(total, 100, 400), "idealLine": [{"predicted": 0.5, "actual": 0.5}, {"predicted": 1.0, "actual": 1.0}], "bins": public_bins, "rmseBins": round(rmse, 4) if rmse is not None else None, "hardIsRecall": True, "limitations": ["compatible_configuration_only", "sparse_bins_not_interpreted"]}


def build_steps(col: Any, groups: list[dict[str, Any]], period: str) -> dict[str, Any]:
    if len(groups) != 1:
        return {"availability": "mixed_configuration", "configurations": [public_group(group) for group in groups], "scenarios": [], "recommendation": None}
    group = groups[0]
    cutoff = int((datetime.now() - timedelta(days=PERIODS[period])).timestamp() * 1000)
    placeholders = ",".join("?" for _ in group["deckIds"])
    try:
        rows = col.db.all(f"""select r.cid,r.id,r.ease,r.type from revlog r join cards c on c.id=r.cid where (case when c.odid>0 then c.odid else c.did end) in ({placeholders}) and r.id>=? and r.ease between 1 and 4 order by r.cid,r.id limit 50000""", *group["deckIds"], cutoff)
    except Exception:
        rows = []
    by_card: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for cid, review_id, ease, kind in rows:
        by_card[_int(cid)].append((_int(review_id), _int(ease), _int(kind)))
    observations: dict[str, list[tuple[float, bool]]] = defaultdict(list)
    rating_name = {1: "first_again", 2: "first_hard", 3: "first_good"}
    for events in by_card.values():
        for index, current in enumerate(events[:-1]):
            following = events[index + 1]
            delay = max(0.0, (following[0] - current[0]) / 1000)
            recalled = following[1] != 1
            if index == 0 and current[1] in rating_name:
                observations[rating_name[current[1]]].append((delay, recalled))
            if current[1] == 1 and following[1] == 3 and index + 2 < len(events):
                third = events[index + 2]
                observations["again_then_good"].append(((third[0] - following[0]) / 1000, third[1] != 1))
            if current[1] == 3 and following[1] == 1 and index + 2 < len(events):
                third = events[index + 2]
                observations["good_then_again"].append(((third[0] - following[0]) / 1000, third[1] != 1))
            if current[2] == 2:
                observations["relearning"].append((delay, recalled))
    scenario_ids = ["first_again", "first_hard", "first_good", "again_then_good", "good_then_again", "relearning"]
    scenarios = []
    for scenario_id in scenario_ids:
        values = observations[scenario_id]
        successful = sorted(delay for delay, recalled in values if recalled)
        scenarios.append({"id": scenario_id, "sampleSize": len(values), "retention": round(sum(1 for _, recalled in values if recalled) / len(values), 4) if values else None, "medianDelaySeconds": _median([delay for delay, _ in values]), "observedSuccessfulRangeSeconds": _quartile_range(successful) if len(values) >= 100 else None, "sufficiency": _sufficiency(len(values), 30, 100)})
    key_samples = [item["sampleSize"] for item in scenarios if item["id"] in {"first_again", "first_good"}]
    sufficient = bool(key_samples and min(key_samples) >= 100)
    ranges = [item["observedSuccessfulRangeSeconds"] for item in scenarios if item["observedSuccessfulRangeSeconds"]]
    recommendation = {"kind": "observed_successful_range", "rangeSeconds": [min(item[0] for item in ranges), max(item[1] for item in ranges)], "confidence": "preliminary", "readOnly": True} if sufficient and ranges else None
    return {"availability": "available" if rows else "insufficient_data", "configuration": public_group(group), "period": period, "scopeExpandedToPreset": True, "learningStepsSeconds": group["learningStepsSeconds"], "relearningStepsSeconds": group["relearningStepsSeconds"], "shortTermMode": group["shortTermMode"], "scenarios": scenarios, "recommendation": recommendation, "limitations": ["observational_not_causal", "no_apply_action"]}


def run_native_simulation(col: Any, group: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        from anki.scheduler_pb2 import SimulateFsrsReviewRequest  # type: ignore
    except Exception as error:
        raise RuntimeError("Native Anki simulator is unavailable.") from error
    config = group["_config"]
    base = dict(
        params=group["_params"], deck_size=group["cardCount"] + inputs["additionalNewCards"],
        days_to_simulate=inputs["horizonDays"], new_limit=inputs["newCardsPerDay"], review_limit=inputs["maximumReviewsPerDay"],
        max_interval=_int(_nested(config, "rev", "maxIvl") or 36500), search=" OR ".join(f'deck:"{_escape_search_text(name)}"' for name in group["deckNames"]),
        new_cards_ignore_review_limit=bool(config.get("newCardsIgnoreReviewLimit", False)), historical_retention=float(config.get("historicalRetention") or 0.9),
        learning_step_count=len(group["learningStepsSeconds"]), relearning_step_count=len(group["relearningStepsSeconds"]),
    )
    def run(target: float) -> dict[str, Any]:
        response = col._backend.simulate_fsrs_review(SimulateFsrsReviewRequest(desired_retention=target, **base))
        reviews = list(response.daily_review_count)[: inputs["horizonDays"]]
        seconds = list(response.daily_time_cost)[: inputs["horizonDays"]]
        points = [{"day": index + 1, "reviews": _int(count), "minutes": round(float(seconds[index] if index < len(seconds) else 0) / 60, 2)} for index, count in enumerate(reviews)]
        limit = inputs["maximumReviewsPerDay"]
        return {"desiredRetention": target, "averageReviewsPerDay": round(sum(reviews) / len(reviews), 2) if reviews else 0, "averageMinutesPerDay": round(sum(item["minutes"] for item in points) / len(points), 2) if points else 0, "peakReviews": max(reviews, default=0), "backlog": sum(max(0, count - limit) for count in reviews), "daily": points}
    current_target = group["defaultDesiredRetention"] or 0.9
    current = run(current_target)
    hypothetical = run(inputs["desiredRetention"])
    return {"configuration": public_group(group), "current": current, "hypothetical": hypothetical, "delta": {"reviewsPerDay": round(hypothetical["averageReviewsPerDay"] - current["averageReviewsPerDay"], 2), "minutesPerDay": round(hypothetical["averageMinutesPerDay"] - current["averageMinutesPerDay"], 2)}, "native": True, "readOnly": True, "limitations": ["simulation_is_estimate", "no_apply_action"]}


def _normalize_scope(raw: object, groups: list[dict[str, Any]], errors: dict[str, str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        errors["scope"] = "Expected an object."
        return {"kind": "all_collection"}
    for key in raw:
        if key not in {"kind", "configurationId", "deckId"}:
            errors[f"scope.{key}"] = "Unexpected field."
    kind = raw.get("kind", "all_collection")
    if kind not in SCOPE_KINDS:
        errors["scope.kind"] = "Unsupported scope."
        return {"kind": "all_collection"}
    scope = {"kind": kind}
    if kind == "configuration":
        config_id = raw.get("configurationId")
        if not isinstance(config_id, str) or config_id not in {group["id"] for group in groups}:
            errors["scope.configurationId"] = "Configuration was not found."
        else:
            scope["configurationId"] = config_id
    elif kind == "deck":
        deck_id = _int(raw.get("deckId"))
        if deck_id <= 0 or not any(deck_id in group["deckIds"] for group in groups):
            errors["scope.deckId"] = "Normal deck was not found."
        else:
            scope["deckId"] = deck_id
    elif any(key in raw for key in ("configurationId", "deckId")):
        errors["scope"] = "IDs are only valid for a matching scope."
    return scope


def _normalize_simulation(raw: object, errors: dict[str, str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        errors["simulation"] = "Expected an object."
        return {}
    allowed = {"desiredRetention", "horizonDays", "additionalNewCards", "newCardsPerDay", "maximumReviewsPerDay"}
    for key in raw:
        if key not in allowed:
            errors[f"simulation.{key}"] = "Unexpected field."
    values = {
        "desiredRetention": _float(raw.get("desiredRetention")), "horizonDays": _int(raw.get("horizonDays")),
        "additionalNewCards": _int(raw.get("additionalNewCards")), "newCardsPerDay": _int(raw.get("newCardsPerDay")),
        "maximumReviewsPerDay": _int(raw.get("maximumReviewsPerDay")),
    }
    if values["desiredRetention"] is None or not 0.75 <= values["desiredRetention"] <= 0.99: errors["simulation.desiredRetention"] = "Expected 0.75–0.99."
    if values["horizonDays"] not in HORIZONS: errors["simulation.horizonDays"] = "Expected 90, 180 or 365."
    for key, maximum in (("additionalNewCards", 100000), ("newCardsPerDay", 1000), ("maximumReviewsPerDay", 10000)):
        if values[key] < 0 or values[key] > maximum or (key == "maximumReviewsPerDay" and values[key] == 0): errors[f"simulation.{key}"] = "Value is out of range."
    return values


def _scope_groups(scope: dict[str, Any], groups: list[dict[str, Any]], dashboard: list[int] | None = None) -> list[dict[str, Any]]:
    if scope["kind"] == "configuration": return [group for group in groups if group["id"] == scope["configurationId"]]
    if scope["kind"] == "deck": return [group for group in groups if scope["deckId"] in group["deckIds"]]
    if scope["kind"] == "dashboard" and dashboard is not None: return [group for group in groups if set(group["deckIds"]) & set(dashboard)]
    return groups


def _scope_deck_ids(scope: dict[str, Any], groups: list[dict[str, Any]], dashboard: list[int] | None) -> list[int]:
    if scope["kind"] == "deck": return [scope["deckId"]]
    if scope["kind"] == "dashboard" and dashboard is not None: return sorted(set(dashboard) & {deck for group in groups for deck in group["deckIds"]})
    return sorted({deck for group in groups for deck in group["deckIds"]})


def _simulation_group(col: Any, group: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    if scope.get("kind") != "deck":
        return group
    deck_id = scope["deckId"]
    cloned = dict(group)
    cloned["deckIds"] = [deck_id]
    cloned["deckNames"] = [name for current, name in zip(group["deckIds"], group["deckNames"]) if current == deck_id]
    overrides = {item["deckId"]: item["desiredRetention"] for item in group["deckDesiredRetentionOverrides"]}
    cloned["defaultDesiredRetention"] = overrides.get(deck_id, group["defaultDesiredRetention"])
    cloned["deckDesiredRetentionOverrides"] = []
    try:
        cloned["cardCount"] = _int(col.db.scalar("select count(*) from cards where case when odid>0 then odid else did end = ?", deck_id))
    except Exception:
        cloned["cardCount"] = 0
    return cloned


def _memory_rows(col: Any, deck_ids: list[int]) -> list[dict[str, Any]]:
    if not deck_ids: return []
    placeholders = ",".join("?" for _ in deck_ids)
    today = _int(getattr(getattr(col, "sched", None), "today", 0))
    try:
        rows = col.db.all(f"""select case when odid>0 then odid else did end,due,ivl,json_extract(data,'$.s'),json_extract(data,'$.d'),coalesce(json_extract(data,'$.decay'),0.5) from cards where queue not in (0,-1) and json_extract(data,'$.s') is not null and (case when odid>0 then odid else did end) in ({placeholders}) limit 200000""", *deck_ids)
    except Exception:
        rows = []
    result = []
    for deck_id, due, interval, stability, difficulty, decay in rows:
        stability = _float(stability)
        if stability is None or stability <= 0: continue
        elapsed = max(0, today - (_int(due) - _int(interval)))
        result.append({"deckId": _int(deck_id), "stability": stability, "difficulty": _float(difficulty), "retrievability": _retrievability(elapsed, stability, _float(decay) or 0.5), "overdue": _int(due) < today})
    return result


def _actual_retention(col: Any, deck_ids: list[int]) -> tuple[float | None, int]:
    if not deck_ids:
        return None, 0
    placeholders = ",".join("?" for _ in deck_ids)
    cutoff = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    try:
        passed, total = col.db.first(f"select sum(case when r.ease>1 then 1 else 0 end),count(*) from revlog r join cards c on c.id=r.cid where r.id>=? and r.ease between 1 and 4 and (case when c.odid>0 then c.odid else c.did end) in ({placeholders})", cutoff, *deck_ids)
    except Exception:
        return None, 0
    sample = _int(total)
    return (round(_int(passed) / sample, 4), sample) if sample else (None, 0)


def _fill_all_group_counts(col: Any, groups: list[dict[str, Any]]) -> None:
    deck_ids = sorted({deck_id for group in groups for deck_id in group["deckIds"]})
    if not deck_ids:
        return
    placeholders = ",".join("?" for _ in deck_ids)
    try:
        card_rows = col.db.all(f"select case when odid>0 then odid else did end,count(*),sum(case when reps>0 then 1 else 0 end) from cards where (case when odid>0 then odid else did end) in ({placeholders}) group by case when odid>0 then odid else did end", *deck_ids)
        review_rows = col.db.all(f"select case when c.odid>0 then c.odid else c.did end,count(*) from revlog r join cards c on c.id=r.cid where r.ease between 1 and 4 and (case when c.odid>0 then c.odid else c.did end) in ({placeholders}) group by case when c.odid>0 then c.odid else c.did end", *deck_ids)
    except Exception:
        card_rows, review_rows = [], []
    cards = {_int(deck_id): (_int(total), _int(reviewed)) for deck_id, total, reviewed in card_rows}
    reviews = {_int(deck_id): _int(total) for deck_id, total in review_rows}
    for group in groups:
        retained = [(deck_id, name) for deck_id, name in zip(group["deckIds"], group["deckNames"]) if cards.get(deck_id, (0, 0))[0] > 0]
        group["deckIds"] = [deck_id for deck_id, _name in retained]
        group["deckNames"] = [name for _deck_id, name in retained]
        group["cardCount"] = sum(cards.get(deck_id, (0, 0))[0] for deck_id in group["deckIds"])
        group["reviewedCardCount"] = sum(cards.get(deck_id, (0, 0))[1] for deck_id in group["deckIds"])
        group["qualifyingReviewCount"] = sum(reviews.get(deck_id, 0) for deck_id in group["deckIds"])


def _enabled(col: Any) -> bool:
    try: return bool(col.get_config("fsrs"))
    except Exception: return False


def _config_for_deck(col: Any, deck_id: int, deck: dict[str, Any]) -> dict[str, Any]:
    try:
        value = col.decks.config_dict_for_deck_id(deck_id)
        return value if isinstance(value, dict) else {}
    except Exception: return {}


def _params(config: dict[str, Any], col: Any | None = None, deck_id: int | None = None) -> tuple[list[float], str]:
    for key, version in (("fsrsParams6", "FSRS-6"), ("fsrsParams5", "FSRS-5"), ("fsrsWeights", "legacy")):
        value = config.get(key)
        if isinstance(value, list) and value: return [float(item) for item in value], version
    if col is not None and deck_id is not None:
        try:
            defaults = col.decks.get_deck_configs_for_update(deck_id).defaults.config
            params = list(defaults.fsrs_params_6)
            if params:
                return [float(item) for item in params], "FSRS-6-default"
        except Exception:
            pass
    return [], "unavailable"


def _steps(config: dict[str, Any], section: str, key: str) -> list[int]:
    value = _nested(config, section, key)
    if not isinstance(value, list): return []
    return [max(0, round(float(item) * 60)) for item in value if isinstance(item, (int, float))]


def _retention(override: object, default: object) -> float | None:
    candidate = _float(override)
    value = candidate if candidate is not None and candidate > 0 else _float(default)
    if value is None: return None
    if value > 1: value /= 100
    return round(value, 4) if 0 < value <= 1 else None


def _retrievability(elapsed: float, stability: float, decay: float) -> float:
    exponent = -abs(decay or 0.5)
    factor = 0.9 ** (1 / exponent) - 1
    return max(0.0, min(1.0, (1 + factor * max(elapsed, 0) / stability) ** exponent))


def _distribution(values: list[float], buckets: Iterable[tuple[float, float, str]]) -> list[dict[str, Any]]:
    total = len(values)
    return [{"label": label, "from": start, "to": None if math.isinf(end) else end, "count": count, "percentage": round(count / total, 4) if total else None} for start, end, label in buckets for count in [sum(1 for value in values if start <= value < end)]]


def _sufficiency(sample: int, preliminary: int, sufficient: int) -> str:
    return "insufficient" if sample < preliminary else "preliminary" if sample < sufficient else "sufficient"


def _mean(values: list[float]) -> float | None: return round(sum(values) / len(values), 4) if values else None
def _median(values: list[float]) -> float | None: return round(float(median(values)), 4) if values else None
def _quartiles(values: list[float]) -> dict[str, float] | None:
    if not values: return None
    ordered = sorted(values); return {"p25": round(ordered[(len(ordered)-1)//4], 4), "p75": round(ordered[(len(ordered)-1)*3//4], 4)}
def _quartile_range(values: list[float]) -> list[int] | None:
    q = _quartiles(values); return [round(q["p25"]), round(q["p75"])] if q else None
def _nested(data: dict[str, Any], key: str, child: str) -> Any:
    value = data.get(key); return value.get(child) if isinstance(value, dict) else None
def _escape_search_text(value: str) -> str: return value.replace("\\", "\\\\").replace('"', '\\"')
def _int(value: object) -> int:
    try: return int(value or 0)
    except (TypeError, ValueError): return 0
def _float(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
        return result if math.isfinite(result) else None
    except (TypeError, ValueError): return None
