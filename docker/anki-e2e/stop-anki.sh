#!/usr/bin/env bash
set -Eeuo pipefail

: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
: "${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/runtime}"
summary_path="${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/reports/failure-summary.json"
pid_file="${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR}/anki.pid"

record_cleanup_failure() {
  local message="$1"
  local command="record-primary"
  [ -f "$summary_path" ] && command="record-secondary"
  /e2e/bin/failure_protocol.py "$command" \
    --output "$summary_path" \
    --producer docker-e2e \
    --failure-code ASR-E2E-CLEANUP \
    --error-type CleanupError \
    --summary "$message" \
    --original-exit-code 1 || true
  /e2e/bin/failure_protocol.py set-cleanup-status --output "$summary_path" --status failure || true
}

if [ ! -f "$pid_file" ]; then
  exit 0
fi

pid="$(cat "$pid_file" || true)"
if [ -z "$pid" ] || ! kill -0 "$pid" >/dev/null 2>&1; then
  rm -f "$pid_file"
  exit 0
fi

if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
  rm -f "$pid_file"
  record_cleanup_failure "Anki PID file contained an invalid process identifier"
  exit 1
fi

echo "Stopping Anki pid ${pid}"
if ! kill -TERM "$pid" >/dev/null 2>&1; then
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    rm -f "$pid_file"
    exit 0
  fi
  record_cleanup_failure "Anki process could not receive SIGTERM during cleanup"
  exit 1
fi

for _ in $(seq 1 30); do
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    rm -f "$pid_file"
    exit 0
  fi
  sleep 1
done

echo "Anki did not exit after TERM; sending KILL"
if ! kill -KILL "$pid" >/dev/null 2>&1; then
  record_cleanup_failure "Anki process could not receive SIGKILL during cleanup"
  exit 1
fi
for _ in $(seq 1 5); do
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    rm -f "$pid_file"
    exit 0
  fi
  sleep 1
done
record_cleanup_failure "Anki process remained alive after SIGKILL during cleanup"
exit 1
