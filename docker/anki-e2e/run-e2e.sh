#!/usr/bin/env bash
set -Eeuo pipefail

: "${WORKSPACE:=/workspace}"
: "${E2E_BUILD_DIR:=/e2e/workspace-build}"
: "${ANKI_BASE:=/e2e/anki-data}"
: "${ANKI_PROFILE:=E2E}"
: "${ANKI_PROFILE_DIR:=${ANKI_BASE}/${ANKI_PROFILE}}"
: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
if [ -n "${ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR:-}" ]; then
  ANKI_STUDY_REPORT_E2E_ARTIFACTS="$ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR"
fi
: "${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/runtime}"
: "${ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/diagnostics}"
: "${ANKI_STUDY_REPORT_E2E_REPORTS_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/reports}"
: "${ANKI_STUDY_REPORT_E2E_HTML_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/html}"
: "${ANKI_STUDY_REPORT_E2E_SCREENSHOTS_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/screenshots}"
: "${ANKI_STUDY_REPORT_E2E_PACKAGE_DIR:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/package}"
: "${ANKI_STUDY_REPORT_E2E_READY_FILE:=${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR}/dashboard-ready.json}"
: "${PNPM_BIN:=/e2e/node_modules/.bin/pnpm}"
: "${E2E_MODE:=standard}"
: "${ANKI_E2E_SCOPE:=full}"
: "${ANKI_E2E_SCREENSHOT_WORKERS:=3}"
: "${ANKI_E2E_RESOURCE_TELEMETRY:=1}"
: "${ANKI_E2E_VERIFY_RESTART:=auto}"

export ANKI_BASE ANKI_PROFILE ANKI_PROFILE_DIR ANKI_STUDY_REPORT_E2E_ARTIFACTS
export ANKI_STUDY_REPORT_E2E_RUNTIME_DIR ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR ANKI_STUDY_REPORT_E2E_REPORTS_DIR
export ANKI_STUDY_REPORT_E2E_HTML_DIR ANKI_STUDY_REPORT_E2E_SCREENSHOTS_DIR ANKI_STUDY_REPORT_E2E_PACKAGE_DIR
export ANKI_STUDY_REPORT_E2E_READY_FILE
export ANKI_STUDY_REPORT_E2E=1
export E2E_MODE ANKI_E2E_SCOPE ANKI_E2E_SCREENSHOT_WORKERS ANKI_E2E_RESOURCE_TELEMETRY ANKI_E2E_VERIFY_RESTART

case "$ANKI_E2E_SCOPE" in full|global|stats|decks|activity|cards|settings) ;; *) echo "Unsupported E2E scope: $ANKI_E2E_SCOPE" >&2; exit 2;; esac
case "$ANKI_E2E_SCREENSHOT_WORKERS" in 1|2|3|4) ;; *) echo "Screenshot workers must be 1..4: $ANKI_E2E_SCREENSHOT_WORKERS" >&2; exit 2;; esac
case "$ANKI_E2E_RESOURCE_TELEMETRY" in 0|1) ;; *) echo "Resource telemetry must be 0 or 1" >&2; exit 2;; esac
case "$ANKI_E2E_VERIFY_RESTART" in auto|0|1) ;; *) echo "Restart policy must be auto, 0, or 1" >&2; exit 2;; esac

TOTAL_STARTED_MS=$(date +%s%3N)
TOTAL_STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
RESOURCE_STOP_FILE="${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR}/resource-sampler.stop"
RESOURCE_PID=""

record_phase() {
  local name="$1" started_ms="$2" started_at="$3" status="${4:-success}" notes="${5:-}"
  local finished_ms finished_at
  finished_ms=$(date +%s%3N)
  finished_at=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
  /e2e/bin/e2e-telemetry.py record-phase --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --name "$name" --started-at "$started_at" --finished-at "$finished_at" \
    --duration-ms "$((finished_ms - started_ms))" --status "$status" \
    --scope "$ANKI_E2E_SCOPE" --mode "$E2E_MODE" --notes "$notes"
}

phase_start() {
  PHASE_STARTED_MS=$(date +%s%3N)
  PHASE_STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
}

phase_end() {
  record_phase "$1" "$PHASE_STARTED_MS" "$PHASE_STARTED_AT" "${2:-success}" "${3:-}"
}

run_status="failed"
cleanup() {
  local exit_status=$?
  /e2e/bin/stop-anki.sh || true
  if [ -n "$RESOURCE_PID" ]; then
    touch "$RESOURCE_STOP_FILE"
    wait "$RESOURCE_PID" || true
    rm -f "$RESOURCE_STOP_FILE"
  fi
  record_phase "total canonical E2E" "$TOTAL_STARTED_MS" "$TOTAL_STARTED_AT" "$([ "$exit_status" -eq 0 ] && echo success || echo failed)" || true
  /e2e/bin/e2e-telemetry.py finalize --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --scope "$ANKI_E2E_SCOPE" --mode "$E2E_MODE" --workers "$ANKI_E2E_SCREENSHOT_WORKERS" \
    $([ "$ANKI_E2E_RESOURCE_TELEMETRY" = "1" ] && echo --resource-telemetry) || true
  local manifest_started_ms manifest_started_at
  manifest_started_ms=$(date +%s%3N)
  manifest_started_at=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
  if ! /e2e/bin/write-artifact-manifest.py \
    --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --status "$run_status" \
    --anki-version "${ANKI_VERSION:-unknown}"; then
    echo "E2E artifact manifest generation or validation failed." >&2
    if [ "$exit_status" -eq 0 ]; then
      exit_status=1
    fi
  fi
  record_phase "manifest generation and validation" "$manifest_started_ms" "$manifest_started_at" || true
  /e2e/bin/e2e-telemetry.py finalize --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --scope "$ANKI_E2E_SCOPE" --mode "$E2E_MODE" --workers "$ANKI_E2E_SCREENSHOT_WORKERS" \
    $([ "$ANKI_E2E_RESOURCE_TELEMETRY" = "1" ] && echo --resource-telemetry) || true
  /e2e/bin/write-artifact-manifest.py --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" --status "$run_status" --anki-version "${ANKI_VERSION:-unknown}" || exit_status=1
  trap - EXIT
  exit "$exit_status"
}
trap cleanup EXIT

section() {
  echo
  echo "==> $*"
}

section "Prepare artifacts"
case "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" in
  ""|"/"|"/e2e"|"/workspace")
    echo "Refusing to clean unsafe E2E artifacts root: ${ANKI_STUDY_REPORT_E2E_ARTIFACTS}" >&2
    exit 1
    ;;
esac
mkdir -p "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"
find "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
mkdir -p \
  "$ANKI_STUDY_REPORT_E2E_RUNTIME_DIR" \
  "$ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR" \
  "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR" \
  "$ANKI_STUDY_REPORT_E2E_HTML_DIR" \
  "$ANKI_STUDY_REPORT_E2E_SCREENSHOTS_DIR" \
  "$ANKI_STUDY_REPORT_E2E_PACKAGE_DIR"

if [ "$ANKI_E2E_RESOURCE_TELEMETRY" = "1" ]; then
  rm -f "$RESOURCE_STOP_FILE"
  /e2e/bin/e2e-telemetry.py sample-resources --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" --stop-file "$RESOURCE_STOP_FILE" --interval 1 &
  RESOURCE_PID=$!
fi

section "Copy workspace to writable build directory"
phase_start
rm -rf "$E2E_BUILD_DIR"
mkdir -p "$E2E_BUILD_DIR"
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.pytest_cache/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.ankiaddon' \
  --exclude 'e2e-artifacts/' \
  --exclude 'web-dashboard/node_modules/' \
  --exclude 'web-dashboard/dist/' \
  --exclude 'anki_study_report/web_dashboard/' \
  --exclude 'anki_study_report/user_files/' \
  "$WORKSPACE/" "$E2E_BUILD_DIR/"
phase_end "workspace copy"

section "Build frontend dashboard"
FRONTEND_DIR="$E2E_BUILD_DIR/web-dashboard"
echo "Workspace build dir: $E2E_BUILD_DIR"
cd "$E2E_BUILD_DIR"
echo "pwd: $(pwd)"
ls -la
ls -la web-dashboard || true
test -f web-dashboard/package.json
"$PNPM_BIN" --version
if [ -f pnpm-workspace.yaml ]; then
  echo "root pnpm-workspace.yaml:"
  sed -n '1,40p' pnpm-workspace.yaml
fi
if [ -f web-dashboard/pnpm-workspace.yaml ]; then
  echo "web-dashboard pnpm-workspace.yaml:"
  sed -n '1,40p' web-dashboard/pnpm-workspace.yaml
  if ! grep -Eq '^[[:space:]]*packages:' web-dashboard/pnpm-workspace.yaml; then
    echo "web-dashboard/pnpm-workspace.yaml must declare packages; expected packages: [\".\"]" >&2
    exit 1
  fi
fi
phase_start
"$PNPM_BIN" --dir "$FRONTEND_DIR" install --offline --frozen-lockfile
phase_end "frontend dependency install" "success" "lockfile-driven offline install from the image pnpm store"
phase_start
"$PNPM_BIN" --dir "$FRONTEND_DIR" run build:addon
phase_end "frontend build"

section "Build and validate add-on archive"
phase_start
cd "$E2E_BUILD_DIR"
python3 scripts/package_addon.py --output "$ANKI_STUDY_REPORT_E2E_PACKAGE_DIR/anki_study_report.ankiaddon" --check
phase_end "add-on package"

section "Create isolated Anki profile and fixture collection"
phase_start
/e2e/bin/create-profile.sh
bootstrap_prefs_args=(
  --base-dir "$ANKI_BASE"
  --profile "$ANKI_PROFILE"
  --profile-dir "$ANKI_PROFILE_DIR"
  --artifacts-dir "$ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR"
)
if [ "${KEEP_E2E_DATA:-0}" != "1" ]; then
  bootstrap_prefs_args+=(--fresh)
fi
/e2e/bin/bootstrap-prefs.py "${bootstrap_prefs_args[@]}"
/e2e/bin/seed-collection.py --profile-dir "$ANKI_PROFILE_DIR" --artifacts-dir "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"
import_apkg_args=(
  --profile-dir "$ANKI_PROFILE_DIR"
  --artifacts-dir "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"
)
if [ "${ANKI_E2E_REQUIRE_APKG_FIXTURE:-0}" = "1" ]; then
  import_apkg_args+=(--require)
fi
/e2e/bin/import-apkg-fixture.py \
  "${import_apkg_args[@]}"
/e2e/bin/mark-apkg-cards-problematic.py \
  --profile-dir "$ANKI_PROFILE_DIR" \
  --artifacts-dir "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"
/e2e/bin/install-addon.sh "$E2E_BUILD_DIR/anki_study_report"
phase_end "fixture and profile preparation"

section "First Anki start"
phase_start
/e2e/bin/start-anki.sh first
phase_end "first Anki start"
phase_start
/e2e/bin/wait-for-dashboard.py --label first
phase_end "first readiness wait"
phase_start
/e2e/bin/smoke-api.py --label first
phase_end "first API smoke"
phase_start
/e2e/bin/smoke-browser.mjs --label first
phase_end "browser serial and parallel capture"

verify_restart="$ANKI_E2E_VERIFY_RESTART"
if [ "$verify_restart" = "auto" ]; then
  [ "$ANKI_E2E_SCOPE" = "full" ] && verify_restart=1 || verify_restart=0
fi
if [ "$verify_restart" = "1" ]; then
  section "Restart Anki"
  phase_start
  /e2e/bin/restart-anki.sh restart
  phase_end "Anki stop and restart"
  phase_start
  /e2e/bin/wait-for-dashboard.py --label restart
  phase_end "restart readiness"
  phase_start
  /e2e/bin/smoke-api.py --label restart
  phase_end "restart API smoke"
else
  echo "Restart smoke skipped for targeted scope=$ANKI_E2E_SCOPE (policy=$ANKI_E2E_VERIFY_RESTART)."
fi

section "E2E completed"
echo "Artifacts: ${ANKI_STUDY_REPORT_E2E_ARTIFACTS}"
run_status="success"
