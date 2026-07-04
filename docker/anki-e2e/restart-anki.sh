#!/usr/bin/env bash
set -Eeuo pipefail

label="${1:-restart}"
/e2e/bin/stop-anki.sh
/e2e/bin/start-anki.sh "$label"
