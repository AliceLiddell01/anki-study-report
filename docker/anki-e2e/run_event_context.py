from __future__ import annotations

import json
from pathlib import Path

from run_event_contract import RunEventError, failure_protocol, validate_event
from run_event_storage import failure_summary_path


def last_successful_phase(output: Path) -> str | None:
    if not output.is_file():
        return None
    phases: list[str] = []
    try:
        for raw_line in output.read_bytes().splitlines():
            value = json.loads(raw_line.decode("utf-8"))
            event = validate_event(value)
            if event["eventKind"] == "phase" and event["status"] == "pass":
                phases.append(event["phaseId"])
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RunEventError):
        return None
    return phases[-1] if phases else None


def summary_primary_code(output: Path) -> str | None:
    path = failure_summary_path(output)
    if not path.is_file():
        return None
    return failure_protocol.load_document(path)["primary"]["failureCode"]


def discover_original_exit_code(output: Path, phase_id: str) -> int | None:
    if output.parent.name != "ci-fast":
        # Current Docker phase adapters expose only generic non-zero status.
        return 1
    timing = output.parent / "timing" / "fast-ci-timing.json"
    try:
        payload = json.loads(timing.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    phases = payload.get("phases") if isinstance(payload, dict) else None
    if not isinstance(phases, list):
        return None
    phase = next((item for item in phases if isinstance(item, dict) and item.get("id") == phase_id), None)
    value = phase.get("exitCode") if isinstance(phase, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
