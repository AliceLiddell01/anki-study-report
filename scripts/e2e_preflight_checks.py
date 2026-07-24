from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Callable, Mapping, Sequence

from e2e_preflight_contract import *
def load_json(path: Path) -> dict[str, object]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc: raise PreflightError("required JSON contract is unreadable") from exc
    if not isinstance(value, dict): raise PreflightError("required JSON contract must be an object")
    return value

def artifact_root(root: Path, env: Mapping[str, str]) -> Path:
    raw = env.get("ANKI_E2E_ARTIFACT_ROOT") or env.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR") or "e2e-artifacts"
    path = Path(raw); return (path if path.is_absolute() else root / path).resolve(strict=False)

def inside(path: Path, root: Path) -> None:
    try: rel = path.relative_to(root)
    except ValueError as exc: raise PreflightError("artifact root must remain inside the repository workspace") from exc
    if not rel.parts or rel.parts[0] in {".git", "docker", "scripts", "tests", "web-dashboard", "anki_study_report"}: raise PreflightError("artifact root is unsafe or overlaps source files")

def static_checks(root: Path, env: Mapping[str, str]) -> list[tuple[str, Callable[[], str]]]:
    mode = env.get("E2E_MODE", "standard"); scope = env.get("ANKI_E2E_SCOPE", env.get("E2E_SCOPE", "full")); workers = env.get("ANKI_E2E_SCREENSHOT_WORKERS", env.get("SCREENSHOT_WORKERS_INPUT", "3")); restart = env.get("ANKI_E2E_VERIFY_RESTART", env.get("VERIFY_RESTART_INPUT", "auto")); source = env.get("ANKI_E2E_PACKAGE_SOURCE", "source-build"); prebuilt = env.get("ANKI_E2E_PREBUILT_ADDON_PATH", ""); cloud = env.get("GITHUB_ACTIONS", "").lower() == "true" or env.get("ANKI_E2E_IMAGE_SOURCE") == "ghcr"
    spec_path = root / "docker/anki-e2e/environment-image-spec.json"; lock_path = root / "docker/anki-e2e/environment-image-lock.json"
    def mode_scope() -> str:
        if mode not in MODES or scope not in SCOPES or (mode in {"strict-apkg", "perf100"} and scope not in {"full", "cards"}): raise PreflightError("Mode or scope is unsupported")
        return "Mode and scope are supported"
    def worker() -> str:
        if workers not in {"1", "2", "3", "4"}: raise PreflightError("Screenshot worker count is unsupported")
        return "Screenshot worker count is supported"
    def restart_check() -> str:
        if restart not in {"auto", "0", "1", "true", "false"}: raise PreflightError("Restart policy is unsupported")
        return "Restart policy is supported"
    def package() -> str:
        if source not in PACKAGE_SOURCES or (source == "source-build" and prebuilt) or (source != "source-build" and not prebuilt) or (cloud and source == "source-build"): raise PreflightError("Package source is unsupported or non-exclusive")
        return "Package source is exclusive and supported"
    def required() -> str:
        if any(not (root / item).is_file() for item in REQUIRED_FILES): raise PreflightError("Required repository files are missing")
        return "Required repository files are present"
    def artifact() -> str: inside(artifact_root(root, env), root); return "Artifact root is repository-scoped and safe"
    def syntax() -> str:
        spec = load_json(spec_path); lock = load_json(lock_path)
        if spec.get("schemaVersion") != 1 or lock.get("schemaVersion") != 1 or not isinstance(lock.get("imageDigest"), str) or not DIGEST_RE.fullmatch(lock["imageDigest"]): raise PreflightError("Environment lock syntax is invalid")
        if not isinstance(lock.get("imageName"), str) or not isinstance(lock.get("publishedFromCommitSha"), str) or not re.fullmatch(r"[0-9a-f]{40}", lock["publishedFromCommitSha"]): raise PreflightError("Environment lock syntax is invalid")
        return "Environment spec and lock syntax is valid"
    def consistency() -> str:
        spec = load_json(spec_path); lock = load_json(lock_path)
        if any(spec.get(k) != lock.get(k) for k in ("environmentVersion", "imageName", "platform")): raise PreflightError("Environment spec and lock differ")
        if not isinstance(lock.get("environmentContractSha256"), str) or not DIGEST_RE.fullmatch(lock["environmentContractSha256"]): raise PreflightError("Environment contract hash is invalid")
        return "Environment spec and lock are consistent"
    def exact() -> str:
        lock = load_json(lock_path); expected = f"{lock['imageName']}@{lock['imageDigest']}"; supplied = env.get("ANKI_E2E_IMAGE") or env.get("ANKI_E2E_IMAGE_REFERENCE")
        if supplied and supplied != expected: raise PreflightError("Exact environment image reference differs from the lock")
        if cloud and not IMAGE_RE.fullmatch(expected): raise PreflightError("Cloud environment image is not an immutable GHCR digest")
        if ":latest" in expected: raise PreflightError("Mutable latest image reference is forbidden")
        return "Environment image reference is immutable and exact"
    def compose() -> str:
        base = (root / "docker/anki-e2e/docker-compose.yml").read_text(encoding="utf-8"); ghcr = (root / "docker/anki-e2e/docker-compose.ghcr.yml").read_text(encoding="utf-8")
        if "services:" not in base or "anki-e2e:" not in base or "anki-e2e:" not in ghcr or "run-e2e-failure-wrapper.sh" not in ghcr: raise PreflightError("Compose service declaration is incomplete")
        return "Compose files declare the canonical E2E service"
    return list(zip(STATIC_CHECK_IDS, (mode_scope, worker, restart_check, package, required, artifact, syntax, consistency, exact, compose)))

def runtime_checks(root: Path, env: Mapping[str, str], runner: CommandRunner) -> list[tuple[str, Callable[[], str]]]:
    source = env.get("ANKI_E2E_PACKAGE_SOURCE", "source-build"); files = ["-f", "docker/anki-e2e/docker-compose.yml"]
    if env.get("ANKI_E2E_IMAGE_SOURCE") == "ghcr": files += ["-f", "docker/anki-e2e/docker-compose.ghcr.yml"]
    prefix = ["docker", "compose", *files]; resolved: dict[str, object] = {}
    def call(args: Sequence[str]) -> CommandResult:
        try: return runner(args, root, env)
        except (OSError, subprocess.SubprocessError) as exc: raise PreflightError("Required command could not be executed") from exc
    def package() -> str:
        if source == "source-build": return "No staged package is required for local source build"
        raw = env.get("ANKI_E2E_HOST_PACKAGE_PATH") or "docker/anki-e2e/local-input/anki_study_report.ankiaddon"; path = Path(raw); path = path if path.is_absolute() else root / path
        try: path.resolve(strict=False).relative_to(root)
        except ValueError as exc: raise PreflightError("Staged package path is outside the repository") from exc
        if not path.is_file() or path.stat().st_size == 0: raise PreflightError("Staged exact package is missing")
        expected = env.get("ANKI_E2E_EXPECTED_PACKAGE_SHA256") or env.get("ANKI_E2E_FAST_CI_PACKAGE_SHA256")
        if expected and (not SHA256_RE.fullmatch(expected) or hashlib.sha256(path.read_bytes()).hexdigest() != expected): raise PreflightError("Staged package hash differs from expected identity")
        return "Staged exact package is present"
    def ok(args: Sequence[str], summary: str) -> str:
        if call(args).returncode != 0: raise PreflightError(summary.replace("is", "is not", 1))
        return summary
    def docker_cli() -> str: return ok(["docker", "--version"], "Docker CLI is available")
    def compose_cli() -> str: return ok(["docker", "compose", "version"], "Docker Compose CLI is available")
    def daemon() -> str: return ok(["docker", "info", "--format", "{{json .ServerVersion}}"], "Docker daemon is reachable")
    def platform() -> str:
        result = call(["docker", "info", "--format", "{{.OSType}}/{{.Architecture}}"])
        if result.returncode or result.stdout.strip() not in {"linux/amd64", "linux/x86_64"}: raise PreflightError("Docker daemon platform is unsupported")
        return "Docker daemon platform is supported"
    def model() -> str:
        if call([*prefix, "config", "--quiet"]).returncode: raise PreflightError("Resolved Compose model is invalid")
        result = call([*prefix, "config", "--format", "json"])
        if result.returncode: raise PreflightError("Resolved Compose JSON is unavailable")
        try: value = json.loads(result.stdout)
        except json.JSONDecodeError as exc: raise PreflightError("Resolved Compose JSON is invalid") from exc
        if not isinstance(value, dict): raise PreflightError("Resolved Compose model must be an object")
        resolved.clear(); resolved.update(value); return "Resolved Compose model is valid"
    def service() -> str:
        services = resolved.get("services")
        if not isinstance(services, dict) or set(services) != {"anki-e2e"}: raise PreflightError("Resolved Compose services differ from the expected singleton")
        return "Resolved Compose contains only the E2E service"
    def image() -> str:
        service = resolved["services"]["anki-e2e"]
        if not isinstance(service, dict): raise PreflightError("Resolved E2E service is invalid")
        value = service.get("image")
        if env.get("ANKI_E2E_IMAGE_SOURCE") == "ghcr":
            expected = env.get("ANKI_E2E_IMAGE")
            if value != expected or not isinstance(value, str) or not IMAGE_RE.fullmatch(value) or service.get("pull_policy") != "never" or env.get("ANKI_E2E_NO_BUILD") != "1": raise PreflightError("Resolved Compose image is not the exact GHCR digest")
        elif value == "latest" or (isinstance(value, str) and value.endswith(":latest")): raise PreflightError("Mutable latest image is forbidden")
        return "Resolved Compose image source is exact and immutable"
    def mounts() -> str:
        service = resolved["services"]["anki-e2e"]; volumes = service.get("volumes", []) if isinstance(service, dict) else []
        for item in volumes:
            if not isinstance(item, dict): raise PreflightError("Resolved Compose mount is invalid")
            if item.get("target") in {"/", "/var/run/docker.sock"} or item.get("source") == "/var/run/docker.sock": raise PreflightError("Resolved Compose contains an unsafe host mount")
            if item.get("target") == "/workspace" and not item.get("read_only", False): raise PreflightError("Workspace mount must be read-only")
        return "Resolved Compose mounts are scoped and safe"
    def ports() -> str:
        service = resolved["services"]["anki-e2e"]
        if not isinstance(service, dict) or service.get("ports") or service.get("expose") or service.get("network_mode") == "host": raise PreflightError("Resolved Compose exposes external ports")
        return "Resolved Compose does not expose external ports"
    return list(zip(RUNTIME_CHECK_IDS, (package, docker_cli, compose_cli, daemon, platform, model, service, image, mounts, ports)))
