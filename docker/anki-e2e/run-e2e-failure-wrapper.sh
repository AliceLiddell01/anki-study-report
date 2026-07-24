#!/usr/bin/env bash
set -uo pipefail

: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
reports_dir="${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/reports"
summary_path="${reports_dir}/failure-summary.json"
events_path="${reports_dir}/run-events.jsonl"
protocol="/e2e/bin/failure_protocol.py"
core="/e2e/bin/run-e2e.sh"

set +e
"$core" "$@"
status=$?
set -e

mkdir -p "$reports_dir"
if [ "$status" -ne 0 ] && [ ! -f "$summary_path" ]; then
  if [ "$status" -eq 130 ] || [ "$status" -eq 143 ]; then
    signal="SIGINT"
    [ "$status" -eq 143 ] && signal="SIGTERM"
    "$protocol" record-primary \
      --output "$summary_path" \
      --producer docker-e2e \
      --failure-code ASR-E2E-CANCELLED \
      --error-type ProcessSignal \
      --summary "Docker E2E was cancelled before a phase failure was persisted" \
      --original-exit-code "$status" \
      --original-signal "$signal" || true
  else
    "$protocol" record-primary \
      --output "$summary_path" \
      --producer docker-e2e \
      --failure-code ASR-E2E-UNKNOWN \
      --error-type ProcessFailure \
      --summary "Docker E2E failed before a known phase failure was persisted" \
      --original-exit-code "$status" || true
  fi
fi

if [ -f "$summary_path" ]; then
  if ! /e2e/bin/write-artifact-manifest.py \
      --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
      --status failed \
      --anki-version "${ANKI_VERSION:-unknown}"; then
    "$protocol" record-secondary \
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
    "$protocol" set-cleanup-status --output "$summary_path" --status success || true
  fi
  if ! "$protocol" validate --output "$summary_path"; then
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
  /e2e/bin/run_event_protocol.py validate --output "$events_path" --producer docker-e2e || {
    echo "Canonical run-event validation failed in the outer E2E wrapper." >&2
    [ "$status" -ne 0 ] || status=6
  }
fi

exit "$status"
