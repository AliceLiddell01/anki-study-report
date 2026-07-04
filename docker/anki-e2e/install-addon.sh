#!/usr/bin/env bash
set -Eeuo pipefail

source_dir="${1:-/e2e/workspace-build/anki_study_report}"
: "${ANKI_BASE:=/e2e/anki-data}"
: "${ANKI_PROFILE:=E2E}"
: "${ANKI_PROFILE_DIR:=${ANKI_BASE}/${ANKI_PROFILE}}"

target_dir="${ANKI_BASE}/addons21/anki_study_report_e2e"
legacy_profile_target="${ANKI_PROFILE_DIR}/addons21/anki_study_report_e2e"

if [ ! -d "$source_dir" ]; then
  echo "Add-on source directory not found: ${source_dir}" >&2
  exit 1
fi

rm -rf "$target_dir" "$legacy_profile_target"
mkdir -p "${ANKI_BASE}/addons21"
mkdir -p "$target_dir"

rsync -a --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.pyo' \
  --exclude 'node_modules/' \
  --exclude 'tests/' \
  --exclude 'user_files/' \
  "$source_dir/" "$target_dir/"

echo "Installed unpacked add-on into ${target_dir}"

required_files=(
  "__init__.py"
  "manifest.json"
  "config.json"
  "web_dashboard/index.html"
)
for relative_path in "${required_files[@]}"; do
  if [ ! -f "${target_dir}/${relative_path}" ]; then
    echo "Installed add-on is missing required file: ${relative_path}" >&2
    exit 1
  fi
done

if ! find "${target_dir}/web_dashboard/assets" -maxdepth 1 -type f -name '*.js' | grep -q .; then
  echo "Installed add-on is missing web_dashboard/assets/*.js" >&2
  exit 1
fi
if ! find "${target_dir}/web_dashboard/assets" -maxdepth 1 -type f -name '*.css' | grep -q .; then
  echo "Installed add-on is missing web_dashboard/assets/*.css" >&2
  exit 1
fi

echo "Anki base folder:"
ls -la "$ANKI_BASE"
echo "Base-level add-ons folder:"
ls -la "${ANKI_BASE}/addons21"
echo "Installed add-on files:"
find "$target_dir" -maxdepth 2 -type f | sort | sed -n '1,80p'
