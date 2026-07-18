#!/usr/bin/env bash
set -Eeuo pipefail

label="${1:-restart}"
/e2e/bin/stop-anki.sh
if [ "${ANKI_E2E_SCOPE:-full}" = "cards" ]; then
  /e2e/bin/mutate-inspection-profile-fixture.py
fi
/e2e/bin/start-anki.sh "$label"
