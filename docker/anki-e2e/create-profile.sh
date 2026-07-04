#!/usr/bin/env bash
set -Eeuo pipefail

: "${ANKI_BASE:=/e2e/anki-data}"
: "${ANKI_PROFILE:=E2E}"
: "${ANKI_PROFILE_DIR:=${ANKI_BASE}/${ANKI_PROFILE}}"

if [ "${KEEP_E2E_DATA:-0}" != "1" ]; then
  case "$ANKI_BASE" in
    ""|"/"|"/e2e"|"/e2e/")
      echo "Refusing to reset unsafe ANKI_BASE: ${ANKI_BASE}" >&2
      exit 1
      ;;
  esac
  mkdir -p "$ANKI_BASE"
  find "$ANKI_BASE" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
fi

mkdir -p "$ANKI_BASE" "$ANKI_PROFILE_DIR" "$ANKI_PROFILE_DIR/collection.media" "$ANKI_BASE/addons21"

cat > "$ANKI_PROFILE_DIR/README-e2e.txt" <<EOF
This Anki profile is generated for Anki Study Report Docker E2E tests.
It is safe to delete and must not contain personal Anki data.
EOF

echo "Prepared isolated Anki profile at ${ANKI_PROFILE_DIR}"
