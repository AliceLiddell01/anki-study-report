from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Iterator

from run_event_contract import *
from run_event_contract import _require_non_negative_int


def _sidecar_directory(output: Path) -> Path:
    return output.parent.parent / "runtime" if output.parent.name == "reports" else output.parent


def state_path(output: Path) -> Path:
    return _sidecar_directory(output) / (output.name + ".state.json")


def lock_path(output: Path) -> Path:
    return _sidecar_directory(output) / (output.name + ".lock")


def failure_summary_path(output: Path) -> Path:
    return output.parent / "failure-summary.json"


def cancellation_summary_path(output: Path) -> Path:
    return output.parent / "cancellation-summary.json"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def _exclusive_lock(output: Path) -> Iterator[None]:
    path = lock_path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        path.write_bytes(b"0")
    with path.open("r+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.01)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _load_state(output: Path) -> dict[str, Any]:
    try:
        state = json.loads(state_path(output).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunEventError(f"run event state does not exist: {state_path(output)}") from exc
    except json.JSONDecodeError as exc:
        raise RunEventError("run event state is not valid JSON") from exc
    if set(state) != {"schemaVersion", "producer", "startedEpochMs"}:
        raise RunEventError("run event state has an invalid shape")
    if state["schemaVersion"] not in SUPPORTED_SCHEMA_VERSIONS or state["producer"] not in PRODUCERS:
        raise RunEventError("run event state identity is invalid")
    _require_non_negative_int(state["startedEpochMs"], "startedEpochMs")
    return state


def _elapsed_ms(output: Path, producer: str) -> int:
    state = _load_state(output)
    if state["producer"] != producer:
        raise RunEventError("run event producer differs from state")
    return max(0, int(time.time() * 1000) - state["startedEpochMs"])


def _last_elapsed_ms(output: Path) -> int:
    if not output.is_file() or output.stat().st_size == 0:
        return 0
    lines = output.read_bytes().splitlines()
    if not lines:
        return 0
    try:
        value = json.loads(lines[-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunEventError("existing run event stream ends with an invalid line") from exc
    elapsed = value.get("elapsedMs") if isinstance(value, dict) else None
    return int(_require_non_negative_int(elapsed, "existing elapsedMs"))


def append_event(output: Path, event: dict[str, Any], *, echo: bool = True) -> dict[str, Any]:
    normalized = validate_event(event)
    output.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_lock(output):
        last_elapsed = _last_elapsed_ms(output)
        if normalized["elapsedMs"] < last_elapsed:
            normalized = dict(normalized)
            normalized["elapsedMs"] = last_elapsed
            normalized = validate_event(normalized)
        encoded = (serialize_event(normalized, validate=False) + "\n").encode("utf-8")
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        descriptor = os.open(output, flags, 0o644)
        try:
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise RunEventError("run event append was incomplete")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    if echo:
        print(format_console(normalized), flush=True)
    return normalized
