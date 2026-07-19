from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .canonical_json import canonical_digest
from .day_aggregation import aggregate_day
from .manifest import python_major_minor
from .models import (
    CompletionStatus,
    ConfidenceLevel,
    DueRelation,
    MemoryContext,
    Outcome,
    ReviewDayInput,
    ReviewEpisodeInput,
    Source,
    SupplementalInput,
    SupportEventInput,
    SupportKind,
    WorkloadSnapshot,
)
from .parameter_catalog import compose_parameter_candidates, parameter_candidate
from .parameters import RewardParameterSet
from .scenario_runner import run_corpus
from .scenario_schema import format_json_path
from .strict_json import load_strict_json
from .validation import close
from .workspace import ResearchWorkspace, resolve_research_workspace


PERSONA_VERSION = "review-persona-v0.1"
GENERATOR_VERSION = "independent-day-workload-v0.2"
EXPECTED_PERSONA_IDS = tuple(
    f"P{index:02d}_{name}"
    for index, name in enumerate(
        (
            "NEW_SMALL", "BEGINNER_REGULAR", "MATURE_CONSISTENT", "HIGH_VOLUME",
            "SMALL_MATURE_COLLECTION", "BACKLOG_RETURN", "IRREGULAR_SCHEDULE",
            "NO_FSRS", "LOW_CONFIDENCE_FSRS", "HIGH_RETENTION", "LOW_RETENTION",
            "MULTI_DEVICE", "HEAVY_LAPSE", "AUDIO_AND_LONG_PROMPTS",
            "FILTERED_EXAM_PREP", "ZERO_DUE",
        ),
        1,
    )
)


@dataclass(frozen=True, slots=True)
class Persona:
    persona_id: str
    version: str
    horizon_days: int
    due_minimum: int
    due_mode: int
    due_maximum: int
    outcome_weights: tuple[tuple[Outcome, float], ...]
    session_pattern: str
    fsrs_available: bool
    confidence: ConfidenceLevel
    retrievability: float
    backlog_probability: float
    filtered_probability: float
    preview_probability: float
    support_probability: float
    zero_due_probability: float
    duplicate_probability: float
    seed_policy: str
    digest: str


def default_persona_schema_path(
    workspace: ResearchWorkspace | Path | None = None,
) -> Path:
    return resolve_research_workspace(workspace).path(
        "schemas/review-persona-v0.1.schema.json"
    )


def _validator(
    workspace: ResearchWorkspace | Path | None = None,
) -> Draft202012Validator:
    schema = load_strict_json(default_persona_schema_path(workspace))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _load_persona(path: Path, validator: Draft202012Validator) -> Persona:
    if path.is_symlink():
        raise ValueError(f"{path}: symlink persona files are not allowed")
    payload = load_strict_json(path)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    )
    if errors:
        raise ValueError(
            "\n".join(
                f"{path}: {format_json_path(list(error.absolute_path))}: {error.message}"
                for error in errors
            )
        )
    due = payload["daily_due_distribution"]
    if not due["minimum"] <= due["mode"] <= due["maximum"]:
        raise ValueError(f"{path}: daily due distribution must satisfy minimum <= mode <= maximum")
    weights = payload["outcome_weights"]
    if not close(sum(weights.values()), 1.0):
        raise ValueError(f"{path}: outcome weights must sum to 1")
    fsrs = payload["fsrs_context"]
    if not fsrs["available"] and fsrs["confidence"] != "unavailable":
        raise ValueError(f"{path}: unavailable FSRS requires unavailable confidence")
    return Persona(
        persona_id=payload["persona_id"],
        version=payload["version"],
        horizon_days=payload["horizon_days"],
        due_minimum=due["minimum"],
        due_mode=due["mode"],
        due_maximum=due["maximum"],
        outcome_weights=tuple((Outcome(key), float(value)) for key, value in weights.items()),
        session_pattern=payload["session_pattern"],
        fsrs_available=fsrs["available"],
        confidence=ConfidenceLevel(fsrs["confidence"]),
        retrievability=float(fsrs["retrievability"]),
        backlog_probability=float(payload["backlog_probability"]),
        filtered_probability=float(payload["filtered_probability"]),
        preview_probability=float(payload["preview_probability"]),
        support_probability=float(payload["support_probability"]),
        zero_due_probability=float(payload["zero_due_probability"]),
        duplicate_probability=float(payload["duplicate_probability"]),
        seed_policy=payload["seed_policy"],
        digest=canonical_digest(payload),
    )


def load_personas(
    root: Path,
    *,
    workspace: ResearchWorkspace | Path | None = None,
) -> tuple[Persona, ...]:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or root.is_symlink():
        raise ValueError("persona root must be a non-symlink directory")
    resolved_workspace = resolve_research_workspace(workspace, anchors=(root,))
    validator = _validator(resolved_workspace)
    personas = tuple(_load_persona(path, validator) for path in sorted(root.glob("*.json")))
    ids = tuple(item.persona_id for item in personas)
    if len(ids) != len(set(ids)):
        raise ValueError("persona IDs must be unique")
    if tuple(sorted(ids)) != tuple(sorted(EXPECTED_PERSONA_IDS)):
        missing = sorted(set(EXPECTED_PERSONA_IDS) - set(ids))
        unexpected = sorted(set(ids) - set(EXPECTED_PERSONA_IDS))
        raise ValueError(f"persona catalog mismatch; missing={missing}; unexpected={unexpected}")
    return tuple(sorted(personas, key=lambda item: item.persona_id))


def resolve_parameter_set(parameter_set_id: str) -> tuple[str, RewardParameterSet]:
    parts = tuple(parameter_candidate(identifier) for identifier in parameter_set_id.split("+"))
    candidate = parts[0] if len(parts) == 1 else compose_parameter_candidates(parts)
    return candidate.parameter_set_id, candidate.parameters


def derive_persona_seed(master_seed: int, persona_id: str, replica: int) -> int:
    material = f"{master_seed}:{persona_id}:{replica}:sha256-master-persona-replica-v1"
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def _sessions(pattern: str, due: int, rng: random.Random) -> tuple[str, ...]:
    if pattern == "single" or due <= 1:
        return ("session-1",)
    if pattern == "split":
        return ("session-1", "session-2")
    return tuple(f"session-{index}" for index in range(1, rng.randint(1, 4) + 1))


def generate_day(
    persona: Persona,
    rng: random.Random,
    replica: int,
    day_index: int,
) -> tuple[ReviewDayInput, tuple[Outcome, ...]]:
    anki_day = (date(2026, 1, 1) + timedelta(days=day_index)).isoformat()
    due = round(rng.triangular(persona.due_minimum, persona.due_maximum, persona.due_mode))
    if rng.random() < persona.zero_due_probability:
        due = 0
    if due and rng.random() < persona.backlog_probability:
        due = min(500, due * 2)
    outcomes, weights = zip(*persona.outcome_weights)
    episodes: list[ReviewEpisodeInput] = []
    honest_outcomes: list[Outcome] = []
    support: list[SupportEventInput] = []
    for index in range(due):
        key = f"{persona.persona_id}-{replica}-{day_index}-{index}"
        outcome = rng.choices(outcomes, weights=weights, k=1)[0]
        filtered = rng.random() < persona.filtered_probability
        memory = MemoryContext()
        if persona.fsrs_available:
            jitter = rng.uniform(-0.05, 0.05)
            actual = min(1.0, max(0.0, persona.retrievability + jitter))
            memory = MemoryContext(
                retrievability_actual=actual,
                retrievability_natural_due=min(1.0, max(actual, persona.retrievability)),
                confidence=persona.confidence,
            )
        episode = ReviewEpisodeInput(
            source_event_key=key,
            card_lineage=f"lineage-{persona.persona_id}-{replica}-{day_index}-{index}",
            anki_day=anki_day,
            outcome=outcome,
            source=Source.FILTERED_RESCHEDULING if filtered else Source.NORMAL_QUEUE,
            due_relation=DueRelation.ON_TIME,
            memory=memory,
        )
        episodes.append(episode)
        honest_outcomes.append(outcome)
        if outcome is Outcome.AGAIN and rng.random() < persona.support_probability:
            support.append(SupportEventInput(f"support-{key}", key, SupportKind.FIRST_STEP))
        if rng.random() < persona.duplicate_probability:
            episodes.append(episode)
    if rng.random() < persona.preview_probability:
        episodes.append(
            ReviewEpisodeInput(
                source_event_key=f"preview-{persona.persona_id}-{replica}-{day_index}",
                card_lineage=f"preview-lineage-{persona.persona_id}-{replica}-{day_index}",
                anki_day=anki_day,
                outcome=Outcome.GOOD,
                source=Source.FILTERED_PREVIEW,
                preview_without_rescheduling=True,
            )
        )
    status = CompletionStatus.ZERO_DUE if due == 0 else CompletionStatus.PARTIAL
    if due and rng.random() < 0.10:
        status = CompletionStatus.SCOPE_CLEARED
    return (
        ReviewDayInput(
            anki_day=anki_day,
            episodes=tuple(episodes),
            support_events=tuple(support),
            workload=WorkloadSnapshot(
                status=status,
                natural_due_at_start=due,
                due_visible_under_limits=due,
            ),
            session_ids=_sessions(persona.session_pattern, due, rng),
        ),
        tuple(honest_outcomes),
    )


def _percentile(values: list[float], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _persona_metrics(
    persona: Persona,
    params: RewardParameterSet,
    master_seed: int,
    replicas: int,
    days: int,
) -> tuple[dict[str, Any], list[int]]:
    totals: list[float] = []
    additional: list[float] = []
    support_shares: list[float] = []
    supplemental_shares: list[float] = []
    baseline_awarded = 0.0
    baseline_expected = 0.0
    failures: set[str] = set()
    derived_seeds: list[int] = []
    history = hashlib.sha256()
    for replica in range(replicas):
        child_seed = derive_persona_seed(master_seed, persona.persona_id, replica)
        derived_seeds.append(child_seed)
        rng = random.Random(child_seed)
        for day_index in range(days):
            day, honest_outcomes = generate_day(persona, rng, replica, day_index)
            result = aggregate_day(day, params)
            totals.append(result.total)
            baseline_awarded += result.core_baseline
            baseline_expected += sum(
                params.attempt_credit + (params.outcome_credit if outcome.passed else 0.0)
                for outcome in honest_outcomes
            )
            if result.total:
                additional.append((result.volume_credit + result.completion_credit) / result.total)
                support_shares.append(result.capped_support / result.total)
                supplemental_shares.append(result.capped_supplemental / result.total)
            if result.total < 0:
                failures.add("NEGATIVE_TOTAL")
            if result.volume_credit > params.volume_cap + 1e-9:
                failures.add("VOLUME_CAP")
            if result.completion_credit > params.completion_cap + 1e-9:
                failures.add("COMPLETION_CAP")
            if not close(
                result.total,
                result.core_baseline + result.core_context + result.capped_support
                + result.capped_supplemental + result.volume_credit + result.completion_credit,
            ):
                failures.add("BREAKDOWN_SUM")
            history.update(
                f"{replica}:{day_index}:{len(honest_outcomes)}:{result.total:.17g}:{result.core_baseline:.17g}\n".encode()
            )
    preservation = 1.0 if baseline_expected == 0 else baseline_awarded / baseline_expected
    if not close(preservation, 1.0):
        failures.add("BASELINE_SUPPRESSION")
    return (
        {
            "persona_id": persona.persona_id,
            "count": len(totals),
            "mean": statistics.fmean(totals),
            "median": statistics.median(totals),
            "p05": _percentile(totals, 0.05),
            "p25": _percentile(totals, 0.25),
            "p75": _percentile(totals, 0.75),
            "p95": _percentile(totals, 0.95),
            "p99": _percentile(totals, 0.99),
            "min": min(totals),
            "max": max(totals),
            "standard_deviation": statistics.pstdev(totals),
            "mean_additional_bonus_share": statistics.fmean(additional) if additional else 0.0,
            "mean_support_share": statistics.fmean(support_shares) if support_shares else 0.0,
            "mean_supplemental_share": statistics.fmean(supplemental_shares) if supplemental_shares else 0.0,
            "baseline_preservation_ratio": preservation,
            "gate_failures": sorted(failures),
            "history_digest": history.hexdigest(),
        },
        derived_seeds,
    )


FAIRNESS_PAIRS = (
    ("small_vs_large_collection", "P05_SMALL_MATURE_COLLECTION", "P04_HIGH_VOLUME"),
    ("fsrs_vs_no_fsrs", "P03_MATURE_CONSISTENT", "P08_NO_FSRS"),
    ("high_vs_low_confidence", "P03_MATURE_CONSISTENT", "P09_LOW_CONFIDENCE_FSRS"),
    ("high_vs_low_retention", "P10_HIGH_RETENTION", "P11_LOW_RETENTION"),
    ("regular_vs_irregular_schedule", "P02_BEGINNER_REGULAR", "P07_IRREGULAR_SCHEDULE"),
    ("short_vs_high_volume", "P05_SMALL_MATURE_COLLECTION", "P04_HIGH_VOLUME"),
    ("backlog_return_vs_regular", "P06_BACKLOG_RETURN", "P02_BEGINNER_REGULAR"),
    ("long_prompts_vs_ordinary", "P14_AUDIO_AND_LONG_PROMPTS", "P02_BEGINNER_REGULAR"),
)


def _fairness(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {item["persona_id"]: item for item in metrics}
    comparisons = []
    for name, left_id, right_id in FAIRNESS_PAIRS:
        left = by_id[left_id]
        right = by_id[right_id]
        comparisons.append(
            {
                "comparison": name,
                "left_persona_id": left_id,
                "right_persona_id": right_id,
                "mean_reward_ratio": 0.0 if right["mean"] == 0 else left["mean"] / right["mean"],
                "left_baseline_preservation_ratio": left["baseline_preservation_ratio"],
                "right_baseline_preservation_ratio": right["baseline_preservation_ratio"],
                "baseline_suppression_hidden": (
                    left["baseline_preservation_ratio"] < 1.0
                    or right["baseline_preservation_ratio"] < 1.0
                ),
            }
        )
    return {"comparisons": comparisons, "all_honest_baselines_preserved": not any(item["baseline_suppression_hidden"] for item in comparisons)}


def _abuse(package_root: Path, params: RewardParameterSet) -> dict[str, Any]:
    result = run_corpus(package_root / "scenarios", command="run-population-abuse", params=params)
    by_id = {item.scenario_id: dict(item.metrics) for item in result.scenario_results}
    pairs = {
        "duplicate_replay": ("duplicate-replay", "duplicate-replay-control"),
        "relearning_loop": ("relearning-loop", "relearning-loop-control"),
        "preview_farm": ("preview-only-farming", "preview-farming-control"),
        "forced_due": ("forced-due-farming", "forced-due-control"),
        "intentional_backlog": ("intentional-backlog", "timely-backlog-control"),
        "wait_farm": ("suspicious-time-bonus-suppression", "normal-time-control"),
    }
    comparisons = []
    for name, (exploit_id, control_id) in pairs.items():
        exploit = by_id[exploit_id]["total_review_units"]
        control = by_id[control_id]["total_review_units"]
        comparisons.append(
            {
                "exploit": name,
                "status": "supported",
                "scenario_id": exploit_id,
                "control_scenario_id": control_id,
                "incremental_reward": exploit - control,
                "gain_ratio": None if control == 0 else exploit / control,
            }
        )
    for name, reason in (
        ("multi_session_reset", "session boundaries are analytical and covered by invariance"),
        ("early_review_farm", "matched forced-due control is the expressible proxy"),
        ("retention_high_cycle", "requires the FSRS reference trajectory contract"),
        ("retention_low_cycle", "requires the FSRS reference trajectory contract"),
        ("button_gaming", "button neutrality is a hard invariant, not a population trajectory"),
        ("fast_macro_burst", "response time is not an input in the deterministic core"),
        ("micro_scope_completion", "covered by deterministic completion scenarios, not persona generation"),
        ("review_limit_manipulation", "covered by configured-limit deterministic scenario"),
        ("sync_replay", "source replay uses the duplicate idempotency contract"),
    ):
        comparisons.append({"exploit": name, "status": "deferred", "reason": reason})
    return {"corpus_digest": result.manifest.output_digest, "comparisons": comparisons}


def run_population(
    personas: tuple[Persona, ...],
    package_root: Path,
    *,
    mode: str,
    parameter_set_id: str,
    master_seed: int,
    smoke: bool = False,
) -> dict[str, Any]:
    if type(master_seed) is not int or master_seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if mode not in {"development", "standard", "long"}:
        raise ValueError("mode must be development, standard, or long")
    if smoke and mode != "long":
        raise ValueError("--smoke is only valid with long mode")
    parameter_set_id, params = resolve_parameter_set(parameter_set_id)
    if mode == "development":
        replicas, days = 1, 30
    elif mode == "standard":
        replicas, days = 100, 365
    else:
        replicas, days = (1, 7) if smoke else (188, 365)
    persona_set_digest = canonical_digest(
        [{"persona_id": item.persona_id, "digest": item.digest} for item in personas]
    )
    metrics = []
    derived_seed_manifest: dict[str, list[int]] = {}
    for persona in personas:
        persona_days = min(days, persona.horizon_days)
        item, seeds = _persona_metrics(persona, params, master_seed, replicas, persona_days)
        metrics.append(item)
        derived_seed_manifest[persona.persona_id] = seeds
    payload = {
        "manifest": {
            "generator_version": GENERATOR_VERSION,
            "persona_version": PERSONA_VERSION,
            "mode": mode,
            "smoke": smoke,
            "master_seed": master_seed,
            "derived_persona_seeds": derived_seed_manifest,
            "python_version": python_major_minor(),
            "parameter_set_id": parameter_set_id,
            "persona_set_digest": persona_set_digest,
            "persona_count": len(personas),
            "persona_days": sum(item["count"] for item in metrics),
        },
        "persona_metrics": metrics,
        "fairness": _fairness(metrics),
        "abuse": _abuse(package_root, params),
        "progression_projection": {
            "status": "indicative-only",
            "candidate_global_xp_per_review_unit": [0.5, 1.0, 2.0],
            "mean_review_units_per_day": statistics.fmean(item["mean"] for item in metrics),
        },
    }
    payload["manifest"]["output_digest"] = canonical_digest(payload)
    return payload


def render_population_summary(payload: dict[str, Any]) -> str:
    manifest = payload["manifest"]
    lines = [
        "# Independent-day workload stress simulation",
        "",
        f"- Mode: `{manifest['mode']}`",
        f"- Persona-days: **{manifest['persona_days']}**",
        f"- Parameter set: `{manifest['parameter_set_id']}`",
        f"- Master seed: `{manifest['master_seed']}`",
        f"- Digest: `{manifest['output_digest']}`",
        "",
        "## Personas",
        "",
        "| Persona | Days | Mean RU | p95 RU | Baseline | Gate failures |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in payload["persona_metrics"]:
        failures = ", ".join(item["gate_failures"]) or "none"
        lines.append(
            f"| `{item['persona_id']}` | {item['count']} | {item['mean']:.6g} | "
            f"{item['p95']:.6g} | {item['baseline_preservation_ratio']:.6g} | {failures} |"
        )
    lines.extend([
        "",
        "## Scope",
        "",
        "Independent synthetic days only; this report is workload/cap stress evidence, not a longitudinal card history. No real review history, card text, deck name, or personal data.",
    ])
    return "\n".join(lines) + "\n"


def _metrics_csv(payload: dict[str, Any]) -> str:
    keys = [key for key in payload["persona_metrics"][0] if key not in {"gate_failures", "history_digest"}]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=[*keys, "gate_failures", "history_digest"], lineterminator="\n")
    writer.writeheader()
    for item in payload["persona_metrics"]:
        row = dict(item)
        row["gate_failures"] = ";".join(row["gate_failures"])
        writer.writerow(row)
    return stream.getvalue()


def write_population_reports(payload: dict[str, Any], output_root: Path) -> Path:
    if output_root.exists() and output_root.is_symlink():
        raise ValueError("population output root must not be a symlink")
    run_dir = output_root.resolve() / "population" / payload["manifest"]["output_digest"][:12]
    run_dir.mkdir(parents=True, exist_ok=True)
    if run_dir.is_symlink():
        raise ValueError("population run directory must not be a symlink")
    (run_dir / "charts").mkdir(exist_ok=True)
    for name, value in (
        ("manifest.json", payload["manifest"]),
        ("fairness.json", payload["fairness"]),
        ("abuse.json", payload["abuse"]),
    ):
        (run_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (run_dir / "persona-metrics.csv").write_text(_metrics_csv(payload), encoding="utf-8")
    (run_dir / "summary.md").write_text(render_population_summary(payload), encoding="utf-8")
    return run_dir
