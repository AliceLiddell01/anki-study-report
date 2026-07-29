#!/usr/bin/env bash
set -uo pipefail

: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
reports_dir="${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/reports"
summary_path="${reports_dir}/failure-summary.json"
cancellation_path="${reports_dir}/cancellation-summary.json"
events_path="${reports_dir}/run-events.jsonl"
browser_path="${reports_dir}/browser-smoke-first.json"
failure_protocol="/e2e/bin/failure_protocol.py"
cancellation_protocol="/e2e/bin/cancellation_protocol.py"
run_event_protocol="/e2e/bin/run_event_protocol.py"
: "${ASR_E2E_CORE:=/e2e/bin/run-e2e.sh}"
core="$ASR_E2E_CORE"

child_pid=""
requested_exit=""
requested_signal=""

forward_signal() {
  local signal="$1" exit_code="$2"
  if [ -n "$requested_exit" ]; then
    return
  fi
  requested_exit="$exit_code"
  requested_signal="$signal"
  if [ -n "$child_pid" ] && kill -0 "$child_pid" >/dev/null 2>&1; then
    kill "-${signal#SIG}" -- "-$child_pid" >/dev/null 2>&1 || kill "-${signal#SIG}" "$child_pid" >/dev/null 2>&1 || true
  fi
}

trap 'forward_signal SIGINT 130' INT
trap 'forward_signal SIGTERM 143' TERM

set +e
setsid "$core" "$@" &
child_pid=$!
wait "$child_pid"
status=$?
set -e

if [ -n "$requested_exit" ]; then
  status="$requested_exit"
  for _ in $(seq 1 15); do
    kill -0 "$child_pid" >/dev/null 2>&1 || break
    sleep 0.1
  done
  if kill -0 "$child_pid" >/dev/null 2>&1; then
    kill -TERM -- "-$child_pid" >/dev/null 2>&1 || kill -TERM "$child_pid" >/dev/null 2>&1 || true
    for _ in $(seq 1 10); do
      kill -0 "$child_pid" >/dev/null 2>&1 || break
      sleep 0.1
    done
  fi
  if kill -0 "$child_pid" >/dev/null 2>&1; then
    kill -KILL -- "-$child_pid" >/dev/null 2>&1 || kill -KILL "$child_pid" >/dev/null 2>&1 || true
  fi
  wait "$child_pid" >/dev/null 2>&1 || true
elif [ "$status" -eq 130 ]; then
  requested_exit=130
elif [ "$status" -eq 143 ]; then
  requested_exit=143
fi

mkdir -p "$reports_dir"

if [ "$status" -eq 130 ] || [ "$status" -eq 143 ]; then
  signal="$requested_signal"
  signal_args=()
  [ -n "$signal" ] && signal_args+=(--original-signal "$signal")
  if [ -f "$summary_path" ]; then
    echo "Cancellation must not coexist with failure-summary.json." >&2
    rm -f "$summary_path"
  fi
  if [ ! -f "$cancellation_path" ]; then
    evidence_args=()
    [ -f "$events_path" ] && evidence_args+=(--evidence-path reports/run-events.jsonl)
    [ -f "${reports_dir}/preflight-report.json" ] && evidence_args+=(--evidence-path reports/preflight-report.json)
    "$cancellation_protocol" record \
      --output "$cancellation_path" \
      --producer docker-e2e \
      --elapsed-ms 0 \
      --original-exit-code "$status" \
      "${signal_args[@]}" \
      --cleanup-status partial \
      --cleanup-duration-ms 0 \
      --cleanup-attempts 1 \
      --artifact-status unavailable \
      --run-events "$events_path" \
      --browser-report "$browser_path" \
      "${evidence_args[@]}" || true
  fi
  if [ -f "$events_path" ]; then
    "$run_event_protocol" cancel-run \
      --output "$events_path" \
      --producer docker-e2e \
      --original-exit-code "$status" \
      "${signal_args[@]}" || true
    "$run_event_protocol" validate --output "$events_path" --producer docker-e2e || true
  fi
  exit "$status"
fi

if [ "$status" -ne 0 ] && [ ! -f "$summary_path" ]; then
  "$failure_protocol" record-primary \
    --output "$summary_path" \
    --producer docker-e2e \
    --failure-code ASR-E2E-UNKNOWN \
    --error-type ProcessFailure \
    --summary "Docker E2E failed before a known phase failure was persisted" \
    --original-exit-code "$status" || true
fi

if [ -f "$summary_path" ]; then
  if ! /e2e/bin/write-artifact-manifest.py \
      --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
      --status failed \
      --anki-version "${ANKI_VERSION:-unknown}"; then
    "$failure_protocol" record-secondary \
      --output "$summary_path" \
      --producer docker-e2e \
      --failure-code ASR-E2E-ARTIFACT-MANIFEST \
      --phase-id artifact-manifest \
      --error-type ManifestFailure \
      --summary "Artifact manifest generation or validation failed" \
      --original-exit-code 6 || true
    [ "$status" -ne 0 ] || status=6
  fi
  cleanup_status="$(python3 - "$summary_path" <<'PY_CLEANUP'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
print(value.get("cleanup", {}).get("status", "not_started"))
PY_CLEANUP
)"
  if [ "$cleanup_status" = "not_started" ]; then
    "$failure_protocol" set-cleanup-status --output "$summary_path" --status success || true
  fi
  if ! "$failure_protocol" validate --output "$summary_path"; then
    echo "Canonical failure summary validation failed." >&2
    [ "$status" -ne 0 ] || status=6
  elif [ "$status" -eq 0 ]; then
    status="$(python3 - "$summary_path" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
print(int(value["primary"]["exitClass"]))
PY
)"
  fi
fi

if [ -f "$events_path" ]; then
  "$run_event_protocol" validate --output "$events_path" --producer docker-e2e || {
    echo "Canonical run-event validation failed in the outer E2E wrapper." >&2
    [ "$status" -ne 0 ] || status=6
  }
fi

exit "$status"
