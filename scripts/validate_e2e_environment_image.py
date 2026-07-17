from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


SCHEMA_VERSION = 1
SPEC_FIELDS = (
    "schemaVersion",
    "environmentVersion",
    "imageName",
    "platform",
    "playwrightImage",
    "playwrightBaseDigest",
    "playwrightVersion",
    "ankiVersion",
    "ankiArchiveSha256",
    "ankiPythonPackage",
    "pnpmVersion",
)
METADATA_FIELDS = (
    "schemaVersion",
    "repository",
    "workflowName",
    "workflowPath",
    "producerJob",
    "sourceCommitSha",
    "imageRevision",
    "runId",
    "runAttempt",
    "imageName",
    "humanTag",
    "imageDigest",
    "platform",
    "environmentVersion",
    "environmentContractSha256",
    "playwrightBaseDigest",
    "attestationStatus",
    "smokeStatus",
    "createdAt",
    "environmentSpec",
)

EXPECTED_SPEC = {
    "schemaVersion": 1,
    "environmentVersion": "env-v1",
    "imageName": "ghcr.io/aliceliddell01/anki-study-report-e2e",
    "platform": "linux/amd64",
    "playwrightImage": "mcr.microsoft.com/playwright:v1.55.1-noble",
    "playwrightBaseDigest": "sha256:2f29369043d81d6d69a815ceb80760f55e85f5020371ad06a4d996f18503ad1c",
    "playwrightVersion": "1.55.1",
    "ankiVersion": "26.05",
    "ankiArchiveSha256": "6223d705563f71ab40ce072a5d96a3919c546d5dde1e4c49dc27975e70067274",
    "ankiPythonPackage": "anki==26.5",
    "pnpmVersion": "9.15.9",
}

REPOSITORY = "AliceLiddell01/anki-study-report"
WORKFLOW_NAME = "E2E Environment Image"
WORKFLOW_PATH = ".github/workflows/e2e-environment-image.yml"
PRODUCER_JOB = "environment-image"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ENVIRONMENT_VERSION_RE = re.compile(r"^env-v[1-9][0-9]*$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
FORBIDDEN_TEXT = (
    "authorization:",
    "bearer ",
    "github_token",
    "access_token",
    "private_token",
    "ghp_",
    "gho_",
    "ghs_",
    "github_pat_",
    "password=",
    "token=",
)


class EnvironmentImageError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def read_canonical_contract_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise EnvironmentImageError(f"{path} must not contain a UTF-8 BOM")
    if b"\0" in raw:
        raise EnvironmentImageError(f"{path} must not contain NUL bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EnvironmentImageError(f"{path} must contain valid UTF-8 text") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def load_json_object(path: Path, *, require_canonical: bool = True) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raise EnvironmentImageError(f"{path} must not contain a UTF-8 BOM")
    if "\r" in raw:
        raise EnvironmentImageError(f"{path} must use LF line endings")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EnvironmentImageError(f"Could not parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EnvironmentImageError(f"{path} must contain a JSON object")
    if require_canonical and raw != canonical_json(value):
        raise EnvironmentImageError(f"{path} must be deterministic canonical UTF-8 JSON")
    return value


def require_exact_fields(value: dict[str, Any], expected: tuple[str, ...], label: str) -> None:
    actual = tuple(value.keys())
    if actual != expected:
        raise EnvironmentImageError(
            f"{label} fields/order differ from schema v1: expected {list(expected)}, found {list(actual)}"
        )


def require_positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EnvironmentImageError(f"{label} must be a positive integer")
    return value


def require_utc_timestamp(value: Any, label: str = "createdAt") -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise EnvironmentImageError(f"{label} must be a UTC ISO-8601 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EnvironmentImageError(f"{label} must be valid UTC ISO-8601") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise EnvironmentImageError(f"{label} must use UTC")
    return value


def utc_timestamp(value: str | None = None) -> str:
    if value is not None:
        return require_utc_timestamp(value)
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def reject_sensitive_or_local_text(value: Any, label: str) -> None:
    for text in iter_strings(value):
        lowered = text.lower()
        if any(marker in lowered for marker in FORBIDDEN_TEXT):
            raise EnvironmentImageError(f"{label} contains a forbidden secret/token marker")
        if text.startswith(("/home/", "/Users/", "/tmp/", "\\\\")):
            raise EnvironmentImageError(f"{label} contains an absolute/local path")
        if re.match(r"^[A-Za-z]:[\\/]", text):
            raise EnvironmentImageError(f"{label} contains a Windows absolute path")


def human_tag(spec: dict[str, Any]) -> str:
    return (
        f"{spec['environmentVersion']}-anki{spec['ankiVersion']}"
        f"-pw{spec['playwrightVersion']}"
    )


def validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    require_exact_fields(spec, SPEC_FIELDS, "Environment specification")
    if spec["schemaVersion"] != SCHEMA_VERSION:
        raise EnvironmentImageError("schemaVersion must be 1")
    if spec != EXPECTED_SPEC:
        differing = [key for key in SPEC_FIELDS if spec.get(key) != EXPECTED_SPEC[key]]
        raise EnvironmentImageError(f"Environment specification differs from env-v1 contract: {differing}")
    if not ENVIRONMENT_VERSION_RE.fullmatch(str(spec["environmentVersion"])):
        raise EnvironmentImageError("environmentVersion has an invalid format")
    image_name = str(spec["imageName"])
    if image_name != image_name.lower() or "@" in image_name or image_name.endswith(":latest"):
        raise EnvironmentImageError("imageName must be lowercase and must not contain a tag/digest/latest")
    if spec["platform"] != "linux/amd64":
        raise EnvironmentImageError("platform must be linux/amd64")
    if not SHA256_RE.fullmatch(str(spec["playwrightBaseDigest"])):
        raise EnvironmentImageError("playwrightBaseDigest must be a lowercase sha256 digest")
    if not HEX64_RE.fullmatch(str(spec["ankiArchiveSha256"])):
        raise EnvironmentImageError("ankiArchiveSha256 must be a lowercase 64-hex digest")
    tag = human_tag(spec)
    if not TAG_RE.fullmatch(tag) or tag == "latest" or tag.endswith("-latest"):
        raise EnvironmentImageError("Derived environment tag is invalid or mutable")
    reject_sensitive_or_local_text(spec, "Environment specification")
    return spec


def read_spec(path: Path) -> dict[str, Any]:
    return validate_spec(load_json_object(path))


def append_github_output(path: Path | None, values: dict[str, str]) -> None:
    if path is None:
        return
    for key, value in values.items():
        if not re.fullmatch(r"[a-z0-9_]+", key) or any(char in value for char in "\r\n\0"):
            raise EnvironmentImageError("Unsafe GitHub output key/value")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def spec_outputs(spec: dict[str, Any]) -> dict[str, str]:
    return {
        "image_name": spec["imageName"],
        "human_tag": human_tag(spec),
        "platform": spec["platform"],
        "environment_version": spec["environmentVersion"],
        "playwright_image": spec["playwrightImage"],
        "playwright_base_digest": spec["playwrightBaseDigest"],
        "playwright_version": spec["playwrightVersion"],
        "anki_version": spec["ankiVersion"],
        "anki_archive_sha256": spec["ankiArchiveSha256"],
        "anki_python_package": spec["ankiPythonPackage"],
        "pnpm_version": spec["pnpmVersion"],
    }


def compute_contract_hash(
    *,
    spec_path: Path,
    dockerfile_path: Path,
    dockerignore_path: Path,
    installer_path: Path,
) -> str:
    inputs = (
        ("environment-image-spec.json", spec_path),
        ("environment.Dockerfile", dockerfile_path),
        ("environment.Dockerfile.dockerignore", dockerignore_path),
        ("install-anki.sh", installer_path),
    )
    digest = hashlib.sha256()
    digest.update(b"anki-study-report-e2e-environment-contract-v1\0")
    for label, path in inputs:
        data = read_canonical_contract_bytes(path)
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def validate_published_metadata(
    metadata: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    require_exact_fields(metadata, METADATA_FIELDS, "Published metadata")
    if metadata["schemaVersion"] != SCHEMA_VERSION:
        raise EnvironmentImageError("Published metadata schemaVersion must be 1")
    expected_identity = {
        "repository": REPOSITORY,
        "workflowName": WORKFLOW_NAME,
        "workflowPath": WORKFLOW_PATH,
        "producerJob": PRODUCER_JOB,
        "imageName": spec["imageName"],
        "humanTag": human_tag(spec),
        "platform": spec["platform"],
        "environmentVersion": spec["environmentVersion"],
        "playwrightBaseDigest": spec["playwrightBaseDigest"],
        "smokeStatus": "success",
    }
    for key, expected in expected_identity.items():
        if metadata[key] != expected:
            raise EnvironmentImageError(f"Published metadata {key} mismatch")
    for key in ("sourceCommitSha", "imageRevision"):
        if not isinstance(metadata[key], str) or not COMMIT_RE.fullmatch(metadata[key]):
            raise EnvironmentImageError(f"{key} must be a lowercase 40-hex commit SHA")
    require_positive_int(metadata["runId"], "runId")
    require_positive_int(metadata["runAttempt"], "runAttempt")
    if not SHA256_RE.fullmatch(str(metadata["imageDigest"])):
        raise EnvironmentImageError("imageDigest must be a lowercase sha256 digest")
    if not SHA256_RE.fullmatch(str(metadata["environmentContractSha256"])):
        raise EnvironmentImageError("environmentContractSha256 must be a lowercase sha256 digest")
    if metadata["attestationStatus"] not in {"created", "existing-not-reissued"}:
        raise EnvironmentImageError("attestationStatus has an invalid value")
    require_utc_timestamp(metadata["createdAt"])
    if metadata["environmentSpec"] != spec:
        raise EnvironmentImageError("environmentSpec does not match the versioned specification")
    reject_sensitive_or_local_text(metadata, "Published metadata")
    return metadata


def read_published_metadata(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    return validate_published_metadata(load_json_object(path), spec)


def create_published_metadata(
    *,
    spec: dict[str, Any],
    output: Path,
    source_commit_sha: str,
    image_revision: str,
    run_id: int,
    run_attempt: int,
    image_digest: str,
    environment_contract_sha256: str,
    attestation_status: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": REPOSITORY,
        "workflowName": WORKFLOW_NAME,
        "workflowPath": WORKFLOW_PATH,
        "producerJob": PRODUCER_JOB,
        "sourceCommitSha": source_commit_sha,
        "imageRevision": image_revision,
        "runId": run_id,
        "runAttempt": run_attempt,
        "imageName": spec["imageName"],
        "humanTag": human_tag(spec),
        "imageDigest": image_digest,
        "platform": spec["platform"],
        "environmentVersion": spec["environmentVersion"],
        "environmentContractSha256": environment_contract_sha256,
        "playwrightBaseDigest": spec["playwrightBaseDigest"],
        "attestationStatus": attestation_status,
        "smokeStatus": "success",
        "createdAt": utc_timestamp(created_at),
        "environmentSpec": spec,
    }
    validate_published_metadata(metadata, spec)
    atomic_write_text(output, canonical_json(metadata))
    return metadata


def render_markdown(metadata: dict[str, Any]) -> str:
    exact_reference = f"{metadata['imageName']}@{metadata['imageDigest']}"
    tag_reference = f"{metadata['imageName']}:{metadata['humanTag']}"
    return "\n".join(
        [
            "# E2E environment image publication",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Result | `{metadata['smokeStatus']}` |",
            f"| Environment | `{metadata['environmentVersion']}` |",
            f"| Human tag | `{tag_reference}` |",
            f"| Exact image | `{exact_reference}` |",
            f"| Platform | `{metadata['platform']}` |",
            f"| Source commit | `{metadata['sourceCommitSha']}` |",
            f"| Image revision | `{metadata['imageRevision']}` |",
            f"| Contract SHA-256 | `{metadata['environmentContractSha256']}` |",
            f"| Playwright base digest | `{metadata['playwrightBaseDigest']}` |",
            f"| Attestation | `{metadata['attestationStatus']}` |",
            f"| Workflow run | `{metadata['runId']}` attempt `{metadata['runAttempt']}` |",
            f"| Created | `{metadata['createdAt']}` |",
            "",
            "Consumers must use the exact digest reference. The human tag is navigation-only.",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the stable E2E environment image contract.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_spec_parser = subparsers.add_parser("validate-spec")
    validate_spec_parser.add_argument("--spec", type=Path, required=True)
    validate_spec_parser.add_argument("--github-output", type=Path)

    contract_parser = subparsers.add_parser("contract-hash")
    contract_parser.add_argument("--spec", type=Path, required=True)
    contract_parser.add_argument("--dockerfile", type=Path, required=True)
    contract_parser.add_argument("--dockerignore", type=Path, required=True)
    contract_parser.add_argument("--installer", type=Path, required=True)
    contract_parser.add_argument("--github-output", type=Path)

    write_parser = subparsers.add_parser("write-published-metadata")
    write_parser.add_argument("--spec", type=Path, required=True)
    write_parser.add_argument("--output", type=Path, required=True)
    write_parser.add_argument("--source-commit-sha", required=True)
    write_parser.add_argument("--image-revision", required=True)
    write_parser.add_argument("--run-id", type=int, required=True)
    write_parser.add_argument("--run-attempt", type=int, required=True)
    write_parser.add_argument("--image-digest", required=True)
    write_parser.add_argument("--environment-contract-sha256", required=True)
    write_parser.add_argument(
        "--attestation-status",
        choices=("created", "existing-not-reissued"),
        required=True,
    )
    write_parser.add_argument("--created-at", help=argparse.SUPPRESS)

    validate_metadata_parser = subparsers.add_parser("validate-published-metadata")
    validate_metadata_parser.add_argument("--spec", type=Path, required=True)
    validate_metadata_parser.add_argument("--metadata", type=Path, required=True)

    render_parser = subparsers.add_parser("render-markdown")
    render_parser.add_argument("--spec", type=Path, required=True)
    render_parser.add_argument("--metadata", type=Path, required=True)
    render_parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "validate-spec":
            spec = read_spec(args.spec)
            append_github_output(args.github_output, spec_outputs(spec))
            print(f"Validated {args.spec} ({human_tag(spec)}).")
            return 0
        if args.command == "contract-hash":
            read_spec(args.spec)
            digest = compute_contract_hash(
                spec_path=args.spec,
                dockerfile_path=args.dockerfile,
                dockerignore_path=args.dockerignore,
                installer_path=args.installer,
            )
            append_github_output(
                args.github_output,
                {"environment_contract_sha256": digest},
            )
            print(digest)
            return 0
        if args.command == "write-published-metadata":
            spec = read_spec(args.spec)
            metadata = create_published_metadata(
                spec=spec,
                output=args.output,
                source_commit_sha=args.source_commit_sha,
                image_revision=args.image_revision,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                image_digest=args.image_digest,
                environment_contract_sha256=args.environment_contract_sha256,
                attestation_status=args.attestation_status,
                created_at=args.created_at,
            )
            print(f"Created metadata for {metadata['imageName']}@{metadata['imageDigest']}.")
            return 0
        if args.command == "validate-published-metadata":
            spec = read_spec(args.spec)
            metadata = read_published_metadata(args.metadata, spec)
            print(f"Validated metadata for {metadata['imageName']}@{metadata['imageDigest']}.")
            return 0
        if args.command == "render-markdown":
            spec = read_spec(args.spec)
            metadata = read_published_metadata(args.metadata, spec)
            atomic_write_text(args.output, render_markdown(metadata))
            print(f"Rendered {args.output}.")
            return 0
        parser.error(f"Unsupported command: {args.command}")
    except (EnvironmentImageError, OSError) as exc:
        print(f"E2E environment image validation error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
