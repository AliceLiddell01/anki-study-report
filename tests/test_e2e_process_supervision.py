from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "docker" / "anki-e2e" / "run-e2e-failure-wrapper.sh"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_dead(pid: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not alive(pid):
            return True
        time.sleep(0.02)
    return not alive(pid)


def make_core(tmp_path: Path, *, functional_exit: int | None = None) -> Path:
    core = tmp_path / "core.sh"
    if functional_exit is not None:
        body = f"#!/usr/bin/env bash\nexit {functional_exit}\n"
    else:
        body = '''#!/usr/bin/env bash
set -u
state="$ASR_TEST_STATE"
cleanup_count="$state/cleanup-count"
on_signal() {
  count=0
  [ -f "$cleanup_count" ] && count="$(cat "$cleanup_count")"
  echo $((count + 1)) > "$cleanup_count"
  exit "$2"
}
trap 'on_signal SIGINT 130' INT
trap 'on_signal SIGTERM 143' TERM
sleep 60 &
child=$!
echo "$child" > "$state/child.pid"
(
  sleep 60 &
  grandchild=$!
  echo "$grandchild" > "$state/grandchild.pid"
  wait "$grandchild"
) &
helper=$!
echo "$helper" > "$state/helper.pid"
wait "$child"
wait "$helper"
'''
    core.write_text(body, encoding="utf-8", newline="\n")
    core.chmod(0o755)
    return core


def start_wrapper(tmp_path: Path, core: Path) -> tuple[subprocess.Popen[str], Path]:
    state = tmp_path / "state"
    state.mkdir()
    artifacts = tmp_path / "artifacts"
    env = os.environ.copy()
    env.update(
        {
            "ASR_E2E_CORE": str(core),
            "ASR_TEST_STATE": str(state),
            "ANKI_STUDY_REPORT_E2E_ARTIFACTS": str(artifacts),
        }
    )
    process = subprocess.Popen(
        ["bash", str(WRAPPER)],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process, state


def wait_pids(state: Path) -> list[int]:
    deadline = time.monotonic() + 2
    paths = [state / "child.pid", state / "helper.pid", state / "grandchild.pid"]
    while time.monotonic() < deadline:
        if all(path.is_file() for path in paths):
            return [int(path.read_text()) for path in paths]
        time.sleep(0.02)
    raise AssertionError("synthetic process tree did not start")


@pytest.mark.skipif(os.name == "nt", reason="Unix signal/process-group contract")
@pytest.mark.parametrize(("sig", "expected"), [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_wrapper_forwards_signal_to_owned_process_group_and_preserves_exit(
    tmp_path: Path, sig: signal.Signals, expected: int
):
    unrelated = subprocess.Popen(["sleep", "60"])
    process, state = start_wrapper(tmp_path, make_core(tmp_path))
    pids = wait_pids(state)
    started = time.monotonic()
    try:
        process.send_signal(sig)
        assert process.wait(timeout=5) == expected
        assert time.monotonic() - started < 5
        assert all(wait_dead(pid) for pid in pids)
        assert alive(unrelated.pid)
        assert (state / "cleanup-count").read_text().strip() == "1"
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=2)
        if process.poll() is None:
            process.kill()


@pytest.mark.skipif(os.name == "nt", reason="Unix signal/process-group contract")
def test_functional_exit_remains_functional_failure(tmp_path: Path):
    process, _ = start_wrapper(tmp_path, make_core(tmp_path, functional_exit=7))
    assert process.wait(timeout=5) == 7
