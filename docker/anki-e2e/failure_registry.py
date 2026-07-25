from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Mapping, Sequence


SCHEMA_VERSION = 1
MAX_SUMMARY_BYTES = 512
MAX_ERROR_TYPE_BYTES = 80
MAX_SECONDARY = 16
MAX_PATHS = 16
MAX_PATH_BYTES = 240
MAX_DOCUMENT_BYTES = 32 * 1024
ALLOWED_PRODUCERS = {"fast-ci", "docker-e2e"}
ALLOWED_CATEGORIES = {
    "validation",
    "package_identity",
    "environment_identity",
    "anki_startup",
    "readiness",
    "api_smoke",
    "browser_item",
    "telemetry",
    "restart",
    "artifact_manifest",
    "sanitization",
    "cleanup",
    "cancellation",
    "unknown",
}
ALLOWED_EXIT_CLASSES = {2, 3, 4, 5, 6, 7, 130, 143}
ALLOWED_SIGNALS = {None, "SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT", "SIGKILL"}
CODE_RE = re.compile(r"^ASR-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
ERROR_TYPE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
TOKEN_URL_RE = re.compile(r"(?:https?://[^\s]+@|[?&](?:access_)?token=)", re.IGNORECASE)
WINDOWS_ABSOLUTE_RE = re.compile(r"(?i)(?:^|[\s'\"(])(?:[A-Z]:[\\/]|\\\\[^\\/\s]+[\\/])")
LINUX_ABSOLUTE_RE = re.compile(r"(?:^|[\s'\"(])/(?:home|Users|workspace|mnt|tmp|var|etc|root)(?:/|\b)")
SECRET_RE = re.compile(
    r"(?:authorization\s*:\s*bearer\s+\S+|-----BEGIN (?:OPENSSH |RSA )?PRIVATE KEY-----|"
    r"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)

FAST_PHASES = frozenset({
    "install-python-dependencies", "install-frontend-dependencies", "changelog-check",
    "frontend-typecheck-tests", "frontend-vitest", "frontend-typecheck-build",
    "frontend-vite-build", "frontend-bundle-check", "frontend-addon-assets-copy",
    "python-pytest", "package-build-check", "package-check-only", "verification-planner",
    "ci-summary", "package-metadata-write", "package-staged-validation", "package-metadata-verify",
})
DOCKER_PHASES = frozenset({
    "workspace-copy", "exact-package-validation", "frontend-dependency-install", "frontend-build",
    "addon-package", "profile-bootstrap", "collection-bootstrap", "real-deck-import",
    "scenario-preparation", "addon-install", "anki-start-first", "dashboard-ready-first",
    "api-smoke-first", "browser-smoke-first", "anki-restart", "dashboard-ready-restart",
    "api-smoke-restart", "telemetry-restart", "artifact-manifest",
})
ALL_PHASES = FAST_PHASES | DOCKER_PHASES


@dataclass(frozen=True)
class FailureDefinition:
    category: str
    domain: str
    default_summary: str
    default_exit_class: int
    allowed_phases: frozenset[str]
    can_be_secondary: bool


def _definition(category: str, domain: str, summary: str, exit_class: int, phases: Sequence[str], secondary: bool = True) -> FailureDefinition:
    return FailureDefinition(category, domain, summary, exit_class, frozenset(phases), secondary)


REGISTRY: Mapping[str, FailureDefinition] = {
    "ASR-FAST-DEPENDENCY": _definition("validation", "fast", "Fast CI dependency setup failed", 2, ["install-python-dependencies", "install-frontend-dependencies"]),
    "ASR-FAST-VALIDATION": _definition("validation", "fast", "Fast CI validation failed", 2, ["changelog-check", "verification-planner"]),
    "ASR-FAST-FRONTEND": _definition("validation", "fast", "Frontend verification failed", 2, [p for p in FAST_PHASES if p.startswith("frontend-")]),
    "ASR-FAST-PYTHON": _definition("validation", "fast", "Python verification failed", 2, ["python-pytest"]),
    "ASR-FAST-PACKAGE": _definition("package_identity", "fast", "Fast CI package verification failed", 3, ["package-build-check", "package-check-only", "package-metadata-write", "package-staged-validation", "package-metadata-verify"]),
    "ASR-FAST-FINALIZATION": _definition("artifact_manifest", "fast", "Fast CI diagnostics finalization failed", 6, ["ci-summary"]),
    "ASR-FAST-CANCELLED": _definition("cancellation", "fast", "Fast CI was cancelled", 130, list(FAST_PHASES), secondary=False),
    "ASR-FAST-UNKNOWN": _definition("unknown", "fast", "Fast CI failed before a known failure path was identified", 2, list(FAST_PHASES)),
    "ASR-E2E-VALIDATION": _definition("validation", "e2e", "Docker E2E validation failed", 2, ["workspace-copy", "frontend-dependency-install", "frontend-build"]),
    "ASR-E2E-PACKAGE-IDENTITY": _definition("package_identity", "e2e", "Exact add-on package identity validation failed", 3, ["exact-package-validation", "addon-package"]),
    "ASR-E2E-ENVIRONMENT-IDENTITY": _definition("environment_identity", "e2e", "Exact E2E environment identity validation failed", 3, []),
    "ASR-E2E-REAL-DECK-CONTRACT": _definition("validation", "e2e", "Real-deck E2E contract validation failed", 3, ["profile-bootstrap", "collection-bootstrap", "real-deck-import", "scenario-preparation", "addon-install"]),
    "ASR-E2E-ANKI-STARTUP": _definition("anki_startup", "e2e", "Anki Desktop failed to start", 4, ["anki-start-first"]),
    "ASR-E2E-READINESS": _definition("readiness", "e2e", "Dashboard readiness verification failed", 4, ["dashboard-ready-first", "dashboard-ready-restart"]),
    "ASR-E2E-API-SMOKE": _definition("api_smoke", "e2e", "Dashboard API smoke failed", 5, ["api-smoke-first", "api-smoke-restart"]),
    "ASR-E2E-BROWSER-ITEM": _definition("browser_item", "e2e", "Browser smoke item failed", 5, ["browser-smoke-first"]),
    "ASR-E2E-TELEMETRY": _definition("telemetry", "e2e", "Telemetry verification failed", 5, ["browser-smoke-first", "telemetry-restart"]),
    "ASR-E2E-RESTART": _definition("restart", "e2e", "Anki restart verification failed", 4, ["anki-restart"]),
    "ASR-E2E-ARTIFACT-MANIFEST": _definition("artifact_manifest", "e2e", "Artifact manifest generation or validation failed", 6, ["artifact-manifest"]),
    "ASR-E2E-SANITIZATION": _definition("sanitization", "e2e", "Public artifact sanitization failed", 6, []),
    "ASR-E2E-CLEANUP": _definition("cleanup", "e2e", "Docker E2E cleanup failed", 7, []),
    "ASR-E2E-CANCELLED": _definition("cancellation", "e2e", "Docker E2E was cancelled", 130, list(DOCKER_PHASES), secondary=False),
    "ASR-E2E-UNKNOWN": _definition("unknown", "e2e", "Docker E2E failed before a known failure path was identified", 5, list(DOCKER_PHASES)),
}

PHASE_FAILURE_CODES: Mapping[str, str] = {
    "install-python-dependencies": "ASR-FAST-DEPENDENCY",
    "install-frontend-dependencies": "ASR-FAST-DEPENDENCY",
    "changelog-check": "ASR-FAST-VALIDATION",
    "verification-planner": "ASR-FAST-VALIDATION",
    "frontend-typecheck-tests": "ASR-FAST-FRONTEND",
    "frontend-vitest": "ASR-FAST-FRONTEND",
    "frontend-typecheck-build": "ASR-FAST-FRONTEND",
    "frontend-vite-build": "ASR-FAST-FRONTEND",
    "frontend-bundle-check": "ASR-FAST-FRONTEND",
    "frontend-addon-assets-copy": "ASR-FAST-FRONTEND",
    "python-pytest": "ASR-FAST-PYTHON",
    "package-build-check": "ASR-FAST-PACKAGE",
    "package-check-only": "ASR-FAST-PACKAGE",
    "package-metadata-write": "ASR-FAST-PACKAGE",
    "package-staged-validation": "ASR-FAST-PACKAGE",
    "package-metadata-verify": "ASR-FAST-PACKAGE",
    "ci-summary": "ASR-FAST-FINALIZATION",
    "workspace-copy": "ASR-E2E-VALIDATION",
    "exact-package-validation": "ASR-E2E-PACKAGE-IDENTITY",
    "frontend-dependency-install": "ASR-E2E-VALIDATION",
    "frontend-build": "ASR-E2E-VALIDATION",
    "addon-package": "ASR-E2E-PACKAGE-IDENTITY",
    "profile-bootstrap": "ASR-E2E-REAL-DECK-CONTRACT",
    "collection-bootstrap": "ASR-E2E-REAL-DECK-CONTRACT",
    "real-deck-import": "ASR-E2E-REAL-DECK-CONTRACT",
    "scenario-preparation": "ASR-E2E-REAL-DECK-CONTRACT",
    "addon-install": "ASR-E2E-REAL-DECK-CONTRACT",
    "anki-start-first": "ASR-E2E-ANKI-STARTUP",
    "dashboard-ready-first": "ASR-E2E-READINESS",
    "api-smoke-first": "ASR-E2E-API-SMOKE",
    "browser-smoke-first": "ASR-E2E-BROWSER-ITEM",
    "anki-restart": "ASR-E2E-RESTART",
    "dashboard-ready-restart": "ASR-E2E-READINESS",
    "api-smoke-restart": "ASR-E2E-API-SMOKE",
    "telemetry-restart": "ASR-E2E-TELEMETRY",
    "artifact-manifest": "ASR-E2E-ARTIFACT-MANIFEST",
}


class FailureProtocolError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def code_for_phase(producer: str, phase_id: str, *, item_kind: str | None = None) -> str:
    if producer not in ALLOWED_PRODUCERS:
        raise FailureProtocolError(f"unknown producer: {producer}")
    if phase_id == "browser-smoke-first" and item_kind == "telemetry":
        return "ASR-E2E-TELEMETRY"
    code = PHASE_FAILURE_CODES.get(phase_id)
    if code:
        return code
    return "ASR-FAST-UNKNOWN" if producer == "fast-ci" else "ASR-E2E-UNKNOWN"


def definition(code: str) -> FailureDefinition:
    value = REGISTRY.get(code)
    if value is None:
        raise FailureProtocolError(f"unknown failure code: {code}")
    return value


def exit_class_for(code: str, original_exit_code: int | None = None, original_signal: str | None = None) -> int:
    if original_signal == "SIGINT" or original_exit_code == 130:
        return 130
    if original_signal == "SIGTERM" or original_exit_code == 143:
        return 143
    return definition(code).default_exit_class
