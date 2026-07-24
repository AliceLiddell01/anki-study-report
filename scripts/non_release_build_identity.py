#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Mapping

SCHEMA_VERSION = 1
KIND = "non-release-build"
CANONICAL_FILENAME = "non-release-build-identity.json"
MAX_DOCUMENT_BYTES = 32 * 1024
WORKFLOW_PATH = ".github/workflows/ci-e2e.yml"
PACKAGE_SOURCE = "fast-ci-artifact"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PLATFORM_RE = re.compile(r"^[a-z0-9_.-]+/[a-z0-9_.-]+$")
REF_RE = re.compile(r"^refs/(?:heads|tags|pull)/[^\r\n\0]+$")

TOP_FIELDS = {"schemaVersion", "kind", "identityDigest", "identity", "execution"}
IDENTITY_FIELDS = {"repository", "package", "harness", "workflow", "environment", "reuse"}
PACKAGE_FIELDS = {
    "source", "testedCommitSha", "sourceRunId", "sourceRunAttempt",
    "artifactId", "artifactDigest", "innerSha256", "sizeBytes",
}
HARNESS_FIELDS = {"commitSha", "checkoutSha"}
WORKFLOW_FIELDS = {"repository", "filePath", "sourceSha"}
ENVIRONMENT_FIELDS = {
    "imageReference", "imageDigest", "platform", "contractSha256",
    "publishedFromCommitSha",
}
REUSE_FIELDS = {"mode", "changedFileCount", "changedPathsSha256"}
EXECUTION_FIELDS = {"runId", "runAttempt", "triggerSha", "ref"}


class BuildIdentityError(ValueError):
    pass


def _object(value: Any, label: str, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BuildIdentityError(f"{label} must be an object")
    actual = set(value)
    if actual != fields:
        missing = sorted(fields - actual)
        unknown = sorted(actual - fields)
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if unknown:
            details.append("unknown=" + ",".join(unknown))
        raise BuildIdentityError(f"{label} fields differ from schema ({'; '.join(details)})")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or any(c in value for c in "\r\n\0"):
        raise BuildIdentityError(f"{label} must be a non-empty single-line string")
    return value


def _sha(value: Any, label: str) -> str:
    value = _string(value, label)
    if value != value.lower() or not SHA_RE.fullmatch(value):
        raise BuildIdentityError(f"{label} must be an exact lowercase 40-character SHA")
    return value


def _sha256(value: Any, label: str) -> str:
    value = _string(value, label)
    if value != value.lower() or not SHA256_RE.fullmatch(value):
        raise BuildIdentityError(f"{label} must be an exact lowercase SHA-256")
    return value


def _digest(value: Any, label: str) -> str:
    value = _string(value, label)
    if value != value.lower() or not DIGEST_RE.fullmatch(value):
        raise BuildIdentityError(f"{label} must use sha256:<64 lowercase hex>")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BuildIdentityError(f"{label} must be a positive integer")
    return value


def _non_negative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BuildIdentityError(f"{label} must be a non-negative integer")
    return value


def _repository(value: Any, label: str) -> str:
    value = _string(value, label)
    if not REPOSITORY_RE.fullmatch(value):
        raise BuildIdentityError(f"{label} has an invalid repository format")
    return value


def _relative_path(value: Any, label: str) -> str:
    value = _string(value, label).replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("./") or re.match(r"^[A-Za-z]:/", value):
        raise BuildIdentityError(f"{label} must be a safe repository-relative path")
    return value


def _normalize_contract_digest(value: Any, label: str) -> str:
    raw = _string(value, label).lower()
    if raw.startswith("sha256:"):
        raw = raw[len("sha256:"):]
    return _sha256(raw, label)


def _canonical_bytes(identity: Mapping[str, Any]) -> bytes:
    return json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_identity_digest(identity: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(identity)).hexdigest()


def _validate_image_reference(reference: str, digest: str) -> None:
    if "@" not in reference:
        raise BuildIdentityError("identity.environment.imageReference must be immutable and include @sha256")
    name, separator, reference_digest = reference.rpartition("@")
    if not separator or not name or _digest(reference_digest, "identity.environment.imageReference digest") != digest:
        raise BuildIdentityError("identity.environment.imageReference digest must match imageDigest")
    if "://" in name or any(c in name for c in " \t"):
        raise BuildIdentityError("identity.environment.imageReference has an invalid format")


def validate_document(document: Any, *, encoded_size: int | None = None) -> dict[str, Any]:
    document = _object(document, "document", TOP_FIELDS)
    if document["schemaVersion"] != SCHEMA_VERSION:
        raise BuildIdentityError(f"schemaVersion must be {SCHEMA_VERSION}")
    if document["kind"] != KIND:
        raise BuildIdentityError(f"kind must be {KIND}")

    identity = _object(document["identity"], "identity", IDENTITY_FIELDS)
    repository = _repository(identity["repository"], "identity.repository")

    package = _object(identity["package"], "identity.package", PACKAGE_FIELDS)
    if package["source"] != PACKAGE_SOURCE:
        raise BuildIdentityError(f"identity.package.source must be {PACKAGE_SOURCE}")
    _sha(package["testedCommitSha"], "identity.package.testedCommitSha")
    _positive_integer(package["sourceRunId"], "identity.package.sourceRunId")
    _positive_integer(package["sourceRunAttempt"], "identity.package.sourceRunAttempt")
    _positive_integer(package["artifactId"], "identity.package.artifactId")
    _digest(package["artifactDigest"], "identity.package.artifactDigest")
    _sha256(package["innerSha256"], "identity.package.innerSha256")
    _positive_integer(package["sizeBytes"], "identity.package.sizeBytes")

    harness = _object(identity["harness"], "identity.harness", HARNESS_FIELDS)
    harness_sha = _sha(harness["commitSha"], "identity.harness.commitSha")
    checkout_sha = _sha(harness["checkoutSha"], "identity.harness.checkoutSha")
    if harness_sha != checkout_sha:
        raise BuildIdentityError("identity.harness.commitSha must match the actual checkoutSha")

    workflow = _object(identity["workflow"], "identity.workflow", WORKFLOW_FIELDS)
    if _repository(workflow["repository"], "identity.workflow.repository") != repository:
        raise BuildIdentityError("identity.workflow.repository must match identity.repository")
    if _relative_path(workflow["filePath"], "identity.workflow.filePath") != WORKFLOW_PATH:
        raise BuildIdentityError(f"identity.workflow.filePath must be {WORKFLOW_PATH}")
    _sha(workflow["sourceSha"], "identity.workflow.sourceSha")

    environment = _object(identity["environment"], "identity.environment", ENVIRONMENT_FIELDS)
    image_digest = _digest(environment["imageDigest"], "identity.environment.imageDigest")
    image_reference = _string(environment["imageReference"], "identity.environment.imageReference")
    _validate_image_reference(image_reference, image_digest)
    platform = _string(environment["platform"], "identity.environment.platform")
    if not PLATFORM_RE.fullmatch(platform):
        raise BuildIdentityError("identity.environment.platform has an invalid format")
    _sha256(environment["contractSha256"], "identity.environment.contractSha256")
    _sha(environment["publishedFromCommitSha"], "identity.environment.publishedFromCommitSha")

    reuse = _object(identity["reuse"], "identity.reuse", REUSE_FIELDS)
    mode = reuse["mode"]
    if mode not in {"exact-tree", "harness-only"}:
        raise BuildIdentityError("identity.reuse.mode must be exact-tree or harness-only")
    changed_count = _non_negative_integer(reuse["changedFileCount"], "identity.reuse.changedFileCount")
    changed_hash = _sha256(reuse["changedPathsSha256"], "identity.reuse.changedPathsSha256")
    empty_hash = hashlib.sha256(b"").hexdigest()
    package_sha = package["testedCommitSha"]
    if mode == "exact-tree":
        if changed_count != 0 or changed_hash != empty_hash or package_sha != harness_sha:
            raise BuildIdentityError("exact-tree reuse requires equal package/harness SHA and an empty changed-path boundary")
    else:
        if changed_count <= 0 or changed_hash == empty_hash or package_sha == harness_sha:
            raise BuildIdentityError("harness-only reuse requires distinct SHA and a non-empty changed-path boundary")

    execution = _object(document["execution"], "execution", EXECUTION_FIELDS)
    _positive_integer(execution["runId"], "execution.runId")
    _positive_integer(execution["runAttempt"], "execution.runAttempt")
    _sha(execution["triggerSha"], "execution.triggerSha")
    ref = _string(execution["ref"], "execution.ref")
    if not REF_RE.fullmatch(ref):
        raise BuildIdentityError("execution.ref must be a bounded Git ref")

    expected = compute_identity_digest(identity)
    if _digest(document["identityDigest"], "identityDigest") != expected:
        raise BuildIdentityError("identityDigest does not match canonical identity bytes")

    if encoded_size is None:
        encoded_size = len(json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if encoded_size > MAX_DOCUMENT_BYTES:
        raise BuildIdentityError(f"identity document exceeds {MAX_DOCUMENT_BYTES} bytes")
    return document


def load_document(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise BuildIdentityError("identity document must not contain a UTF-8 BOM")
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise BuildIdentityError(f"identity document exceeds {MAX_DOCUMENT_BYTES} bytes")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildIdentityError(f"identity document is not valid UTF-8 JSON: {exc}") from exc
    return validate_document(value, encoded_size=len(raw))


def atomic_write(path: Path, document: Mapping[str, Any]) -> None:
    validate_document(dict(document))
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_DOCUMENT_BYTES:
        raise BuildIdentityError(f"identity document exceeds {MAX_DOCUMENT_BYTES} bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildIdentityError(f"could not read {label} from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BuildIdentityError(f"{label} must be a JSON object")
    return value


def _file_identity(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    if size <= 0:
        raise BuildIdentityError("exact package file must not be empty")
    return digest.hexdigest(), size


def build_document(
    *, handoff: Mapping[str, Any], reuse: Mapping[str, Any], environment_lock: Mapping[str, Any],
    package_path: Path, repository: str, harness_sha: str, checkout_sha: str,
    workflow_repository: str, workflow_path: str, workflow_source_sha: str,
    image_reference: str, image_digest: str, image_platform: str,
    run_id: int, run_attempt: int, trigger_sha: str, ref: str,
) -> dict[str, Any]:
    repository = _repository(repository, "repository")
    package_hash, package_size = _file_identity(package_path)
    contract_hash = _normalize_contract_digest(environment_lock.get("environmentContractSha256"), "environment lock contract SHA-256")

    identity: dict[str, Any] = {
        "repository": repository,
        "package": {
            "source": PACKAGE_SOURCE,
            "testedCommitSha": str(handoff.get("sourceTestedCommitSha") or "").lower(),
            "sourceRunId": handoff.get("sourceRunId"),
            "sourceRunAttempt": handoff.get("sourceRunAttempt"),
            "artifactId": handoff.get("packageArtifactId"),
            "artifactDigest": str(handoff.get("packageArtifactDigest") or "").lower(),
            "innerSha256": package_hash,
            "sizeBytes": package_size,
        },
        "harness": {
            "commitSha": str(harness_sha).lower(),
            "checkoutSha": str(checkout_sha).lower(),
        },
        "workflow": {
            "repository": workflow_repository,
            "filePath": workflow_path,
            "sourceSha": str(workflow_source_sha).lower(),
        },
        "environment": {
            "imageReference": image_reference,
            "imageDigest": image_digest.lower(),
            "platform": image_platform,
            "contractSha256": contract_hash,
            "publishedFromCommitSha": str(environment_lock.get("publishedFromCommitSha") or "").lower(),
        },
        "reuse": {
            "mode": reuse.get("reuseMode"),
            "changedFileCount": reuse.get("changedFileCount"),
            "changedPathsSha256": str(reuse.get("changedPathsSha256") or "").lower(),
        },
    }
    document = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": KIND,
        "identityDigest": compute_identity_digest(identity),
        "identity": identity,
        "execution": {
            "runId": run_id,
            "runAttempt": run_attempt,
            "triggerSha": trigger_sha.lower(),
            "ref": ref,
        },
    }
    validate_document(document)
    validate_cross_evidence(
        document=document,
        handoff=handoff,
        reuse=reuse,
        environment_lock=environment_lock,
        package_path=package_path,
    )
    return document


def validate_cross_evidence(
    *, document: Mapping[str, Any], handoff: Mapping[str, Any], reuse: Mapping[str, Any],
    environment_lock: Mapping[str, Any], package_path: Path,
) -> None:
    validated = validate_document(dict(document))
    identity = validated["identity"]
    package = identity["package"]
    harness = identity["harness"]
    workflow = identity["workflow"]
    environment = identity["environment"]
    reuse_identity = identity["reuse"]

    expected_handoff = {
        "packageSource": PACKAGE_SOURCE,
        "repository": identity["repository"],
        "sourceTestedCommitSha": package["testedCommitSha"],
        "sourceRunId": package["sourceRunId"],
        "sourceRunAttempt": package["sourceRunAttempt"],
        "packageArtifactId": package["artifactId"],
        "packageArtifactDigest": package["artifactDigest"],
        "packageSha256": package["innerSha256"],
        "packageSizeBytes": package["sizeBytes"],
        "e2eWorkflowSourceSha": workflow["sourceSha"],
        "e2eCheckoutSha": harness["checkoutSha"],
    }
    for key, expected in expected_handoff.items():
        actual = handoff.get(key)
        if key in {
            "sourceTestedCommitSha", "packageArtifactDigest", "packageSha256",
            "e2eWorkflowSourceSha", "e2eCheckoutSha",
        } and isinstance(actual, str):
            actual = actual.lower()
        if actual != expected:
            raise BuildIdentityError(f"Fast CI handoff mismatch for {key}")

    package_hash, package_size = _file_identity(package_path)
    if package_hash != package["innerSha256"] or package_size != package["sizeBytes"]:
        raise BuildIdentityError("exact package bytes do not match canonical package identity")

    expected_reuse = {
        "reuseAllowed": True,
        "reuseMode": reuse_identity["mode"],
        "packageTestedCommitSha": package["testedCommitSha"],
        "e2eHarnessCommitSha": harness["commitSha"],
        "workflowSourceSha": workflow["sourceSha"],
        "changedFileCount": reuse_identity["changedFileCount"],
        "changedPathsSha256": reuse_identity["changedPathsSha256"],
    }
    for key, expected in expected_reuse.items():
        actual = reuse.get(key)
        if key in {
            "packageTestedCommitSha", "e2eHarnessCommitSha", "workflowSourceSha",
            "changedPathsSha256",
        } and isinstance(actual, str):
            actual = actual.lower()
        if actual != expected:
            raise BuildIdentityError(f"harness reuse mismatch for {key}")
    changed_paths = reuse.get("changedPaths")
    if not isinstance(changed_paths, list) or len(changed_paths) != reuse_identity["changedFileCount"]:
        raise BuildIdentityError("harness reuse changedPaths count does not match canonical boundary")
    normalized_paths = []
    for item in changed_paths:
        normalized_paths.append(_relative_path(item, "reuse.changedPaths item"))
    if normalized_paths != sorted(dict.fromkeys(normalized_paths)):
        raise BuildIdentityError("reuse.changedPaths must be sorted and unique")
    encoded = "".join(f"{item}\n" for item in normalized_paths).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != reuse_identity["changedPathsSha256"]:
        raise BuildIdentityError("reuse.changedPaths hash does not match canonical boundary")

    lock_digest = _digest(environment_lock.get("imageDigest"), "environment lock imageDigest")
    lock_reference = f"{_string(environment_lock.get('imageName'), 'environment lock imageName')}@{lock_digest}"
    expected_environment = {
        "imageReference": lock_reference,
        "imageDigest": lock_digest,
        "platform": _string(environment_lock.get("platform"), "environment lock platform"),
        "contractSha256": _normalize_contract_digest(
            environment_lock.get("environmentContractSha256"), "environment lock contract SHA-256"
        ),
        "publishedFromCommitSha": _sha(
            environment_lock.get("publishedFromCommitSha"), "environment lock publishedFromCommitSha"
        ),
    }
    if environment != expected_environment:
        raise BuildIdentityError("environment identity does not match the immutable consumer lock")


def validate_pair(raw_path: Path, public_path: Path) -> dict[str, Any]:
    raw = load_document(raw_path)
    public = load_document(public_path)
    if raw != public:
        raise BuildIdentityError("public identity differs from validated raw identity")
    if raw["identityDigest"] != public["identityDigest"]:
        raise BuildIdentityError("public identity digest differs from validated raw identity")
    return raw


def render_summary(document: Mapping[str, Any]) -> str:
    document = validate_document(dict(document))
    identity = document["identity"]
    package = identity["package"]
    return "\n".join([
        "## Non-release build identity",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Identity digest | `{document['identityDigest']}` |",
        f"| Package tested SHA | `{package['testedCommitSha']}` |",
        f"| Package artifact | `{package['artifactId']}` / `{package['artifactDigest']}` |",
        f"| Inner package SHA-256 | `{package['innerSha256']}` |",
        f"| Harness SHA | `{identity['harness']['commitSha']}` |",
        f"| Workflow source SHA | `{identity['workflow']['sourceSha']}` |",
        f"| Environment digest | `{identity['environment']['imageDigest']}` |",
        f"| Reuse mode | `{identity['reuse']['mode']}` |",
        "",
    ])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and validate canonical non-release E2E build identity")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--handoff", type=Path, required=True)
    build.add_argument("--reuse", type=Path, required=True)
    build.add_argument("--environment-lock", type=Path, required=True)
    build.add_argument("--package", type=Path, required=True)
    build.add_argument("--repository", required=True)
    build.add_argument("--harness-sha", required=True)
    build.add_argument("--checkout-sha", required=True)
    build.add_argument("--workflow-repository", required=True)
    build.add_argument("--workflow-path", required=True)
    build.add_argument("--workflow-source-sha", required=True)
    build.add_argument("--image-reference", required=True)
    build.add_argument("--image-digest", required=True)
    build.add_argument("--image-platform", required=True)
    build.add_argument("--run-id", type=int, required=True)
    build.add_argument("--run-attempt", type=int, required=True)
    build.add_argument("--trigger-sha", required=True)
    build.add_argument("--ref", required=True)
    build.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)

    cross = subparsers.add_parser("validate-cross-evidence")
    cross.add_argument("--input", type=Path, required=True)
    cross.add_argument("--handoff", type=Path, required=True)
    cross.add_argument("--reuse", type=Path, required=True)
    cross.add_argument("--environment-lock", type=Path, required=True)
    cross.add_argument("--package", type=Path, required=True)

    pair = subparsers.add_parser("validate-pair")
    pair.add_argument("--raw", type=Path, required=True)
    pair.add_argument("--public", type=Path, required=True)

    summary = subparsers.add_parser("render-summary")
    summary.add_argument("--input", type=Path, required=True)
    summary.add_argument("--output", type=Path)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        if args.command == "build":
            document = build_document(
                handoff=_load_object(args.handoff, "Fast CI handoff"),
                reuse=_load_object(args.reuse, "harness reuse evidence"),
                environment_lock=_load_object(args.environment_lock, "environment lock"),
                package_path=args.package,
                repository=args.repository,
                harness_sha=args.harness_sha,
                checkout_sha=args.checkout_sha,
                workflow_repository=args.workflow_repository,
                workflow_path=args.workflow_path,
                workflow_source_sha=args.workflow_source_sha,
                image_reference=args.image_reference,
                image_digest=args.image_digest,
                image_platform=args.image_platform,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                trigger_sha=args.trigger_sha,
                ref=args.ref,
            )
            atomic_write(args.output, document)
            print(f"Non-release build identity: {document['identityDigest']}")
        elif args.command == "validate":
            document = load_document(args.input)
            print(f"Valid non-release build identity: {document['identityDigest']}")
        elif args.command == "validate-cross-evidence":
            validate_cross_evidence(
                document=load_document(args.input),
                handoff=_load_object(args.handoff, "Fast CI handoff"),
                reuse=_load_object(args.reuse, "harness reuse evidence"),
                environment_lock=_load_object(args.environment_lock, "environment lock"),
                package_path=args.package,
            )
            print("Non-release build identity cross-evidence validation passed")
        elif args.command == "validate-pair":
            document = validate_pair(args.raw, args.public)
            print(f"Raw/public non-release build identity parity: {document['identityDigest']}")
        elif args.command == "render-summary":
            text = render_summary(load_document(args.input))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
            else:
                print(text, end="")
        else:
            parser.error("unsupported command")
        return 0
    except (BuildIdentityError, OSError) as exc:
        parser.exit(2, f"non-release build identity error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
