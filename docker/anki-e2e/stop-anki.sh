#!/usr/bin/env bash
set -Eeuo pipefail

: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
: "${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/runtime}"
pid_file="${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR}/anki.pid"

if [ ! -f "$pid_file" ]; then
  exit 0
fi

pid="$(cat "$pid_file" || true)"
if [ -z "$pid" ] || ! kill -0 "$pid" >/dev/null 2>&1; then
  rm -f "$pid_file"
  exit 0
fi

echo "Stopping Anki pid ${pid}"
kill -TERM "$pid" >/dev/null 2>&1 || true

for _ in $(seq 1 30); do
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    rm -f "$pid_file"
    exit 0
  fi
  sleep 1
done

echo "Anki did not exit after TERM; sending KILL"
kill -KILL "$pid" >/dev/null 2>&1 || true
rm -f "$pid_file"
