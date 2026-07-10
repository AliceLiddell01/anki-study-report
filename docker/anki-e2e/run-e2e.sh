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

export ANKI_BASE ANKI_PROFILE ANKI_PROFILE_DIR ANKI_STUDY_REPORT_E2E_ARTIFACTS
export ANKI_STUDY_REPORT_E2E_RUNTIME_DIR ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR ANKI_STUDY_REPORT_E2E_REPORTS_DIR
export ANKI_STUDY_REPORT_E2E_HTML_DIR ANKI_STUDY_REPORT_E2E_SCREENSHOTS_DIR ANKI_STUDY_REPORT_E2E_PACKAGE_DIR
export ANKI_STUDY_REPORT_E2E_READY_FILE
export ANKI_STUDY_REPORT_E2E=1

run_status="failed"
cleanup() {
  local exit_status=$?
  /e2e/bin/stop-anki.sh || true
  if ! /e2e/bin/write-artifact-manifest.py \
    --root "$ANKI_STUDY_REPORT_E2E_ARTIFACTS" \
    --status "$run_status" \
    --anki-version "${ANKI_VERSION:-unknown}"; then
    echo "E2E artifact manifest generation or validation failed." >&2
    if [ "$exit_status" -eq 0 ]; then
      exit_status=1
    fi
  fi
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

section "Copy workspace to writable build directory"
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
"$PNPM_BIN" --dir "$FRONTEND_DIR" install --frozen-lockfile
"$PNPM_BIN" --dir "$FRONTEND_DIR" run build:addon

section "Build and validate add-on archive"
cd "$E2E_BUILD_DIR"
python3 scripts/package_addon.py --output "$ANKI_STUDY_REPORT_E2E_PACKAGE_DIR/anki_study_report.ankiaddon" --check

section "Create isolated Anki profile and fixture collection"
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

section "First Anki start"
/e2e/bin/start-anki.sh first
/e2e/bin/wait-for-dashboard.py --label first
/e2e/bin/smoke-api.py --label first
/e2e/bin/smoke-browser.mjs --label first

section "Restart Anki"
/e2e/bin/restart-anki.sh restart
/e2e/bin/wait-for-dashboard.py --label restart
/e2e/bin/smoke-api.py --label restart

section "E2E completed"
echo "Artifacts: ${ANKI_STUDY_REPORT_E2E_ARTIFACTS}"
run_status="success"
