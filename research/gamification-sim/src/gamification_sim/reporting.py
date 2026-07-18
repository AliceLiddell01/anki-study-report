from __future__ import annotations

import json
from pathlib import Path

from .breakdown import to_dict
from .scenario_models import CorpusRunResult
from .scenario_models import AssertionStatus


def report_payload(result: CorpusRunResult) -> dict:
    payload = to_dict(result)
    passed = sum(item.passed for item in result.scenario_results)
    failures = [
        {
            "scenario_id": scenario.scenario_id,
            "detail": assertion.detail,
        }
        for scenario in result.scenario_results
        for assertion in scenario.assertions
        if assertion.status is AssertionStatus.FAILED
    ]
    payload["corpus_summary"] = {
        "scenario_count": len(result.scenario_results),
        "passed": passed,
        "failed": len(result.scenario_results) - passed,
        "assertions": {
            status.value: sum(
                assertion.status is status
                for scenario in result.scenario_results
                for assertion in scenario.assertions
            )
            for status in AssertionStatus
        },
    }
    payload["failures"] = failures
    return payload


def render_json_report(result: CorpusRunResult) -> str:
    return json.dumps(
        report_payload(result),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def render_markdown_report(result: CorpusRunResult) -> str:
    passed = sum(item.passed for item in result.scenario_results)
    failed = len(result.scenario_results) - passed
    lines = [
        "# Deterministic Review Scenario Report",
        "",
        f"- Simulator: `{result.manifest.simulator_version}`",
        f"- Rule version: `{result.manifest.rule_version}`",
        f"- Scenario schema: `{result.manifest.scenario_schema_version}`",
        f"- Python: `{result.manifest.python_version}`",
        f"- Scenarios: **{len(result.scenario_results)}**",
        f"- Passed: **{passed}**",
        f"- Failed: **{failed}**",
        f"- Assertions passed: **{sum(a.status is AssertionStatus.PASSED for s in result.scenario_results for a in s.assertions)}**",
        f"- Assertions failed: **{sum(a.status is AssertionStatus.FAILED for s in result.scenario_results for a in s.assertions)}**",
        f"- Assertions not applicable: **{sum(a.status is AssertionStatus.NOT_APPLICABLE for s in result.scenario_results for a in s.assertions)}**",
        f"- Input digest: `{result.manifest.input_digest}`",
        f"- Output digest: `{result.manifest.output_digest}`",
        "",
        "## Scenario results",
        "",
        "| Scenario | Category | Days | Total RU | Assertions |",
        "|---|---|---:|---:|---|",
    ]
    for scenario in result.scenario_results:
        metrics = dict(scenario.metrics)
        status = "PASS" if scenario.passed else "FAIL"
        lines.append(
            f"| `{scenario.scenario_id}` | {scenario.category.value} | {len(scenario.day_results)} | "
            f"{metrics['total_review_units']:.9g} | {status} |"
        )

    failures = [
        (scenario.scenario_id, assertion.detail)
        for scenario in result.scenario_results
        for assertion in scenario.assertions
        if assertion.status is AssertionStatus.FAILED
    ]
    lines.extend(["", "## Failed assertions", ""])
    if failures:
        lines.extend(f"- `{scenario_id}`: {detail}" for scenario_id, detail in failures)
    else:
        lines.append("None.")

    lines.extend(["", "## Abuse and control comparisons", ""])
    comparisons = [item.comparison for item in result.scenario_results if item.comparison]
    if comparisons:
        lines.extend([
            "| Scenario | Control | Total delta | Total ratio |",
            "|---|---|---:|---:|",
        ])
        for comparison in comparisons:
            deltas = dict(comparison.deltas)
            ratios = dict(comparison.ratios)
            ratio = ratios["total_review_units"]
            ratio_text = "undefined" if ratio is None else f"{ratio:.9g}"
            lines.append(
                f"| `{comparison.scenario_id}` | `{comparison.control_scenario_id}` | "
                f"{deltas['total_review_units']:.9g} | {ratio_text} |"
            )
    else:
        lines.append("None.")

    lines.extend(["", "## Component breakdown", ""])
    for scenario in result.scenario_results:
        metrics = dict(scenario.metrics)
        lines.extend([
            f"### `{scenario.scenario_id}`",
            "",
            f"- Core baseline: `{metrics['core_baseline']:.9g}`",
            f"- Core context: `{metrics['core_context']:.9g}`",
            f"- Support: `{metrics['support']:.9g}`",
            f"- Supplemental: `{metrics['supplemental']:.9g}`",
            f"- Volume: `{metrics['volume_credit']:.9g}`",
            f"- Completion: `{metrics['completion_credit']:.9g}`",
            f"- Total: `{metrics['total_review_units']:.9g}`",
            "",
        ])

    lines.extend(["## Warnings", ""])
    if result.warnings:
        lines.extend(f"- {warning}" for warning in result.warnings)
    else:
        lines.append("None.")
    lines.extend(["", "## Executed scenario IDs", ""])
    lines.extend(f"- `{item}`" for item in result.manifest.scenario_ids)
    return "\n".join(lines) + "\n"


def write_reports(result: CorpusRunResult, output_root: Path) -> Path:
    resolved_root = output_root.resolve()
    if output_root.exists() and output_root.is_symlink():
        raise ValueError(f"output directory must not be a symlink: {output_root}")
    resolved_root.mkdir(parents=True, exist_ok=True)
    run_dir = resolved_root / f"run-{result.manifest.input_digest[:12]}"
    if run_dir.exists() and run_dir.is_symlink():
        raise ValueError(f"run output directory must not be a symlink: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "results.json").write_text(render_json_report(result), encoding="utf-8")
    (run_dir / "summary.md").write_text(render_markdown_report(result), encoding="utf-8")
    return run_dir
