#!/usr/bin/env bash
set -Eeuo pipefail

EXPECTED_REPOSITORY="AliceLiddell01/anki-study-report"
EXPECTED_BRANCH="c2-manual-acceptance-remediation"
PACKAGE_TESTED_SHA="a162dde223b1bc40b6b0f566ae1fb5d665089359"
PACKAGE_SHA256="e01b9dd3e3277d9ff0cafb9ac3a298a1459118056f07834a171662c91ae79357"
APKG_RELATIVE="docker/anki-e2e/fixtures/real-decks/words-n1.apkg"
APKG_SHA256="78dfab9424fcdb1f5da4005f7e5a2789a04c13414c5477bc647069a06ad10a9b"
REFERENCE_AUDIT_SHA256="e2c1d35bb12088ad0d285371514789637be60025050f5a8ded6307048c6dd2da"
REFERENCE_PROTOTYPE_SHA256="48f3ace56b11f0dd328709923a99bb7277b0747f2cbc489e00dee7821f6bf8f9"
DEFAULT_IMAGE="anki-study-report-e2e:local"
DEFAULT_IMAGE_ID="sha256:2e952fb095fb554b0d4567027a86f475f4d9734892bd10f091a44bdd24ac0c43"

usage() {
  cat <<'EOF'
Usage:
  docker/anki-e2e/run-cards-exact-av-media-host.sh \
    --package /absolute/path/anki_study_report.ankiaddon \
    --reference-audit /absolute/path/cards-visual-parity-and-profiles-audit-evidence.zip \
    --reference-prototype /absolute/path/pr130_visual_prototype_v3_2_3.zip \
    [--output-dir /absolute/new/directory] \
    [--image anki-study-report-e2e:local] \
    [--expected-image-id sha256:...]

The command requires a clean, committed and pushed
c2-manual-acceptance-remediation checkout. It uses only strict Docker --mount
binds and never creates a missing source path.
EOF
}

fail() {
  printf '\nSTOP:\n%s\n' "$1" >&2
  printf '\nПодтверждено:\n%s\n' "${2:-No later gate was started.}" >&2
  printf '\nDiagnostics:\n%s\n' "${3:-not created}" >&2
  printf '\nНужно от владельца:\n%s\n' "${4:-Return the full command output.}" >&2
  exit 2
}

require_file() {
  local path="$1" label="$2"
  [ -e "$path" ] || fail "$label is missing: $path"
  [ -f "$path" ] || fail "$label must be a regular file, found another path type: $path"
  [ ! -L "$path" ] || fail "$label must not be a symbolic link: $path"
}

require_dir() {
  local path="$1" label="$2"
  [ -e "$path" ] || fail "$label is missing: $path"
  [ -d "$path" ] || fail "$label must be a directory, found another path type: $path"
  [ ! -L "$path" ] || fail "$label must not be a symbolic link: $path"
}

verify_sha() {
  local path="$1" expected="$2" label="$3" actual
  actual="$(sha256sum "$path" | awk '{print $1}')"
  if [ "$actual" != "$expected" ]; then
    fail "$label SHA-256 mismatch: expected=$expected actual=$actual path=$path"
  fi
  printf '[ OK ] %-28s %s\n' "$label" "$actual"
}

repo=""
package=""
reference_audit=""
reference_prototype=""
output_dir=""
image="$DEFAULT_IMAGE"
expected_image_id="$DEFAULT_IMAGE_ID"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) repo="${2:-}"; shift 2 ;;
    --package) package="${2:-}"; shift 2 ;;
    --reference-audit) reference_audit="${2:-}"; shift 2 ;;
    --reference-prototype) reference_prototype="${2:-}"; shift 2 ;;
    --output-dir) output_dir="${2:-}"; shift 2 ;;
    --image) image="${2:-}"; shift 2 ;;
    --expected-image-id) expected_image_id="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; fail "Unknown argument: $1" ;;
  esac
done

if [ -z "$repo" ]; then
  repo="$(git rev-parse --show-toplevel 2>/dev/null || true)"
fi
[ -n "$repo" ] || fail "Repository path was not provided and cannot be resolved from the current directory."
repo="$(realpath -e "$repo")"
package="${package:+$(realpath -e "$package" 2>/dev/null || printf '%s' "$package")}"
reference_audit="${reference_audit:+$(realpath -e "$reference_audit" 2>/dev/null || printf '%s' "$reference_audit")}"
reference_prototype="${reference_prototype:+$(realpath -e "$reference_prototype" 2>/dev/null || printf '%s' "$reference_prototype")}"

[ -n "$package" ] || fail "--package is required."
[ -n "$reference_audit" ] || fail "--reference-audit is required."
[ -n "$reference_prototype" ] || fail "--reference-prototype is required."
require_dir "$repo" "repository"
require_file "$package" "exact package"
require_file "$reference_audit" "visual-audit reference ZIP"
require_file "$reference_prototype" "prototype reference ZIP"
require_file "$repo/$APKG_RELATIVE" "committed Words APKG"

cd "$repo"

branch="$(git branch --show-current)"
[ "$branch" = "$EXPECTED_BRANCH" ] || fail \
  "Wrong branch: current=$branch expected=$EXPECTED_BRANCH" \
  "No Docker container was started." \
  "git status --short --branch" \
  "Switch only after preserving unrelated changes."

remote="$(git remote get-url origin)"
case "${remote%.git}" in
  *github.com/AliceLiddell01/anki-study-report|*github.com:AliceLiddell01/anki-study-report) ;;
  *) fail "Wrong repository origin: $remote" ;;
esac

status="$(git status --porcelain=v1)"
[ -z "$status" ] || fail \
  "Working tree is not clean; final E2E requires a committed harness." \
  "$status" \
  "git status --short --branch" \
  "Do not reset/clean blindly. Return the exact dirty set."

head="$(git rev-parse HEAD)"
remote_head="$(git rev-parse "origin/$EXPECTED_BRANCH")"
[ "$head" = "$remote_head" ] || fail \
  "Local and remote branch heads differ: local=$head remote=$remote_head" \
  "No Docker container was started." \
  "git log --oneline --decorate -8" \
  "Push or reconcile the intended harness commit without force-push."

git merge-base --is-ancestor "$PACKAGE_TESTED_SHA" "$head" || fail \
  "Exact package tested commit is not an ancestor of the current harness: package=$PACKAGE_TESTED_SHA harness=$head"

changed_paths_file="$(mktemp)"
reuse_report="$(mktemp)"
temp_root=""
cleanup() {
  set +e
  rm -f "$changed_paths_file" "$reuse_report"
  if [ -n "$temp_root" ] && [ -d "$temp_root" ]; then
    rm -rf "$temp_root" 2>/dev/null
    if [ -d "$temp_root" ] && command -v docker >/dev/null 2>&1; then
      docker run --rm --user 0:0 --entrypoint /bin/sh \
        --mount "type=bind,source=$temp_root,target=/cleanup" \
        "$image" \
        -c 'find /cleanup -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +' \
        >/dev/null 2>&1
      rm -rf "$temp_root" 2>/dev/null
    fi
    if [ -d "$temp_root" ]; then
      printf '[WARN] temporary Docker data could not be removed: %s\n' "$temp_root" >&2
    fi
  fi
}
trap cleanup EXIT

git diff --name-only "$PACKAGE_TESTED_SHA..$head" > "$changed_paths_file"
python3 scripts/validate_e2e_harness_reuse.py \
  --package-tested-sha "$PACKAGE_TESTED_SHA" \
  --harness-sha "$head" \
  --workflow-source-sha "$head" \
  --changed-paths "$changed_paths_file" \
  --output "$reuse_report" ||
  fail \
    "The committed diff is not eligible for exact package harness-only reuse." \
    "$(cat "$changed_paths_file")" \
    "$reuse_report" \
    "Return this output; do not build or substitute a new package."

reuse_mode="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["reuseMode"])' "$reuse_report")"

verify_sha "$package" "$PACKAGE_SHA256" "exact package"
verify_sha "$repo/$APKG_RELATIVE" "$APKG_SHA256" "Words APKG"
verify_sha "$reference_audit" "$REFERENCE_AUDIT_SHA256" "visual-audit ZIP"
verify_sha "$reference_prototype" "$REFERENCE_PROTOTYPE_SHA256" "prototype ZIP"

python3 - "$reference_audit" "$reference_prototype" <<'PY'
import sys, zipfile
for value in sys.argv[1:]:
    with zipfile.ZipFile(value) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise SystemExit(f"ZIP CRC failure: {value} member={bad}")
        unsafe = [
            item.filename for item in archive.infolist()
            if item.filename.startswith("/") or ".." in item.filename.replace("\\", "/").split("/")
        ]
        if unsafe:
            raise SystemExit(f"ZIP unsafe members: {value} {unsafe[:5]}")
        print(f"[ OK ] ZIP CRC/members           {value} members={len(archive.infolist())}")
PY

command -v docker >/dev/null || fail "Docker CLI is not installed."
docker info >/dev/null 2>&1 || fail "Docker daemon is unavailable."
actual_image_id="$(docker image inspect "$image" --format '{{.Id}}' 2>/dev/null || true)"
[ -n "$actual_image_id" ] || fail "Docker image is missing: $image"
if [ -n "$expected_image_id" ] && [ "$actual_image_id" != "$expected_image_id" ]; then
  fail \
    "Docker image identity mismatch: expected=$expected_image_id actual=$actual_image_id image=$image" \
    "No container was started." \
    "docker image inspect $image" \
    "Return this output instead of rebuilding the image blindly."
fi
printf '[ OK ] Docker image identity        %s\n' "$actual_image_id"

if [ -z "$output_dir" ]; then
  output_dir="$HOME/.cache/anki-study-report/manual-gates/$head/cards-final-av-media-final"
fi
case "$output_dir" in
  /*) ;;
  *) output_dir="$repo/$output_dir" ;;
esac
if [ -e "$output_dir" ]; then
  if [ -d "$output_dir" ] && [ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    :
  else
    fail \
      "Output path already exists and is not an empty directory: $output_dir" \
      "No existing artifacts were overwritten." \
      "$output_dir" \
      "Choose a new --output-dir or return its inventory for state-aware handling."
  fi
else
  mkdir -p "$output_dir"
fi
output_dir="$(realpath -e "$output_dir")"
[ -w "$output_dir" ] || fail "Output directory is not writable: $output_dir"

temp_root="$(mktemp -d "${TMPDIR:-/tmp}/asr-cards-exact.XXXXXX")"
input_dir="$temp_root/input"
reference_dir="$temp_root/reference-input"
anki_data="$temp_root/anki-data"
mkdir -p "$input_dir" "$reference_dir" "$anki_data"
install -m 0444 "$package" "$input_dir/anki_study_report.ankiaddon"
install -m 0444 "$reference_audit" "$reference_dir/cards-visual-parity-and-profiles-audit-evidence.zip"
install -m 0444 "$reference_prototype" "$reference_dir/pr130_visual_prototype_v3_2_3.zip"

for path_type in \
  "$repo:directory" \
  "$output_dir:directory" \
  "$input_dir:directory" \
  "$reference_dir:directory" \
  "$anki_data:directory"
do
  path="${path_type%:*}"
  expected="${path_type##*:}"
  if [ "$expected" = "directory" ] && [ ! -d "$path" ]; then
    fail "Mount source is not a directory: $path"
  fi
done

process_log="$output_dir/container.log"
host_uid="$(id -u)"
host_gid="$(id -g)"

printf '\nCards exact AV/media final run\n'
printf 'repository:         %s\n' "$repo"
printf 'package tested SHA: %s\n' "$PACKAGE_TESTED_SHA"
printf 'harness SHA:        %s\n' "$head"
printf 'reuse mode:         %s\n' "$reuse_mode"
printf 'output:             %s\n' "$output_dir"
printf 'image:              %s\n\n' "$actual_image_id"

set +e
docker run --rm --init --shm-size 2g \
  --user 0:0 \
  -e HOME=/e2e/home \
  -e E2E_MODE=standard \
  -e ANKI_E2E_SCOPE=cards-exact-av-media \
  -e ANKI_E2E_SCREENSHOT_WORKERS=1 \
  -e ANKI_E2E_RESOURCE_TELEMETRY=0 \
  -e ANKI_E2E_VERIFY_RESTART=0 \
  -e ANKI_E2E_PACKAGE_SOURCE=fast-ci-artifact \
  -e ANKI_E2E_PREBUILT_ADDON_PATH=/e2e/input/anki_study_report.ankiaddon \
  -e ANKI_E2E_FAST_CI_RUN_ID=30225212079 \
  -e ANKI_E2E_FAST_CI_TESTED_SHA="$PACKAGE_TESTED_SHA" \
  -e ANKI_E2E_FAST_CI_PACKAGE_SHA256="$PACKAGE_SHA256" \
  -e ANKI_E2E_HARNESS_SHA="$head" \
  -e ANKI_E2E_REUSE_MODE="$reuse_mode" \
  -e ANKI_E2E_IMAGE_REFERENCE="$image" \
  -e ANKI_E2E_IMAGE_ID="$actual_image_id" \
  -e ANKI_E2E_HOST_UID="$host_uid" \
  -e ANKI_E2E_HOST_GID="$host_gid" \
  -e ANKI_E2E_EXACT_CARD_ID=1649481469689 \
  -e ANKI_E2E_EXACT_WORD=影 \
  -e ANKI_E2E_EXACT_GIF_NAME=影.gif \
  -e ANKI_E2E_EXACT_GIF_SHA256=4a4d7f3ad02b029e00d96c28a7f1f4af245aab38858b2a00c9681fa0d2667bce \
  -e ANKI_E2E_EXACT_MP3_NAME=影.mp3 \
  -e ANKI_E2E_EXACT_MP3_SHA256=f7ad06083e9911da13af81f52de3282166a666e452b690cebf4c4a0e45ea7dc7 \
  -e ANKI_E2E_EXACT_PNG_NAME=影.png \
  -e ANKI_E2E_EXACT_PNG_SHA256=25cae7e94b0ba6fe12b7ecfea741aefbb2ea901d2b62c693c1cf015283a150e1 \
  -e ANKI_E2E_EXACT_APKG_PATH=/workspace/"$APKG_RELATIVE" \
  -e ANKI_E2E_EXACT_APKG_SHA256="$APKG_SHA256" \
  -e ANKI_E2E_EXACT_THEMES=light,dark \
  -e 'ANKI_E2E_EXACT_VIEWPORTS_JSON={"wide":{"width":1440,"height":900},"drawer":{"width":1024,"height":768},"expanded":{"width":1440,"height":900}}' \
  -e ANKI_E2E_EXACT_REFERENCE_AUDIT_ZIP=/e2e/reference-input/cards-visual-parity-and-profiles-audit-evidence.zip \
  -e ANKI_E2E_EXACT_REFERENCE_AUDIT_SHA256="$REFERENCE_AUDIT_SHA256" \
  -e ANKI_E2E_EXACT_REFERENCE_PROTOTYPE_ZIP=/e2e/reference-input/pr130_visual_prototype_v3_2_3.zip \
  -e ANKI_E2E_EXACT_REFERENCE_PROTOTYPE_SHA256="$REFERENCE_PROTOTYPE_SHA256" \
  --mount "type=bind,source=$repo,target=/workspace,readonly" \
  --mount "type=bind,source=$output_dir,target=/e2e/artifacts" \
  --mount "type=bind,source=$anki_data,target=/e2e/anki-data" \
  --mount "type=bind,source=$input_dir,target=/e2e/input,readonly" \
  --mount "type=bind,source=$reference_dir,target=/e2e/reference-input,readonly" \
  "$image" \
  /e2e/bin/bootstrap-current-harness.sh \
  /e2e/bin/cards-exact-av-media-entrypoint.sh \
  2>&1 | tee "$process_log"
run_status="${PIPESTATUS[0]}"
set -e

if [ "$run_status" -ne 0 ]; then
  token=""
  ready_file="$output_dir/runtime/dashboard-ready.json"
  if [ -f "$ready_file" ]; then
    token="$(python3 - "$ready_file" <<'PY'
import json,sys
try:
    value=json.load(open(sys.argv[1], encoding="utf-8"))
    print(value.get("token",""))
except Exception:
    print("")
PY
)"
  fi
  failure_zip="$output_dir/cards-exact-av-media-failure-${head:0:8}.zip"
  failure_args=(
    --artifacts "$output_dir"
    --process-log "$process_log"
    --output "$failure_zip"
    --home "$HOME"
  )
  if [ -n "$token" ]; then
    failure_args+=(--token "$token")
  fi
  python3 "$repo/docker/anki-e2e/cards-exact-av-media-failure.py" \
    "${failure_args[@]}" || true
  failure_sha="$(sha256sum "$failure_zip" 2>/dev/null | awk '{print $1}')"
  first_problem="$(python3 - "$output_dir" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
for relative in ("reports/failure-summary.json","reports/exact-browser.json","reports/exact-api.json"):
    path=root/relative
    if not path.is_file():
        continue
    try:
        value=json.load(open(path,encoding="utf-8"))
    except Exception:
        continue
    if relative.endswith("failure-summary.json"):
        print(value.get("primary",{}).get("summary") or "canonical E2E failure")
    else:
        failure=value.get("failure")
        if failure:
            print(failure.get("message") or failure)
    break
else:
    print("container process failed; inspect the public-safe diagnostics bundle")
PY
)"
  fail \
    "$first_problem (container exit=$run_status)" \
    "Exact input hashes and strict mount sources passed before the container started." \
    "$failure_zip${failure_sha:+ sha256=$failure_sha}" \
    "Upload the single failure ZIP and this full output. Do not rerun."
fi

final_zip="$output_dir/cards-final-av-media-fidelity-evidence.zip"
self_report="$output_dir/reports/cards-exact-av-media-self-verification.json"
require_file "$final_zip" "final evidence ZIP"
require_file "$self_report" "final self-verification report"
final_status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$self_report")"
[ "$final_status" = "PASS" ] || fail "Final self-verification report is not PASS: $final_status"
final_sha="$(sha256sum "$final_zip" | awk '{print $1}')"
final_size="$(stat -c %s "$final_zip")"

printf '\nCARDS EXACT AV/MEDIA FINAL RUN: PASS\n'
printf 'artifact: %s\n' "$final_zip"
printf 'size:     %s bytes\n' "$final_size"
printf 'sha256:   %s\n' "$final_sha"
printf 'output:   %s\n' "$output_dir"
printf 'Inspection Profiles requests: 0\n'
printf 'Do not start Profiles. Return this full output and the final ZIP.\n'
