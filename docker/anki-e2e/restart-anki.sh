#!/usr/bin/env bash
set -Eeuo pipefail

label="${1:-restart}"
/e2e/bin/stop-anki.sh
case "${ANKI_E2E_SCOPE:-full}" in
  full|cards)
    /e2e/bin/mutate-inspection-profile-fixture.py
    ;;
esac
/e2e/bin/start-anki.sh "$label"
