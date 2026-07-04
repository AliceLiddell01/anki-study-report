#!/usr/bin/env bash
set -Eeuo pipefail

: "${WORKSPACE:=/workspace}"
: "${E2E_BUILD_DIR:=/e2e/workspace-build}"
: "${ANKI_BASE:=/e2e/anki-data}"
: "${ANKI_PROFILE:=E2E}"
: "${ANKI_PROFILE_DIR:=${ANKI_BASE}/${ANKI_PROFILE}}"
: "${ANKI_STUDY_REPORT_E2E_ARTIFACTS:=/e2e/artifacts}"
: "${ANKI_STUDY_REPORT_E2E_READY_FILE:=${ANKI_STUDY_REPORT_E2E_ARTIFACTS}/dashboard-ready.json}"
: "${PNPM_BIN:=/e2e/node_modules/.bin/pnpm}"

export ANKI_BASE ANKI_PROFILE ANKI_PROFILE_DIR ANKI_STUDY_REPORT_E2E_ARTIFACTS ANKI_STUDY_REPORT_E2E_READY_FILE
export ANKI_STUDY_REPORT_E2E=1

cleanup() {
  /e2e/bin/stop-anki.sh || true
}
trap cleanup EXIT

section() {
  echo
  echo "==> $*"
}

section "Prepare artifacts"
mkdir -p "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"
rm -f "$ANKI_STUDY_REPORT_E2E_READY_FILE" \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/api-*.json \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/cards-*.png \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/cards-*.html \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/anki-stdout-*.log \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/anki-stderr-*.log \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/addon-e2e-events.jsonl \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/prefs21-summary.txt \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/anki-data-tree.txt \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/addons-tree.txt \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"/anki-startup-tail.txt
ln -sf anki_study_report.log "$ANKI_STUDY_REPORT_E2E_ARTIFACTS/anki-study-report.log" || true

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
    echo "Adding E2E-local packages entry to copied web-dashboard/pnpm-workspace.yaml"
    cp web-dashboard/pnpm-workspace.yaml web-dashboard/pnpm-workspace.e2e-original.yaml
    {
      printf '%s\n' 'packages:' '  - "."'
      cat web-dashboard/pnpm-workspace.e2e-original.yaml
    } > web-dashboard/pnpm-workspace.yaml
  fi
fi
"$PNPM_BIN" --dir "$FRONTEND_DIR" install --frozen-lockfile
"$PNPM_BIN" --dir "$FRONTEND_DIR" run build:addon

section "Build and validate add-on archive"
cd "$E2E_BUILD_DIR"
python3 scripts/package_addon.py --output "$ANKI_STUDY_REPORT_E2E_ARTIFACTS/anki_study_report.ankiaddon" --check

section "Create isolated Anki profile and fixture collection"
/e2e/bin/create-profile.sh
bootstrap_prefs_args=(
  --base-dir "$ANKI_BASE"
  --profile "$ANKI_PROFILE"
  --profile-dir "$ANKI_PROFILE_DIR"
  --artifacts-dir "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"
)
if [ "${KEEP_E2E_DATA:-0}" != "1" ]; then
  bootstrap_prefs_args+=(--fresh)
fi
/e2e/bin/bootstrap-prefs.py "${bootstrap_prefs_args[@]}"
/e2e/bin/seed-collection.py --profile-dir "$ANKI_PROFILE_DIR" --artifacts-dir "$ANKI_STUDY_REPORT_E2E_ARTIFACTS"
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

cp -f "$ANKI_STUDY_REPORT_E2E_ARTIFACTS/anki_study_report.log" \
  "$ANKI_STUDY_REPORT_E2E_ARTIFACTS/anki-study-report.log" 2>/dev/null || true

section "E2E completed"
echo "Artifacts: ${ANKI_STUDY_REPORT_E2E_ARTIFACTS}"
