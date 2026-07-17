#!/usr/bin/env bash
set -Eeuo pipefail

readonly SOURCE_DIR="/workspace/docker/anki-e2e"
readonly DESTINATION_DIR="/e2e/bin"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Current E2E harness source is missing: $SOURCE_DIR" >&2
  exit 1
fi
if [ ! -d "$DESTINATION_DIR" ]; then
  echo "E2E harness destination is missing: $DESTINATION_DIR" >&2
  exit 1
fi
if find "$SOURCE_DIR" -maxdepth 1 -type l -print -quit | grep -q .; then
  echo "Symbolic links are not allowed in the current E2E harness source." >&2
  exit 1
fi

staging_dir="$(mktemp -d /e2e/.current-harness.XXXXXX)"
cleanup() {
  rm -rf "$staging_dir"
}
trap cleanup EXIT

mapfile -d '' harness_files < <(
  find "$SOURCE_DIR" -maxdepth 1 -type f \
    \( -name '*.sh' -o -name '*.py' -o -name '*.mjs' \) \
    -print0 | sort -z
)
if [ "${#harness_files[@]}" -eq 0 ]; then
  echo "No allowed current E2E harness files were found." >&2
  exit 1
fi

for source_path in "${harness_files[@]}"; do
  base_name="$(basename "$source_path")"
  target_name="$base_name"
  case "$base_name" in
    smoke-browser.mjs)
      target_name="smoke-browser-core.mjs"
      ;;
    smoke-browser-wrapper.mjs)
      target_name="smoke-browser.mjs"
      ;;
  esac
  tr -d '\r' < "$source_path" > "$staging_dir/$target_name"
  chmod 0755 "$staging_dir/$target_name"
done

required_files=(
  entrypoint.sh
  run-e2e.sh
  start-anki.sh
  stop-anki.sh
  restart-anki.sh
  smoke-browser-core.mjs
  smoke-browser.mjs
)
for required_file in "${required_files[@]}"; do
  if [ ! -f "$staging_dir/$required_file" ]; then
    echo "Required current E2E harness file is missing: $required_file" >&2
    exit 1
  fi
done

for staged_path in "$staging_dir"/*; do
  install -m 0755 "$staged_path" "$DESTINATION_DIR/$(basename "$staged_path")"
done

if [ "$#" -eq 0 ]; then
  set -- /e2e/bin/run-e2e.sh
fi
exec /e2e/bin/entrypoint.sh "$@"
