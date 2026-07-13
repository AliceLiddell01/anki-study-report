"""Deterministic advisory verification planner for a Git change set."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


PRODUCT_RULES = {
    "stats": ("anki_study_report/statistics_", "anki_study_report/fsrs_", "web-dashboard/src/pages/statistics", "web-dashboard/src/pages/fsrs", "web-dashboard/src/components/statistics"),
    "decks": ("anki_study_report/deck_", "web-dashboard/src/pages/decks"),
    "activity": ("anki_study_report/activity_", "web-dashboard/src/pages/activity", "web-dashboard/src/pages/calendar"),
    "settings": ("anki_study_report/config_", "web-dashboard/src/pages/settings", "web-dashboard/src/pages/reportsettings", "web-dashboard/src/pages/serversettings"),
    "cards": ("anki_study_report/note_", "anki_study_report/browser_", "web-dashboard/src/pages/cards", "web-dashboard/src/components/ankicard"),
}
DOC_PREFIXES = ("docs/", "readme.md")
FULL_PREFIXES = (
    ".github/workflows/ci-e2e", "docker/anki-e2e/", "scripts/run_anki_e2e", "scripts/run_full_check",
    "anki_study_report/dashboard_server", "scripts/package_addon", "build_ankiaddon",
)
GLOBAL_PREFIXES = (
    "web-dashboard/src/app/", "web-dashboard/src/layout/", "web-dashboard/src/styles.css",
    "web-dashboard/src/components/statistics/statisticscharts",
)
PAYLOAD_WIDE = ("anki_study_report/dashboard_payload", "web-dashboard/src/types/report")


def plan_for_paths(paths: list[str]) -> dict:
    normalized = sorted({_normalize_path(p) for p in paths if p.strip()})
    if not normalized:
        return _plan(False, None, False, "standard", ["No changed paths were detected."], normalized)
    if all(path.startswith(DOC_PREFIXES) or path.endswith((".md", ".txt")) for path in normalized):
        return _plan(False, None, False, "standard", ["Documentation-only change."], normalized)

    reasons: list[str] = []
    scopes: set[str] = set()
    full = False
    for path in normalized:
        if path.startswith(FULL_PREFIXES) or path.startswith(PAYLOAD_WIDE):
            full = True
            reasons.append(f"High-risk shared runtime surface changed: {path}")
        if path.startswith(GLOBAL_PREFIXES):
            scopes.add("global")
            full = True
            reasons.append(f"Shared app shell or visual primitive changed: {path}")
        for scope, prefixes in PRODUCT_RULES.items():
            if path.startswith(prefixes):
                scopes.add(scope)
                reasons.append(f"{scope} product surface changed: {path}")
    product_scopes = scopes - {"global"}
    if len(product_scopes) > 1:
        full = True
        reasons.append("Multiple product scopes changed.")
    target = next(iter(product_scopes)) if len(product_scopes) == 1 else ("global" if scopes == {"global"} else None)
    e2e = bool(target or full)
    if full and target is None:
        target = "full"
    if not reasons:
        reasons.append("Pure unit/build logic changed; Fast CI is sufficient by default.")
    return _plan(e2e, target, full, "standard", reasons, normalized)


def _normalize_path(path: str) -> str:
    value = path.replace("\\", "/").lower()
    while value.startswith("./"):
        value = value[2:]
    return value


def _plan(e2e: bool, scope: str | None, full: bool, mode: str, reasons: list[str], paths: list[str]) -> dict:
    return {
        "schemaVersion": 1,
        "advisory": True,
        "fastCi": "full",
        "e2eRequired": e2e,
        "targetedScope": scope,
        "fullRequired": full,
        "mode": mode,
        "resourceTelemetry": False,
        "warmCacheRepeat": False,
        "reasons": list(dict.fromkeys(reasons)),
        "changedPaths": paths,
    }


def changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", base, head], check=True, capture_output=True, text=True)
    return result.stdout.splitlines()


def markdown(plan: dict) -> str:
    scope = plan["targetedScope"] or "none"
    reasons = "\n".join(f"- {reason}" for reason in plan["reasons"])
    return (
        "# Verification plan\n\n"
        f"- Fast CI: `required`\n- E2E required: `{str(plan['e2eRequired']).lower()}`\n"
        f"- Targeted scope: `{scope}`\n- Final full gate: `{str(plan['fullRequired']).lower()}`\n"
        f"- Mode: `{plan['mode']}`\n- Resource telemetry: `off`\n- Warm-cache repeat: `forbidden`\n\n"
        f"## Reasons\n\n{reasons}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD^")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--output-dir", default="verification-plan")
    args = parser.parse_args()
    paths = args.paths if args.paths is not None else changed_paths(args.base, args.head)
    plan = plan_for_paths(paths)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "verification-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rendered = markdown(plan)
    (output / "verification-plan.md").write_text(rendered, encoding="utf-8")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write("\n" + rendered)
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
