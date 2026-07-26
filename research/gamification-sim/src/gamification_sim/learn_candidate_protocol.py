from __future__ import annotations

from typing import Any, Mapping

from .canonical_json import canonical_digest


def _variant_registry(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for candidate in protocol["candidate_registry"]:
        variants.append(
            {
                "candidate_or_reference_id": candidate["candidate_id"],
                "family_id": candidate["family_id"],
                "parameterization_id": candidate["parameterization_id"],
                "subject_strategy_id": candidate["subject_strategy_id"],
                "delay_policy_id": candidate["delay_policy_id"],
            }
        )
    for reference in protocol["reference"]["variants"]:
        variants.append(
            {
                "candidate_or_reference_id": reference["reference_variant_id"],
                "family_id": "REFERENCE",
                "parameterization_id": "P-NONE",
                "subject_strategy_id": reference["subject_strategy_id"],
                "delay_policy_id": "D-NONE",
            }
        )
    return variants


def generate_dry_units(protocol: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    units: list[dict[str, Any]] = []
    for variant in _variant_registry(protocol):
        for scenario in protocol["scenario_registry"]:
            for configuration in scenario["configuration_profiles"]:
                for arrangement in scenario["session_time_arrangements"]:
                    for replica in protocol["matrix_axes"]["replica"]:
                        identity = {
                            "protocol_version": protocol["identity"]["version"],
                            **variant,
                            "scenario_id": scenario["scenario_id"],
                            "configuration_profile_id": configuration,
                            "session_time_arrangement_id": arrangement,
                            "replica": replica,
                            "seed": None,
                        }
                        units.append({"unit_id": "U-" + canonical_digest(identity), **identity})
    return tuple(units)


def matrix_summary(protocol: Mapping[str, Any]) -> dict[str, Any]:
    units = generate_dry_units(protocol)
    return {
        "unit_count": len(units),
        "unique_unit_ids": len({unit["unit_id"] for unit in units}),
        "candidate_or_reference_ids": sorted({unit["candidate_or_reference_id"] for unit in units}),
        "subject_strategy_ids": sorted({unit["subject_strategy_id"] for unit in units}),
        "delay_policy_ids": sorted({unit["delay_policy_id"] for unit in units}),
        "scenario_ids": sorted({unit["scenario_id"] for unit in units}),
        "configuration_profile_ids": sorted({unit["configuration_profile_id"] for unit in units}),
        "session_time_arrangement_ids": sorted({unit["session_time_arrangement_id"] for unit in units}),
        "replicas": sorted({unit["replica"] for unit in units}),
        "seeds": sorted({unit["seed"] for unit in units}, key=lambda value: (value is not None, value)),
    }
