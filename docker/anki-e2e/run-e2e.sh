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
: "${PNPM_STORE_DIR:=/e2e/pnpm-store}"
: "${E2E_MODE:=standard}"
: "${ANKI_E2E_SCOPE:=full}"
: "${ANKI_E2E_SCREENSHOT_WORKERS:=3}"
: "${ANKI_E2E_RESOURCE_TELEMETRY:=1}"
: "${ANKI_E2E_VERIFY_RESTART:=auto}"
: "${ANKI_E2E_PREBUILT_ADDON_PATH:=}"
: "${ANKI_E2E_PACKAGE_SOURCE:=source-build}"
: "${ANKI_E2E_FAST_CI_RUN_ID:=}"
: "${ANKI_E2E_FAST_CI_TESTED_SHA:=}"
: "${ANKI_E2E_FAST_CI_PACKAGE_SHA256:=}"

case "$E2E_MODE" in standard|strict-apkg|perf100) ;; *) echo "Unsupported E2E mode: $E2E_MODE" >&2; exit 2;; esac
if [ "$E2E_MODE" = "strict-apkg" ]; then
  echo "[real-decks] strict-apkg compatibility mode maps to standard; real packages are mandatory in every run."
  E2E_MODE=standard
fi

export ANKI_BASE ANKI_PROFILE ANKI_PROFILE_DIR ANKI_STUDY_REPORT_E2E_ARTIFACTS
export ANKI_STUDY_REPORT_E2E_RUNTIME_DIR ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR ANKI_STUDY_REPORT_E2E_REPORTS_DIR
export ANKI_STUDY_REPORT_E2E_HTML_DIR ANKI_STUDY_REPORT_E2E_SCREENSHOTS_DIR ANKI_STUDY_REPORT_E2E_PACKAGE_DIR
export ANKI_STUDY_REPORT_E2E_READY_FILE ANKI_STUDY_REPORT_E2E
export E2E_MODE ANKI_E2E_SCOPE ANKI_E2E_SCREENSHOT_WORKERS ANKI_E2E_RESOURCE_TELEMETRY ANKI_E2E_VERIFY_RESTART
export ANKI_E2E_PACKAGE_SOURCE ANKI_E2E_FAST_CI_RUN_ID ANKI_E2E_FAST_CI_TESTED_SHA ANKI_E2E_FAST_CI_PACKAGE_SHA256
ANKI_STUDY_REPORT_E2E=1

case "$ANKI_E2E_SCOPE" in full|global|stats|decks|activity|cards|settings|notifications) ;; *) echo "Unsupported E2E scope: $ANKI_E2E_SCOPE" >&2; exit 2;; esac
case "$ANKI_E2E_SCREENSHOT_WORKERS" in 1|2|3|4) ;; *) echo "Screenshot workers must be 1..4: $ANKI_E2E_SCREENSHOT_WORKERS" >&2; exit 2;; esac
case "$ANKI_E2E_RESOURCE_TELEMETRY" in 0|1) ;; *) echo "Resource telemetry must be 0 or 1" >&2; exit 2;; esac
case "$ANKI_E2E_VERIFY_RESTART" in auto|0|1) ;; *) echo "Restart policy must be auto, 0, or 1" >&2; exit 2;; esac
case "$ANKI_E2E_PACKAGE_SOURCE" in source-build|fast-ci-artifact|release-artifact) ;; *) echo "Unsupported package source: $ANKI_E2E_PACKAGE_SOURCE" >&2; exit 2;; esac
if [ -n "$ANKI_E2E_PREBUILT_ADDON_PATH" ] && [ "$ANKI_E2E_PACKAGE_SOURCE" = "source-build" ]; then
  echo "A prebuilt add-on path requires fast-ci-artifact or release-artifact package source." >&2
  exit 2
fi
if [ -z "$ANKI_E2E_PREBUILT_ADDON_PATH" ] && [ "$ANKI_E2E_PACKAGE_SOURCE" != "source-build" ]; then
  echo "Package source $ANKI_E2E_PACKAGE_SOURCE requires a prebuilt add-on path." >&2
  exit 2
fi
if [ "$E2E_MODE" = "perf100" ]; then
  export ANKI_E2E_PERF100=1
fi

TOTAL_STARTED_MS=$(date +%s%3N)
TOTAL_STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
RESOURCE_STOP_FILE="${ANKI_STUDY_REPORT_E2E_RUNTIME_DIR}/resource-sampler.stop"
RESOURCE_PID=""
TELEMETRY_FAKE_PID=""
RUN_EVENTS_PATH="${ANKI_STUDY_REPORT_E2E_REPORTS_DIR}/run-events.jsonl"
RUN_EVENTS_INITIALIZED=0
ACTIVE_PHASE_ID=""
ACTIVE_PHASE_NAME=""
ACTIVE_PHASE_STARTED_MS=""
ACTIVE_PHASE_STARTED_AT=""
run_status="failed"

section() {
  echo
  echo "==> $*"
}

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

run_event() {
  /e2e/bin/run_event_protocol.py "$@" --output "$RUN_EVENTS_PATH" --producer docker-e2e
}

phase_start() {
  ACTIVE_PHASE_ID="$1"
  ACTIVE_PHASE_NAME="$2"
  ACTIVE_PHASE_STARTED_MS=$(date +%s%3N)
  ACTIVE_PHASE_STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)
  run_event emit --phase-id "$ACTIVE_PHASE_ID" --event-kind phase --status start
}

phase_end() {
  local status="${1:-success}" notes="${2:-}"
  local finished_ms duration_ms event_status
  finished_ms=$(date +%s%3N)
  duration_ms=$((finished_ms - ACTIVE_PHASE_STARTED_MS))
  record_phase "$ACTIVE_PHASE_NAME" "$ACTIVE_PHASE_STARTED_MS" "$ACTIVE_PHASE_STARTED_AT" "$status" "$notes"
  case "$status" in
    success) event_status=pass ;;
    skipped) event_status=skip ;;
    *) event_status=fail ;;
  esac
  run_event emit --phase-id "$ACTIVE_PHASE_ID" --event-kind phase --status "$event_status" --duration-ms "$duration_ms"
  ACTIVE_PHASE_ID=""
  ACTIVE_PHASE_NAME=""
  ACTIVE_PHASE_STARTED_MS=""
  ACTIVE_PHASE_STARTED_AT=""
}

cleanup() {
  local exit_status=$?
  /e2e/bin/stop-anki.sh || true
  if [ -n "$TELEMETRY_FAKE_PID" ]; then
    kill "$TELEMETRY_FAKE_PID" >/dev/null 2>&1 || true
    wait "$TELEMETRY_FAKE_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$RESOURCE_PID" ]; then
    touch "$RESOURCE_STOP_FILE"
    wait "$RESOURCE_PID" || true
    rm -f "$RESOURCE_STOP_FILE"
  fi
  if [ "$RUN_EVENTS_INITIALIZED" = "1" ] && [ -n "$ACTIVE_PHASE_ID" ]; then
    local failed_finished_ms failed_duration_ms
    failed_finished_ms=$(date +%s%3N)
    failed_duration_ms=$((failed_finished_ms - ACTIVE_PHASE_STARTED_MS))
    record_phase "$ACTIVE_PHASE_NAME" "$ACTIVE_PHASE_STARTED_MS" "$ACTIVE_PHASE_STARTED_AT" "failed" || true
    run_event emit --phase-id "$ACTIVE_PHASE_ID" --event-kind phase --status fail --duration-ms "$failed_duration_ms" --message "phase command failed" || true
    ACTIVE_PHASE_ID=""
  fi
  record_phase "total canonical E2E" "$TOTAL_STARTED_MS" "$TOTAL_STARTED_AT" "$([ "$exit_status" -eq 0 ] && echo success || echo failed)" || true
  /e2e/bin/e2e-telemetry.py finalize --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --scope "$ANKI_E2E_SCOPE" --mode "$E2E_MODE" --workers "$ANKI_E2E_SCREENSHOT_WORKERS" \
    $([ "$ANKI_E2E_RESOURCE_TELEMETRY" = "1" ] && echo --resource-telemetry) || true

  if [ "$RUN_EVENTS_INITIALIZED" = "1" ]; then
    phase_start "artifact-manifest" "manifest generation and validation"
  fi
  if ! /e2e/bin/write-artifact-manifest.py \
    --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --status "$run_status" \
    --anki-version "${ANKI_VERSION:-unknown}"; then
    echo "E2E artifact manifest generation or validation failed." >&2
    if [ "$RUN_EVENTS_INITIALIZED" = "1" ]; then
      phase_end "failed" || true
    fi
    if [ "$exit_status" -eq 0 ]; then
      exit_status=1
    fi
  elif [ "$RUN_EVENTS_INITIALIZED" = "1" ]; then
    phase_end "success" || exit_status=1
  fi

  /e2e/bin/e2e-telemetry.py finalize --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --scope "$ANKI_E2E_SCOPE" --mode "$E2E_MODE" --workers "$ANKI_E2E_SCREENSHOT_WORKERS" \
    $([ "$ANKI_E2E_RESOURCE_TELEMETRY" = "1" ] && echo --resource-telemetry) || true

  if [ "$RUN_EVENTS_INITIALIZED" = "1" ]; then
    local final_status final_duration_ms
    final_duration_ms="$(($(date +%s%3N) - TOTAL_STARTED_MS))"
    if [ "$exit_status" -eq 0 ] && [ "$run_status" = "success" ]; then
      final_status=pass
    else
      final_status=fail
    fi
    run_event finish-run --status "$final_status" --duration-ms "$final_duration_ms" || exit_status=1
    /e2e/bin/run_event_protocol.py validate --output "$RUN_EVENTS_PATH" --producer docker-e2e || exit_status=1
  fi

  /e2e/bin/write-artifact-manifest.py \
    --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --status "$run_status" \
    --anki-version "${ANKI_VERSION:-unknown}" || exit_status=1
  trap - EXIT
  exit "$exit_status"
}
trap cleanup EXIT

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
run_event initialize --message "mode=$E2E_MODE scope=$ANKI_E2E_SCOPE"
RUN_EVENTS_INITIALIZED=1

if [ -n "${ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT:-}" ]; then
  /e2e/bin/fake-telemetry-server.py \
    --summary "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR/telemetry-fake-summary.json" \
    >"$ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR/telemetry-fake.log" 2>&1 &
  TELEMETRY_FAKE_PID=$!
  for _ in $(seq 1 50); do
    if python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8788/__e2e/state", timeout=1).read()' >/dev/null 2>&1; then
      break
    fi
    sleep 0.1
  done
  kill -0 "$TELEMETRY_FAKE_PID"
fi

if [ "$ANKI_E2E_RESOURCE_TELEMETRY" = "1" ]; then
  rm -f "$RESOURCE_STOP_FILE"
  /e2e/bin/e2e-telemetry.py sample-resources --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" --stop-file "$RESOURCE_STOP_FILE" --interval 1 &
  RESOURCE_PID=$!
fi

section "Copy workspace to writable build directory"
phase_start "workspace-copy" "workspace copy"
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
phase_end

FRONTEND_DIR="$E2E_BUILD_DIR/web-dashboard"
echo "Workspace build dir: $E2E_BUILD_DIR"
cd "$E2E_BUILD_DIR"
echo "pwd: $(pwd)"
ls -la
ls -la web-dashboard || true
test -f web-dashboard/package.json
ADDON_INSTALL_SOURCE="$E2E_BUILD_DIR/anki_study_report"

if [ -n "$ANKI_E2E_PREBUILT_ADDON_PATH" ]; then
  section "Validate exact prebuilt add-on artifact"
  test -f "$ANKI_E2E_PREBUILT_ADDON_PATH"
  phase_start "exact-package-validation" "exact prebuilt add-on validation and extraction"
  python3 scripts/package_addon.py --output "$ANKI_E2E_PREBUILT_ADDON_PATH" --check-only
  cp "$ANKI_E2E_PREBUILT_ADDON_PATH" "$ANKI_STUDY_REPORT_E2E_PACKAGE_DIR/anki_study_report.ankiaddon"
  PREBUILT_ADDON_DIR="$E2E_BUILD_DIR/prebuilt-addon"
  rm -rf "$PREBUILT_ADDON_DIR"
  mkdir -p "$PREBUILT_ADDON_DIR"
  python3 -m zipfile -e "$ANKI_E2E_PREBUILT_ADDON_PATH" "$PREBUILT_ADDON_DIR"
  ADDON_INSTALL_SOURCE="$PREBUILT_ADDON_DIR"
  phase_end "success" "packageSource=$ANKI_E2E_PACKAGE_SOURCE"
else
  section "Build frontend dashboard"
  "$PNPM_BIN" --version
  if [ -f pnpm-workspace.yaml ]; then
    echo "root pnpm-workspace.yaml:"
    sed -n '1,40p' pnpm-workspace.yaml
  fi
  if [ -f web-dashboard/pnpm-workspace.yaml ]; then
    echo "web-dashboard/pnpm-workspace.yaml:"
    sed -n '1,40p' web-dashboard/pnpm-workspace.yaml
    if ! grep -Eq '^[[:space:]]*packages:' web-dashboard/pnpm-workspace.yaml; then
      echo 'web-dashboard/pnpm-workspace.yaml must declare packages; expected packages: ["."]' >&2
      exit 1
    fi
  fi
  phase_start "frontend-dependency-install" "frontend dependency install"
  "$PNPM_BIN" --store-dir "$PNPM_STORE_DIR" --dir "$FRONTEND_DIR" install --offline --frozen-lockfile
  phase_end "success" "lockfile-driven offline install from the image pnpm store"
  phase_start "frontend-build" "frontend build"
  "$PNPM_BIN" --dir "$FRONTEND_DIR" run build:addon
  phase_end

  section "Build and validate add-on archive"
  phase_start "addon-package" "add-on package"
  cd "$E2E_BUILD_DIR"
  python3 scripts/package_addon.py --output "$ANKI_STUDY_REPORT_E2E_PACKAGE_DIR/anki_study_report.ankiaddon" --check
  phase_end
fi

section "Create isolated Anki profile"
phase_start "profile-bootstrap" "profile bootstrap"
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
phase_end

section "Create empty collection"
phase_start "collection-bootstrap" "empty collection bootstrap"
/e2e/bin/seed-collection.py \
  --profile-dir "$ANKI_PROFILE_DIR" \
  --artifacts-dir "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"
phase_end

section "Validate and import committed real decks"
phase_start "real-deck-import" "real deck checksum import inventory and anchors"
/e2e/bin/import-apkg-fixture.py \
  --profile-dir "$ANKI_PROFILE_DIR" \
  --artifacts-dir "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"
phase_end

section "Apply deterministic real-card scenarios"
phase_start "scenario-preparation" "real card scenario preparation"
/e2e/bin/mark-apkg-cards-problematic.py \
  --profile-dir "$ANKI_PROFILE_DIR" \
  --artifacts-dir "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"
phase_end

section "Install add-on and optional non-collection fixtures"
phase_start "addon-install" "add-on install and auxiliary profile preparation"
/e2e/bin/install-addon.sh "$ADDON_INSTALL_SOURCE"
if [ "$ANKI_E2E_SCOPE" = "full" ] || [ "$ANKI_E2E_SCOPE" = "notifications" ]; then
  /e2e/bin/seed-notification-lifecycle.py \
    --addon-dir "${ANKI_BASE}/addons21/anki_study_report_e2e" \
    --profile-dir "$ANKI_PROFILE_DIR" \
    --artifacts-dir "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR"
fi
phase_end

section "First Anki start"
phase_start "anki-start-first" "first Anki start"
/e2e/bin/start-anki.sh first
phase_end
phase_start "dashboard-ready-first" "first readiness wait"
/e2e/bin/wait-for-dashboard.py --label first
phase_end
phase_start "api-smoke-first" "first API smoke"
/e2e/bin/smoke-api.py --label first
phase_end
phase_start "browser-smoke-first" "browser real-deck and dashboard capture"
/e2e/bin/smoke-browser.mjs --label first
phase_end

verify_restart="$ANKI_E2E_VERIFY_RESTART"
if [ "$verify_restart" = "auto" ]; then
  [ "$ANKI_E2E_SCOPE" = "full" ] && verify_restart=1 || verify_restart=0
fi
if [ "$verify_restart" = "1" ]; then
  section "Restart Anki"
  phase_start "anki-restart" "Anki stop and restart"
  /e2e/bin/restart-anki.sh restart
  phase_end
  phase_start "dashboard-ready-restart" "restart readiness"
  /e2e/bin/wait-for-dashboard.py --label restart
  phase_end
  phase_start "api-smoke-restart" "restart API smoke"
  /e2e/bin/smoke-api.py --label restart
  phase_end
  if [ -n "${ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT:-}" ]; then
    phase_start "telemetry-restart" "telemetry restart persistence and deletion"
    /e2e/bin/verify-telemetry-restart.py \
      --ready "$ANKI_STUDY_REPORT_E2E_READY_FILE" \
      --fake-endpoint "$ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT" \
      --output "$ANKI_STUDY_REPORT_E2E_REPORTS_DIR/telemetry-restart-proof.json"
    phase_end
  fi
else
  echo "Restart smoke skipped for targeted scope=$ANKI_E2E_SCOPE (policy=$ANKI_E2E_VERIFY_RESTART)."
fi

section "E2E completed"
echo "Artifacts: ${ANKI_STUDY_REPORT_E2E_ARTIFACTS}"
run_status="success"
