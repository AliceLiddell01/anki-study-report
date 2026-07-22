#!/usr/bin/env bash
set -u
set -o pipefail

EXPECTED_REPOSITORY="AliceLiddell01/anki-study-report"
EXPECTED_BASE="origin/core"
DO_FETCH=0
OFFLINE=0
REQUIRE_CLEAN=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/codex-environment-preflight.sh [options]

Options:
  --expected-base <ref>  Base ref that must resolve (default: origin/core)
  --fetch                Run git fetch origin --prune before freshness checks
  --offline              Forbid network calls; use existing refs only
  --require-clean        Block on tracked or untracked working-tree changes
  -h, --help             Show this help

Exit codes:
  0  PASS
  2  Environment, path, tool, or Git configuration blocker
  3  GitHub authentication or fetch blocker
  4  Repository identity, expected-base, or dirty-state blocker
USAGE
}

while (($#)); do
  case "$1" in
    --expected-base)
      [[ $# -ge 2 ]] || { echo "--expected-base requires a value" >&2; exit 2; }
      EXPECTED_BASE="$2"
      shift 2
      ;;
    --fetch)
      DO_FETCH=1
      shift
      ;;
    --offline)
      OFFLINE=1
      shift
      ;;
    --require-clean)
      REQUIRE_CLEAN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ((DO_FETCH && OFFLINE)); then
  echo "--fetch and --offline are mutually exclusive" >&2
  exit 2
fi

SOURCE_TREE="${CODEX_SOURCE_TREE_PATH:-}"
WORKTREE="${CODEX_WORKTREE_PATH:-}"
SOURCE_REAL="NOT_CHECKED"
WORKTREE_REAL="NOT_CHECKED"
FILESYSTEM="NOT_CHECKED"
REPOSITORY="NOT_CHECKED"
ORIGIN_PROTOCOL="NOT_CHECKED"
ORIGIN_SAFE="NOT_CHECKED"
EXPECTED_BASE_SHA="NOT_CHECKED"
GIT_FETCH="OFFLINE"
DIRTY_STATE="NOT_CHECKED"
LOCAL_CORE="NOT_CHECKED"
PROJECT_PYTHON="NOT_READY"
BLOCKER=""

declare -A TOOL_PATHS=()
declare -A TOOL_VERSIONS=()
declare -a WARNINGS=()

safe_line() {
  local value="$1"
  value="${value//$'\n'/ }"
  value="${value//$'\r'/ }"
  printf '%s' "$value"
}

print_summary() {
  local status="$1"
  echo "Codex environment preflight: $status"
  echo "source_tree: $(safe_line "$SOURCE_REAL")"
  echo "worktree: $(safe_line "$WORKTREE_REAL")"
  echo "filesystem: $(safe_line "$FILESYSTEM")"
  echo "repository: $(safe_line "$REPOSITORY")"
  echo "origin_protocol: $(safe_line "$ORIGIN_PROTOCOL")"
  echo "origin: $(safe_line "$ORIGIN_SAFE")"
  echo "expected_base: $(safe_line "$EXPECTED_BASE")"
  echo "expected_base_sha: $(safe_line "$EXPECTED_BASE_SHA")"
  echo "git: $(safe_line "${TOOL_PATHS[git]:-NOT_CHECKED} ${TOOL_VERSIONS[git]:-}")"
  echo "node: $(safe_line "${TOOL_PATHS[node]:-NOT_CHECKED} ${TOOL_VERSIONS[node]:-}")"
  echo "pnpm: $(safe_line "${TOOL_PATHS[pnpm]:-NOT_CHECKED} ${TOOL_VERSIONS[pnpm]:-}")"
  echo "uv: $(safe_line "${TOOL_PATHS[uv]:-NOT_CHECKED} ${TOOL_VERSIONS[uv]:-}")"
  echo "docker: $(safe_line "${TOOL_PATHS[docker]:-UNAVAILABLE} ${TOOL_VERSIONS[docker]:-}")"
  echo "pwsh: $(safe_line "${TOOL_PATHS[pwsh]:-UNAVAILABLE} ${TOOL_VERSIONS[pwsh]:-}")"
  echo "project_python: $(safe_line "$PROJECT_PYTHON")"
  echo "git_fetch: $(safe_line "$GIT_FETCH")"
  echo "local_core: $(safe_line "$LOCAL_CORE")"
  echo "dirty_state: $(safe_line "$DIRTY_STATE")"
  if [[ -n "$BLOCKER" ]]; then
    echo "blocker: $(safe_line "$BLOCKER")"
  fi
  echo "warnings:"
  if ((${#WARNINGS[@]} == 0)); then
    echo "- none"
  else
    local warning
    for warning in "${WARNINGS[@]}"; do
      echo "- $(safe_line "$warning")"
    done
  fi
}

die() {
  local code="$1"
  shift
  BLOCKER="$*"
  print_summary "BLOCKED"
  exit "$code"
}

is_windows_path_text() {
  local value="$1"
  [[ "$value" =~ (^|[[:space:]\"\'])([A-Za-z]:[\\/]|/mnt/[A-Za-z]/) ]] ||
    [[ "$value" =~ \.(exe|cmd|bat)([[:space:]\"\']|$) ]]
}

resolve_path() {
  local label="$1"
  local raw="$2"
  local output_var="$3"
  [[ -n "$raw" ]] || die 2 "$label is not set"
  [[ "$raw" == /* ]] || die 2 "$label must be an absolute Linux path"
  is_windows_path_text "$raw" && die 2 "$label contains a Windows or mounted-drive path: $raw"

  local resolved
  resolved="$(realpath -m -- "$raw" 2>/dev/null)" || die 2 "$label cannot be resolved: $raw"
  case "$resolved" in
    /home/*) ;;
    *) die 2 "$label must resolve under /home, got: $resolved" ;;
  esac
  [[ -d "$resolved" ]] || die 2 "$label does not exist or is not a directory: $resolved"
  printf -v "$output_var" '%s' "$resolved"
}

validate_tool_path() {
  local name="$1"
  local path="$2"
  [[ "$path" == /* ]] || die 2 "$name did not resolve to an absolute executable path: $path"
  is_windows_path_text "$path" && die 2 "$name resolves to a Windows executable or mounted-drive path: $path"
}

resolve_tool() {
  local name="$1"
  local required="$2"
  local path
  path="$(type -P "$name" 2>/dev/null || true)"
  if [[ -z "$path" ]]; then
    if [[ "$required" == "required" ]]; then
      die 2 "required tool is unavailable: $name"
    fi
    WARNINGS+=("optional tool is unavailable: $name")
    return 0
  fi
  local resolved
  resolved="$(realpath -e -- "$path" 2>/dev/null || true)"
  [[ -n "$resolved" ]] || die 2 "$name executable cannot be resolved: $path"
  validate_tool_path "$name" "$resolved"
  TOOL_PATHS["$name"]="$resolved"
}

redact_remote() {
  local url="$1"
  if [[ "$url" =~ ^https?://[^/@]+@ ]]; then
    url="$(printf '%s' "$url" | sed -E 's#^(https?://)[^/@]+@#\1***@#')"
  fi
  printf '%s' "$url"
}

normalize_repository() {
  local url="$1"
  url="${url%.git}"
  case "$url" in
    https://github.com/*|http://github.com/*)
      url="${url#*://github.com/}"
      ;;
    https://*@github.com/*|http://*@github.com/*)
      url="${url#*@github.com/}"
      ;;
    git@github.com:*)
      url="${url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      url="${url#ssh://git@github.com/}"
      ;;
    *)
      return 1
      ;;
  esac
  [[ "$url" =~ ^[^/]+/[^/]+$ ]] || return 1
  printf '%s' "$url"
}

remote_protocol() {
  local url="$1"
  case "$url" in
    https://*|http://*) echo "https" ;;
    git@*|ssh://*) echo "ssh" ;;
    *) echo "unknown" ;;
  esac
}

contains_windows_override() {
  local text="$1"
  [[ -n "$text" ]] && is_windows_path_text "$text"
}

read_engine() {
  local key="$1"
  local file="$2"
  grep -oE "\"${key}\"[[:space:]]*:[[:space:]]*\"[^\"]+\"" "$file" \
    | head -n 1 \
    | sed -E 's/^[^:]+:[[:space:]]*"([^"]+)"$/\1/'
}

major_version() {
  local version="$1"
  version="${version#v}"
  version="${version%%[^0-9.]*}"
  printf '%s' "${version%%.*}"
}

check_major_engine() {
  local tool="$1"
  local actual="$2"
  local engine="$3"
  local major min max exact
  major="$(major_version "$actual")"
  [[ "$major" =~ ^[0-9]+$ ]] || die 2 "could not parse $tool version: $actual"

  if [[ "$engine" =~ ^([0-9]+)\.x$ ]]; then
    exact="${BASH_REMATCH[1]}"
    ((major == exact)) || die 2 "$tool $actual does not satisfy repository engine $engine"
    return
  fi

  min="$(printf '%s' "$engine" | grep -oE '>=[[:space:]]*[0-9]+' | head -n 1 | grep -oE '[0-9]+' || true)"
  max="$(printf '%s' "$engine" | grep -oE '<[[:space:]]*[0-9]+' | head -n 1 | grep -oE '[0-9]+' || true)"
  if [[ -n "$min" ]] && ((major < min)); then
    die 2 "$tool $actual does not satisfy repository engine $engine"
  fi
  if [[ -n "$max" ]] && ((major >= max)); then
    die 2 "$tool $actual does not satisfy repository engine $engine"
  fi
}

[[ "$(uname -s 2>/dev/null || true)" == "Linux" ]] || die 2 "Codex preflight requires Linux"

resolve_path CODEX_SOURCE_TREE_PATH "$SOURCE_TREE" SOURCE_REAL
resolve_path CODEX_WORKTREE_PATH "$WORKTREE" WORKTREE_REAL
FILESYSTEM="native-linux"

resolve_tool git required
TOOL_VERSIONS[git]="$(${TOOL_PATHS[git]} --version 2>/dev/null || true)"

CURRENT_ROOT="$(${TOOL_PATHS[git]} rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$CURRENT_ROOT" ]] || die 4 "current directory is not inside a Git worktree"
CURRENT_ROOT="$(realpath -e -- "$CURRENT_ROOT" 2>/dev/null || true)"
[[ "$CURRENT_ROOT" == "$WORKTREE_REAL" ]] || die 4 "current Git root differs from CODEX_WORKTREE_PATH: $CURRENT_ROOT"

SOURCE_ROOT="$(${TOOL_PATHS[git]} -C "$SOURCE_REAL" rev-parse --show-toplevel 2>/dev/null || true)"
WORKTREE_ROOT="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$SOURCE_ROOT" && -n "$WORKTREE_ROOT" ]] || die 4 "source tree or worktree is not a Git repository"
SOURCE_ROOT="$(realpath -e -- "$SOURCE_ROOT" 2>/dev/null || true)"
WORKTREE_ROOT="$(realpath -e -- "$WORKTREE_ROOT" 2>/dev/null || true)"
[[ "$SOURCE_ROOT" == "$SOURCE_REAL" ]] || die 4 "declared source path is not its Git root: $SOURCE_REAL"
[[ "$WORKTREE_ROOT" == "$WORKTREE_REAL" ]] || die 4 "declared worktree path is not its Git root: $WORKTREE_REAL"

SOURCE_ORIGIN="$(${TOOL_PATHS[git]} -C "$SOURCE_REAL" remote get-url origin 2>/dev/null || true)"
WORKTREE_ORIGIN="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" remote get-url origin 2>/dev/null || true)"
[[ -n "$SOURCE_ORIGIN" && -n "$WORKTREE_ORIGIN" ]] || die 4 "source tree and worktree must both have an origin remote"
SOURCE_REPOSITORY="$(normalize_repository "$SOURCE_ORIGIN" 2>/dev/null || true)"
WORKTREE_REPOSITORY="$(normalize_repository "$WORKTREE_ORIGIN" 2>/dev/null || true)"
[[ "$SOURCE_REPOSITORY" == "$EXPECTED_REPOSITORY" ]] || die 4 "source tree has unexpected repository identity: ${SOURCE_REPOSITORY:-unknown}"
[[ "$WORKTREE_REPOSITORY" == "$EXPECTED_REPOSITORY" ]] || die 4 "worktree has unexpected repository identity: ${WORKTREE_REPOSITORY:-unknown}"
[[ "$SOURCE_REPOSITORY" == "$WORKTREE_REPOSITORY" ]] || die 4 "source tree and worktree repository identities differ"
REPOSITORY="$WORKTREE_REPOSITORY"
ORIGIN_PROTOCOL="$(remote_protocol "$WORKTREE_ORIGIN")"
ORIGIN_SAFE="$(redact_remote "$WORKTREE_ORIGIN")"
[[ "$ORIGIN_PROTOCOL" != "unknown" ]] || die 4 "unsupported origin transport"

resolve_tool node required
resolve_tool pnpm required
resolve_tool uv required
resolve_tool docker optional
resolve_tool pwsh optional

TOOL_VERSIONS[node]="$(${TOOL_PATHS[node]} --version 2>/dev/null || true)"
TOOL_VERSIONS[pnpm]="$(${TOOL_PATHS[pnpm]} --version 2>/dev/null || true)"
TOOL_VERSIONS[uv]="$(${TOOL_PATHS[uv]} --version 2>/dev/null || true)"
[[ -n "${TOOL_PATHS[docker]:-}" ]] && TOOL_VERSIONS[docker]="$(${TOOL_PATHS[docker]} --version 2>/dev/null || true)"
[[ -n "${TOOL_PATHS[pwsh]:-}" ]] && TOOL_VERSIONS[pwsh]="$(${TOOL_PATHS[pwsh]} --version 2>/dev/null || true)"

PACKAGE_JSON="$WORKTREE_REAL/web-dashboard/package.json"
[[ -f "$PACKAGE_JSON" ]] || die 4 "repository package config is missing: web-dashboard/package.json"
NODE_ENGINE="$(read_engine node "$PACKAGE_JSON")"
PNPM_ENGINE="$(read_engine pnpm "$PACKAGE_JSON")"
[[ -n "$NODE_ENGINE" ]] || die 4 "Node engine is missing from web-dashboard/package.json"
[[ -n "$PNPM_ENGINE" ]] || die 4 "pnpm engine is missing from web-dashboard/package.json"
check_major_engine node "${TOOL_VERSIONS[node]}" "$NODE_ENGINE"
check_major_engine pnpm "${TOOL_VERSIONS[pnpm]}" "$PNPM_ENGINE"

PYTHON_VERSION_FILE="$WORKTREE_REAL/.python-version"
[[ -f "$PYTHON_VERSION_FILE" ]] || die 4 "repository Python version file is missing: .python-version"
EXPECTED_PYTHON="$(tr -d '[:space:]' < "$PYTHON_VERSION_FILE")"
[[ -n "$EXPECTED_PYTHON" ]] || die 4 ".python-version is empty"
if [[ -e "$WORKTREE_REAL/.venv/bin/python" ]]; then
  PROJECT_PYTHON_PATH="$(realpath -e -- "$WORKTREE_REAL/.venv/bin/python" 2>/dev/null || true)"
  [[ -n "$PROJECT_PYTHON_PATH" ]] || die 2 "project Python cannot be resolved"
  validate_tool_path project_python "$PROJECT_PYTHON_PATH"
  PROJECT_PYTHON_VERSION="$($PROJECT_PYTHON_PATH --version 2>&1 || true)"
  [[ "$PROJECT_PYTHON_VERSION" == "Python $EXPECTED_PYTHON"* ]] || die 2 "project Python $PROJECT_PYTHON_VERSION does not match .python-version $EXPECTED_PYTHON"
  PROJECT_PYTHON="$PROJECT_PYTHON_PATH $PROJECT_PYTHON_VERSION"
else
  PROJECT_PYTHON="NOT_READY (expected Python $EXPECTED_PYTHON at .venv/bin/python)"
  WARNINGS+=("project virtual environment is not ready; setup may create .venv after preflight")
fi

if contains_windows_override "${GIT_SSH:-}"; then
  die 2 "GIT_SSH contains a Windows or mounted-drive executable"
fi
if contains_windows_override "${GIT_SSH_COMMAND:-}"; then
  die 2 "GIT_SSH_COMMAND contains a Windows or mounted-drive executable"
fi

LOCAL_SSH_COMMAND="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" config --local --get-all core.sshCommand 2>/dev/null || true)"
ALL_SSH_COMMAND="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" config --show-origin --get-all core.sshCommand 2>/dev/null || true)"
LOCAL_SSH_VARIANT="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" config --local --get-all ssh.variant 2>/dev/null || true)"

if contains_windows_override "$LOCAL_SSH_COMMAND"; then
  die 2 "repository-local core.sshCommand contains a Windows or mounted-drive executable"
fi
if [[ "$ORIGIN_PROTOCOL" == "https" ]] && contains_windows_override "$ALL_SSH_COMMAND"; then
  WARNINGS+=("higher-level Windows core.sshCommand is present but does not affect the canonical HTTPS origin")
fi
if [[ "$ORIGIN_PROTOCOL" == "https" && -n "$LOCAL_SSH_VARIANT" ]]; then
  WARNINGS+=("repository-local ssh.variant is set but unused by the canonical HTTPS origin")
fi

if [[ "$ORIGIN_PROTOCOL" == "ssh" ]]; then
  EFFECTIVE_SSH="${GIT_SSH_COMMAND:-}"
  [[ -n "$EFFECTIVE_SSH" ]] || EFFECTIVE_SSH="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" config --get core.sshCommand 2>/dev/null || true)"
  [[ -n "$EFFECTIVE_SSH" ]] || EFFECTIVE_SSH="${GIT_SSH:-}"
  [[ -n "$EFFECTIVE_SSH" ]] || EFFECTIVE_SSH="$(type -P ssh 2>/dev/null || true)"
  [[ -n "$EFFECTIVE_SSH" ]] || die 2 "SSH origin has no resolvable SSH executable"
  SSH_EXECUTABLE="${EFFECTIVE_SSH%%[[:space:]]*}"
  SSH_EXECUTABLE="${SSH_EXECUTABLE%\"}"
  SSH_EXECUTABLE="${SSH_EXECUTABLE#\"}"
  if [[ "$SSH_EXECUTABLE" != */* ]]; then
    SSH_EXECUTABLE="$(type -P "$SSH_EXECUTABLE" 2>/dev/null || true)"
  fi
  [[ -n "$SSH_EXECUTABLE" ]] || die 2 "effective SSH executable cannot be resolved"
  validate_tool_path ssh "$SSH_EXECUTABLE"
fi

if ((DO_FETCH)); then
  [[ "$ORIGIN_PROTOCOL" == "https" ]] || WARNINGS+=("fetch uses SSH origin; Linux SSH validation passed")
  if [[ "$ORIGIN_PROTOCOL" == "https" ]]; then
    resolve_tool gh required
    TOOL_VERSIONS[gh]="$(${TOOL_PATHS[gh]} --version 2>/dev/null | head -n 1 || true)"
    ${TOOL_PATHS[gh]} auth status --hostname github.com >/dev/null 2>&1 || die 3 "GitHub CLI authentication failed for github.com"
  fi
  FETCH_OUTPUT=""
  if ! FETCH_OUTPUT="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" fetch origin --prune 2>&1)"; then
    GIT_FETCH="FAIL"
    die 3 "git fetch origin --prune failed"
  fi
  GIT_FETCH="PASS"
elif ((OFFLINE)); then
  GIT_FETCH="OFFLINE"
else
  GIT_FETCH="NOT_REQUESTED"
fi

EXPECTED_BASE_SHA="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" rev-parse --verify "${EXPECTED_BASE}^{commit}" 2>/dev/null || true)"
[[ -n "$EXPECTED_BASE_SHA" ]] || die 4 "expected base does not resolve: $EXPECTED_BASE"

if ${TOOL_PATHS[git]} -C "$WORKTREE_REAL" show-ref --verify --quiet refs/heads/core; then
  COUNTS="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" rev-list --left-right --count "core...$EXPECTED_BASE" 2>/dev/null || true)"
  if [[ "$COUNTS" =~ ^([0-9]+)[[:space:]]+([0-9]+)$ ]]; then
    LOCAL_CORE="ahead=${BASH_REMATCH[1]} behind=${BASH_REMATCH[2]}"
    if ((BASH_REMATCH[2] > 0)); then
      WARNINGS+=("local core is behind $EXPECTED_BASE; task branches must start from exact $EXPECTED_BASE_SHA")
    fi
  else
    LOCAL_CORE="comparison unavailable"
  fi
else
  LOCAL_CORE="local branch missing"
fi

STATUS_OUTPUT="$(${TOOL_PATHS[git]} -C "$WORKTREE_REAL" status --short --untracked-files=all 2>/dev/null || true)"
if [[ -n "$STATUS_OUTPUT" ]]; then
  DIRTY_COUNT="$(printf '%s\n' "$STATUS_OUTPUT" | sed '/^$/d' | wc -l | tr -d '[:space:]')"
  DIRTY_STATE="DIRTY ($DIRTY_COUNT entries)"
  if ((REQUIRE_CLEAN)); then
    die 4 "worktree contains tracked or untracked changes"
  fi
  WARNINGS+=("worktree is dirty; --require-clean was not requested")
else
  DIRTY_STATE="CLEAN"
fi

print_summary "PASS"
exit 0
