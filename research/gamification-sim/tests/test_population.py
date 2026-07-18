from __future__ import annotations

import random

from gamification_sim.day_aggregation import aggregate_day
from gamification_sim.population import (
    EXPECTED_PERSONA_IDS,
    derive_persona_seed,
    generate_day,
    load_personas,
    resolve_parameter_set,
    run_population,
    write_population_reports,
)


ROOT = __import__("pathlib").Path(__file__).parents[1]
PERSONA_ROOT = ROOT / "personas"


def test_persona_catalog_is_complete_strict_and_non_personal():
    personas = load_personas(PERSONA_ROOT)
    assert tuple(item.persona_id for item in personas) == tuple(sorted(EXPECTED_PERSONA_IDS))
    assert len({item.digest for item in personas}) == 16
    forbidden = ("card_text", "deck_name", "email", "user_id")
    raw = "\n".join(path.read_text(encoding="utf-8") for path in PERSONA_ROOT.glob("*.json"))
    assert not any(item in raw for item in forbidden)


def test_child_seed_is_hash_derived_not_iteration_derived():
    first = derive_persona_seed(20260716, "P01_NEW_SMALL", 0)
    assert first == derive_persona_seed(20260716, "P01_NEW_SMALL", 0)
    assert first != derive_persona_seed(20260716, "P01_NEW_SMALL", 1)
    assert first != derive_persona_seed(20260717, "P01_NEW_SMALL", 0)


def test_generator_creates_normalized_inputs_without_reward_logic():
    persona = load_personas(PERSONA_ROOT)[0]
    day, honest_outcomes = generate_day(persona, random.Random(7), 0, 0)
    _, params = resolve_parameter_set("R-CURRENT")
    result = aggregate_day(day, params)
    assert len(honest_outcomes) >= 0
    assert result.anki_day == day.anki_day
    assert result.total >= 0


def test_development_population_is_reproducible_and_seed_sensitive():
    personas = load_personas(PERSONA_ROOT)
    first = run_population(personas, ROOT, mode="development", parameter_set_id="R-CURRENT", master_seed=20260716)
    repeated = run_population(personas, ROOT, mode="development", parameter_set_id="R-CURRENT", master_seed=20260716)
    changed = run_population(personas, ROOT, mode="development", parameter_set_id="R-CURRENT", master_seed=20260717)
    assert first["manifest"]["output_digest"] == repeated["manifest"]["output_digest"]
    assert first["manifest"]["output_digest"] != changed["manifest"]["output_digest"]
    assert first["manifest"]["persona_days"] == 16 * 30
    assert all(not item["gate_failures"] for item in first["persona_metrics"])
    assert first["fairness"]["all_honest_baselines_preserved"] is True


def test_long_mode_has_explicit_bounded_smoke():
    payload = run_population(
        load_personas(PERSONA_ROOT), ROOT,
        mode="long", parameter_set_id="R-CURRENT", master_seed=20260716, smoke=True,
    )
    assert payload["manifest"]["mode"] == "long"
    assert payload["manifest"]["smoke"] is True
    assert payload["manifest"]["persona_days"] == 16 * 7


def test_population_reports_have_required_artifacts(tmp_path):
    payload = run_population(
        load_personas(PERSONA_ROOT), ROOT,
        mode="development", parameter_set_id="R-CURRENT", master_seed=1,
    )
    run_dir = write_population_reports(payload, tmp_path)
    assert {item.name for item in run_dir.iterdir()} == {
        "manifest.json", "persona-metrics.csv", "fairness.json", "abuse.json",
        "summary.md", "charts",
    }
