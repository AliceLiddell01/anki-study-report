from __future__ import annotations

import json
from pathlib import Path
import time

import pytest

from scripts.ci_fast_timing import (
    PHASES,
    SCHEMA_VERSION,
    TimingError,
    finalize,
    finish_phase,
    initialize,
    record_phase_for_test,
    render_markdown,
    start_phase,
    validate_document,
)

SHA = "A" * 40
START = "2026-07-16T10:00:00.000Z"
END = "2026-07-16T10:00:01.000Z"


def init(tmp_path: Path, **overrides: object) -> Path:
    output = tmp_path / "timing" / "fast-ci-timing.json"
    values = {
        "repository": "AliceLiddell01/anki-study-report",
        "event_name": "workflow_dispatch",
        "ref": "refs/heads/example",
        "tested_commit_sha": SHA,
        "run_id": 123,
        "run_attempt": 1,
    }
    values.update(overrides)
    initialize(output, **values)
    return output


def test_initialize_valid_document(tmp_path: Path) -> None:
    output = init(tmp_path)
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["schemaVersion"] == SCHEMA_VERSION == 1
    assert document["testedCommitSha"] == SHA.lower()
    assert document["result"] == "running"
    assert document["completedAt"] is None
    assert output.with_name(output.name + ".state").is_file()
    validate_document(document, allow_running=True)


def test_successful_phase_uses_monotonic_duration(tmp_path: Path) -> None:
    output = init(tmp_path)
    start_phase(output, "frontend-vitest")
    time.sleep(0.002)
    finish_phase(output, "frontend-vitest", 0)
    phase = json.loads(output.read_text(encoding="utf-8"))["phases"][0]
    assert phase["status"] == "success"
    assert phase["exitCode"] == 0
    assert phase["durationMs"] >= 0


def test_failed_phase(tmp_path: Path) -> None:
    output = init(tmp_path)
    start_phase(output, "python-pytest")
    finish_phase(output, "python-pytest", 7)
    phase = json.loads(output.read_text(encoding="utf-8"))["phases"][0]
    assert phase["status"] == "failure"
    assert phase["exitCode"] == 7


def test_duplicate_phase_id_is_rejected(tmp_path: Path) -> None:
    output = init(tmp_path)
    start_phase(output, "frontend-vitest")
    with pytest.raises(TimingError, match="Duplicate phase id"):
        start_phase(output, "frontend-vitest")


def test_invalid_phase_id_is_rejected(tmp_path: Path) -> None:
    output = init(tmp_path)
    with pytest.raises(TimingError, match="Unknown phase id"):
        start_phase(output, "not-allowlisted")


def test_negative_duration_is_rejected(tmp_path: Path) -> None:
    output = init(tmp_path)
    with pytest.raises(TimingError, match="non-negative"):
        record_phase_for_test(
            output,
            phase_id="frontend-vitest",
            status="success",
            started_at=START,
            completed_at=END,
            duration_ms=-1,
            exit_code=0,
        )


def test_invalid_status_is_rejected(tmp_path: Path) -> None:
    output = init(tmp_path)
    with pytest.raises(TimingError, match="Invalid phase status"):
        record_phase_for_test(
            output,
            phase_id="frontend-vitest",
            status="unknown",
            started_at=START,
            completed_at=END,
            duration_ms=1,
            exit_code=0,
        )


def test_invalid_sha_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(TimingError, match="40-character"):
        init(tmp_path, tested_commit_sha="bad")


@pytest.mark.parametrize(("field", "value"), [("run_id", 0), ("run_attempt", -1)])
def test_invalid_run_identity_is_rejected(tmp_path: Path, field: str, value: int) -> None:
    with pytest.raises(TimingError, match="positive integer"):
        init(tmp_path, **{field: value})


def test_atomic_output_update_leaves_no_temp_files(tmp_path: Path) -> None:
    output = init(tmp_path)
    start_phase(output, "frontend-vitest")
    finish_phase(output, "frontend-vitest", 0)
    finalize(output, "success")
    assert not list(output.parent.glob("*.tmp"))
    assert not output.with_name(output.name + ".state").exists()


def test_markdown_renders_missing_historical_typecheck_without_fabricating_phase(tmp_path: Path) -> None:
    output = init(tmp_path)
    record_phase_for_test(
        output,
        phase_id="frontend-typecheck-tests",
        status="success",
        started_at=START,
        completed_at=END,
        duration_ms=10,
        exit_code=0,
    )
    record_phase_for_test(
        output,
        phase_id="frontend-vitest",
        status="success",
        started_at=START,
        completed_at=END,
        duration_ms=20,
        exit_code=0,
    )
    document = finalize(output, "success")
    markdown = render_markdown(document)
    assert "# Fast CI timing" in markdown
    assert markdown.index("| Frontend Vitest | frontend | success | 20 ms |") < markdown.index(
        "| Frontend typecheck before tests | frontend | success | 10 ms |"
    )
    assert "| Frontend typecheck before tests | 10 ms |" in markdown
    assert "| Frontend typecheck before build | not recorded |" in markdown
    assert all(phase["id"] != "frontend-typecheck-build" for phase in document["phases"])
    assert "GitHub Jobs API" in markdown


def test_failure_finalization_recovers_running_phase(tmp_path: Path) -> None:
    output = init(tmp_path)
    start_phase(output, "python-pytest")
    document = finalize(output, "failure")
    assert document["result"] == "failure"
    assert document["phases"][0]["status"] == "failure"
    assert document["phases"][0]["exitCode"] == 1
    validate_document(document)


def test_success_finalization_downgrades_when_phase_is_running(tmp_path: Path) -> None:
    output = init(tmp_path)
    start_phase(output, "python-pytest")
    document = finalize(output, "success")
    assert document["result"] == "failure"


def test_document_rejects_absolute_paths_and_token_urls(tmp_path: Path) -> None:
    with pytest.raises(TimingError, match="unsafe path"):
        init(tmp_path, ref="C:\\Users\\example")
    with pytest.raises(TimingError, match="unsafe path"):
        init(tmp_path / "second", ref="https://example.invalid/?token=secret")


def test_stable_schema_and_phase_allowlist(tmp_path: Path) -> None:
    output = init(tmp_path)
    document = json.loads(output.read_text(encoding="utf-8"))
    assert set(document) == {
        "schemaVersion",
        "repository",
        "workflowName",
        "producerJob",
        "eventName",
        "ref",
        "testedCommitSha",
        "runId",
        "runAttempt",
        "startedAt",
        "completedAt",
        "result",
        "durationMs",
        "phases",
    }
    assert "frontend-typecheck-tests" in PHASES
    assert "frontend-typecheck-build" in PHASES
    assert all(" " not in phase_id for phase_id in PHASES)
