from __future__ import annotations

from pathlib import Path

from run_event_contract import failure_protocol
from run_event_context import discover_original_exit_code, last_successful_phase, summary_primary_code
from run_event_storage import _elapsed_ms, failure_summary_path


def ensure_failure_summary(
    output: Path,
    producer: str,
    phase_id: str,
    code: str,
    *,
    message: str | None,
    original_exit_code: int | None,
    original_signal: str | None,
) -> None:
    if phase_id == "run":
        return
    path = failure_summary_path(output)
    if original_exit_code is None:
        original_exit_code = discover_original_exit_code(output, phase_id)
    if producer == "docker-e2e" and phase_id == "browser-smoke-first" and not path.is_file():
        browser_report = output.parent / "browser-smoke-first.json"
        if browser_report.is_file():
            try:
                browser_entry, last_item = failure_protocol.browser_failure_from_report(
                    browser_report, original_exit_code=original_exit_code or 1
                )
                failure_protocol.record_failure(
                    path,
                    producer,
                    browser_entry,
                    primary=True,
                    last_successful_phase_id=last_successful_phase(output),
                    last_successful_item_id=last_item,
                    active_phase_id=phase_id,
                    active_item_id=browser_entry["itemId"],
                )
                return
            except failure_protocol.FailureProtocolError:
                pass
    entry = failure_protocol.build_failure(
        code=code,
        phase_id=phase_id,
        error_type="ProcessFailure",
        summary=message or failure_protocol.definition(code).default_summary,
        elapsed_ms=_elapsed_ms(output, producer),
        original_exit_code=original_exit_code,
        original_signal=original_signal,
        evidence_paths=[output.relative_to(output.parent.parent).as_posix()]
        if output.parent.name == "reports"
        else [output.name],
        raw_diagnostic_paths=["logs/fast-check.log"] if producer == "fast-ci" else ["diagnostics/anki.log"],
    )
    failure_protocol.record_failure(
        path,
        producer,
        entry,
        primary=not path.is_file(),
        last_successful_phase_id=last_successful_phase(output),
        active_phase_id=phase_id,
    )


def resolve_failure_code(
    output: Path,
    producer: str,
    phase_id: str,
    status: str,
    failure_code: str | None,
) -> str | None:
    if status not in {"fail", "cancel"}:
        return None
    if status == "cancel":
        return "ASR-FAST-CANCELLED" if producer == "fast-ci" else "ASR-E2E-CANCELLED"
    if failure_code:
        return failure_code
    if phase_id == "run":
        return summary_primary_code(output) or (
            "ASR-FAST-UNKNOWN" if producer == "fast-ci" else "ASR-E2E-UNKNOWN"
        )
    return failure_protocol.code_for_phase(producer, phase_id)


def create_run_level_summary(
    output: Path,
    producer: str,
    status: str,
    *,
    duration_ms: int,
    message: str | None,
    failure_code: str | None,
    original_exit_code: int | None,
    original_signal: str | None,
) -> None:
    summary_file = failure_summary_path(output)
    if summary_file.is_file() or status not in {"fail", "cancel"}:
        return
    if status == "cancel":
        code = "ASR-FAST-CANCELLED" if producer == "fast-ci" else "ASR-E2E-CANCELLED"
    else:
        code = failure_code or ("ASR-FAST-UNKNOWN" if producer == "fast-ci" else "ASR-E2E-UNKNOWN")
    entry = failure_protocol.build_failure(
        code=code,
        error_type="ProcessFailure",
        summary=message or failure_protocol.definition(code).default_summary,
        elapsed_ms=duration_ms,
        original_exit_code=original_exit_code,
        original_signal=original_signal,
        evidence_paths=[output.relative_to(output.parent.parent).as_posix()]
        if output.parent.name == "reports"
        else [output.name],
    )
    failure_protocol.record_failure(
        summary_file,
        producer,
        entry,
        primary=True,
        last_successful_phase_id=last_successful_phase(output),
    )
