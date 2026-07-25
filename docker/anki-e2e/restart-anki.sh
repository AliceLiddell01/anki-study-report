#!/usr/bin/env bash
set -Eeuo pipefail

label="${1:-restart}"
/e2e/bin/stop-anki.sh
echo "[real-decks] restarting Anki without mutating imported note types, fields, templates, or media"
/e2e/bin/start-anki.sh "$label"
