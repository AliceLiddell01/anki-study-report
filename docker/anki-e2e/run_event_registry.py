from __future__ import annotations

from datetime import datetime, timezone
import re

LEGACY_SCHEMA_VERSION = 1
SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION}
MAX_MESSAGE_BYTES = 512
MAX_LINE_BYTES = 2048
PRODUCERS = {"fast-ci", "docker-e2e"}
EVENT_KINDS = {"run", "phase", "message"}
STATUSES = {"start", "pass", "fail", "skip", "cancel", "info"}
RUN_STATUSES = {"start", "pass", "fail", "cancel"}
PHASE_STATUSES = {"start", "pass", "fail", "skip", "cancel"}
MESSAGE_STATUSES = {"info"}

FAST_CI_PHASES = {
    "run",
    "install-python-dependencies",
    "install-frontend-dependencies",
    "changelog-check",
    "frontend-typecheck-tests",
    "frontend-vitest",
    "frontend-typecheck-build",
    "frontend-vite-build",
    "frontend-bundle-check",
    "frontend-addon-assets-copy",
    "python-pytest",
    "package-build-check",
    "package-check-only",
    "verification-planner",
    "ci-summary",
    "package-metadata-write",
    "package-staged-validation",
    "package-metadata-verify",
}

DOCKER_E2E_PHASES = {
    "run",
    "workspace-copy",
    "exact-package-validation",
    "frontend-dependency-install",
    "frontend-build",
    "addon-package",
    "profile-bootstrap",
    "collection-bootstrap",
    "real-deck-import",
    "scenario-preparation",
    "addon-install",
    "anki-start-first",
    "dashboard-ready-first",
    "api-smoke-first",
    "browser-smoke-first",
    "anki-restart",
    "dashboard-ready-restart",
    "api-smoke-restart",
    "telemetry-restart",
    "artifact-manifest",
}

PHASE_REGISTRY = {"fast-ci": FAST_CI_PHASES, "docker-e2e": DOCKER_E2E_PHASES}
EVENT_FIELDS = (
    "schemaVersion",
    "timestampUtc",
    "elapsedMs",
    "producer",
    "phaseId",
    "eventKind",
    "status",
    "durationMs",
    "current",
    "total",
    "message",
    "failureCode",
)
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
PHASE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOKEN_URL_RE = re.compile(r"(?:https?://[^\s]+@|[?&](?:access_)?token=)", re.IGNORECASE)
WINDOWS_ABSOLUTE_RE = re.compile(r"(?i)(?:^|[\s'\"(])(?:[A-Z]:[\\/]|\\\\[^\\/\s]+[\\/])")
LINUX_ABSOLUTE_RE = re.compile(r"(?:^|[\s'\"(])/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:/|\b)")
SECRET_RE = re.compile(
    r"(?:authorization\s*:\s*bearer\s+\S+|-----BEGIN (?:OPENSSH |RSA )?PRIVATE KEY-----|"
    r"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)
