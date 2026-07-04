#!/usr/bin/env bash
set -Eeuo pipefail

label="${1:-run}"
: "${ANKI_BIN:=/opt/anki/anki}"
: "${ANKI_BASE:=/e2e/anki-data}"
: "${ANKI_PROFILE:=E2E}"
: "${ANKI_PROFILE_DIR:=${ANKI_BASE}/${ANKI_PROFILE}}"
: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
: "${ANKI_STUDY_REPORT_E2E_READY_FILE:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/dashboard-ready.json}"
: "${DISPLAY:=:99}"

mkdir -p "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"
rm -f "$ANKI_STUDY_REPORT_E2E_READY_FILE" "$ANKI_STUDY_REPORT_E2E_ARTIFACTS/anki.pid"

write_e2e_runner_event() {
  local stage="$1"
  local addon_dir="${ANKI_BASE}/addons21/anki_study_report_e2e"
  STAGE="$stage" \
  ADDON_DIR="$addon_dir" \
  ANKI_STUDY_REPORT_E2E_EVENTS_FILE="${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/addon-e2e-events.jsonl" \
    python3 - <<'PY'
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path

addon_dir = Path(os.environ["ADDON_DIR"])
payload = {
    "stage": os.environ["STAGE"],
    "time": datetime.now().isoformat(timespec="milliseconds"),
    "pid": os.getpid(),
    "source": "start-anki.sh",
    "path": str(addon_dir),
    "hasInit": (addon_dir / "__init__.py").is_file(),
    "hasManifest": (addon_dir / "manifest.json").is_file(),
}
events_file = Path(os.environ["ANKI_STUDY_REPORT_E2E_EVENTS_FILE"])
events_file.parent.mkdir(parents=True, exist_ok=True)
with events_file.open("a", encoding="utf-8") as file:
    file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    file.write("\n")
PY
}

print_prefs_profiles() {
  PREFS_PATH="${ANKI_BASE}/prefs21.db" python3 - <<'PY'
from __future__ import annotations

import os
from pathlib import Path
import sqlite3

prefs = Path(os.environ["PREFS_PATH"])
print(f"prefs21.db exists: {prefs.is_file()} ({prefs})")
if not prefs.is_file():
    raise SystemExit(0)
try:
    with sqlite3.connect(prefs) as conn:
        rows = conn.execute(
            "select name, length(cast(data as blob)) from profiles order by name"
        ).fetchall()
except Exception as exc:
    print(f"prefs21.db profiles query failed: {exc}")
else:
    print("prefs21.db profiles:")
    for name, blob_bytes in rows:
        print(f"  {name}: blobBytes={int(blob_bytes or 0)}")
PY
}

{
  echo "Anki Study Report E2E env:"
  echo "ANKI_STUDY_REPORT_E2E=${ANKI_STUDY_REPORT_E2E:-1}"
  echo "ANKI_STUDY_REPORT_E2E_ARTIFACTS=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}"
  echo "ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR=${ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR:-}"
  echo "ANKI_STUDY_REPORT_E2E_DEBUG_QT=${ANKI_STUDY_REPORT_E2E_DEBUG_QT:-0}"
} | tee "${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/e2e-env-${label}.txt"

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  Xvfb "$DISPLAY" -screen 0 1920x1080x24 +extension GLX +render -noreset \
    >"${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/xvfb.log" 2>&1 &
  echo "$!" > "${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/xvfb.pid"
fi

for _ in $(seq 1 20); do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  echo "Warning: Xvfb display ${DISPLAY} is not responding before Anki start."
fi

if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  eval "$(dbus-launch --sh-syntax)"
  echo "${DBUS_SESSION_BUS_PID:-}" > "${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/dbus.pid"
fi

echo "Anki base add-ons before start:"
ls -la "${ANKI_BASE}/addons21" || true
echo "Anki profile folder before start:"
ls -la "$ANKI_PROFILE_DIR" || true
echo "Anki prefs before start:"
print_prefs_profiles || true
echo "Collection before start:"
if [ -f "${ANKI_PROFILE_DIR}/collection.anki2" ]; then
  ls -la "${ANKI_PROFILE_DIR}/collection.anki2"
else
  echo "Missing ${ANKI_PROFILE_DIR}/collection.anki2"
fi
echo "E2E add-on init before start:"
if [ -f "${ANKI_BASE}/addons21/anki_study_report_e2e/__init__.py" ]; then
  ls -la "${ANKI_BASE}/addons21/anki_study_report_e2e/__init__.py"
else
  echo "Missing ${ANKI_BASE}/addons21/anki_study_report_e2e/__init__.py"
fi
if [ -d "${ANKI_PROFILE_DIR}/addons21" ]; then
  echo "Warning: ${ANKI_PROFILE_DIR}/addons21 exists, but Anki add-ons should be installed under ${ANKI_BASE}/addons21."
  ls -la "${ANKI_PROFILE_DIR}/addons21" || true
fi
write_e2e_runner_event "addon_folder_present"

diagnostics_file="${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/qt-xcb-diagnostics-${label}.log"
{
  echo "Anki Qt/XCB diagnostics (${label})"
  echo "DISPLAY=${DISPLAY}"
  echo
  echo "which anki:"
  which anki || true
  echo
  echo "ANKI_BIN=${ANKI_BIN}"
  echo "Anki version:"
  "$ANKI_BIN" --version || true
  echo
  echo "xdpyinfo:"
  xdpyinfo -display "$DISPLAY" 2>&1 | sed -n '1,40p' || true
  echo
  echo "libqxcb.so files:"
  mapfile -t qxcb_plugins < <(find /opt/anki -name 'libqxcb.so' -print)
  if [ "${#qxcb_plugins[@]}" -eq 0 ]; then
    echo "No libqxcb.so found under /opt/anki"
  fi
  for plugin in "${qxcb_plugins[@]}"; do
    echo "$plugin"
  done
  for plugin in "${qxcb_plugins[@]}"; do
    echo
    echo "ldd ${plugin}:"
    ldd "$plugin" || true
  done
} | tee "$diagnostics_file"

if grep -q "not found" "$diagnostics_file"; then
  echo "Missing Qt xcb dependencies detected"
fi

help_text="$("$ANKI_BIN" --help 2>&1 || true)"
printf '%s\n' "$help_text" > "${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/anki-help.txt"

anki_args=()
if grep -q -- "-b" <<<"$help_text"; then
  anki_args+=("-b" "$ANKI_BASE")
fi
if grep -q -- "-p" <<<"$help_text"; then
  anki_args+=("-p" "$ANKI_PROFILE")
fi

echo "Starting Anki (${label}) with args: ${anki_args[*]}"
if [ "${ANKI_STUDY_REPORT_E2E_DEBUG_QT:-0}" = "1" ]; then
  QT_DEBUG_PLUGINS=1 \
  ANKI_STUDY_REPORT_E2E=1 \
  ANKI_STUDY_REPORT_E2E_ARTIFACTS="$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
  ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR="${ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR:-}" \
  ANKI_STUDY_REPORT_E2E_READY_FILE="$ANKI_STUDY_REPORT_E2E_READY_FILE" \
  QTWEBENGINE_DISABLE_SANDBOX=1 \
  QT_OPENGL=software \
  LIBGL_ALWAYS_SOFTWARE=1 \
  NO_AT_BRIDGE=1 \
  "$ANKI_BIN" "${anki_args[@]}" \
    >"${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/anki-stdout-${label}.log" \
    2>"${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/anki-stderr-${label}.log" &
else
  ANKI_STUDY_REPORT_E2E=1 \
  ANKI_STUDY_REPORT_E2E_ARTIFACTS="$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
  ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR="${ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR:-}" \
  ANKI_STUDY_REPORT_E2E_READY_FILE="$ANKI_STUDY_REPORT_E2E_READY_FILE" \
  QTWEBENGINE_DISABLE_SANDBOX=1 \
  QT_OPENGL=software \
  LIBGL_ALWAYS_SOFTWARE=1 \
  NO_AT_BRIDGE=1 \
  "$ANKI_BIN" "${anki_args[@]}" \
    >"${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/anki-stdout-${label}.log" \
    2>"${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/anki-stderr-${label}.log" &
fi

echo "$!" > "${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/anki.pid"
echo "Anki pid: $(cat "${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/anki.pid")"
