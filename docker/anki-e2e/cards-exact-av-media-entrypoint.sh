#!/usr/bin/env bash
set -uo pipefail

: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
: "${ANKI_E2E_HOST_UID:=}"
: "${ANKI_E2E_HOST_GID:=}"

export ASR_E2E_CORE=/e2e/bin/run-e2e.sh

set +e
/e2e/bin/run-e2e-failure-wrapper.sh
status=$?
set -e

ownership_status=0
if [ -n "$ANKI_E2E_HOST_UID" ] && [ -n "$ANKI_E2E_HOST_GID" ]; then
  if ! chown -R "$ANKI_E2E_HOST_UID:$ANKI_E2E_HOST_GID" "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"; then
    echo "Cards exact E2E ownership normalization failed for the artifact directory." >&2
    ownership_status=7
  fi
fi

if [ "$status" -eq 0 ] && [ "$ownership_status" -ne 0 ]; then
  status="$ownership_status"
fi
exit "$status"
