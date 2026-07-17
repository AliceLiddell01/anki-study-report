from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Any

from validate_e2e_environment_image import (
    COMMIT_RE,
    SHA256_RE,
    EnvironmentImageError,
    append_github_output,
    human_tag,
    load_json_object,
    reject_sensitive_or_local_text,
    require_exact_fields,
    require_positive_int,
    read_spec,
)


LOCK_FIELDS = (
    "schemaVersion",
    "environmentVersion",
    "imageName",
    "imageDigest",
    "platform",
    "humanTag",
    "environmentContractSha256",
    "publishedFromCommitSha",
    "publicationRunId",
    "idempotentVerificationRunId",
)
EXPECTED_IMAGE_DIGEST = "sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475"
EXPECTED_ENVIRONMENT_CONTRACT = "sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447"
EXPECTED_PUBLICATION_COMMIT = "298be46ffe84bffa612dd6322dc0421b1ff0955e"
EXPECTED_PUBLICATION_RUN_ID = 29561205765
EXPECTED_REUSE_RUN_ID = 29573061110


def exact_reference(lock: dict[str, Any]) -> str:
    return f"{lock['imageName']}@{lock['imageDigest']}"


def validate_consumer_lock(lock: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    require_exact_fields(lock, LOCK_FIELDS, "Environment consumer lock")
    if lock["schemaVersion"] != 1:
        raise EnvironmentImageError("Environment consumer lock schemaVersion must be 1")

    expected = {
        "environmentVersion": spec["environmentVersion"],
        "imageName": spec["imageName"],
        "imageDigest": EXPECTED_IMAGE_DIGEST,
        "platform": spec["platform"],
        "humanTag": human_tag(spec),
        "environmentContractSha256": EXPECTED_ENVIRONMENT_CONTRACT,
        "publishedFromCommitSha": EXPECTED_PUBLICATION_COMMIT,
        "publicationRunId": EXPECTED_PUBLICATION_RUN_ID,
        "idempotentVerificationRunId": EXPECTED_REUSE_RUN_ID,
    }
    for key, expected_value in expected.items():
        if lock[key] != expected_value:
            raise EnvironmentImageError(f"Environment consumer lock {key} mismatch")

    if not SHA256_RE.fullmatch(str(lock["imageDigest"])):
        raise EnvironmentImageError("Environment consumer lock imageDigest must be a lowercase sha256 digest")
    if not SHA256_RE.fullmatch(str(lock["environmentContractSha256"])):
        raise EnvironmentImageError(
            "Environment consumer lock environmentContractSha256 must be a lowercase sha256 digest"
        )
    if not COMMIT_RE.fullmatch(str(lock["publishedFromCommitSha"])):
        raise EnvironmentImageError(
            "Environment consumer lock publishedFromCommitSha must be a lowercase 40-hex commit SHA"
        )
    require_positive_int(lock["publicationRunId"], "publicationRunId")
    require_positive_int(lock["idempotentVerificationRunId"], "idempotentVerificationRunId")

    image_name = str(lock["imageName"])
    if image_name != image_name.lower() or "@" in image_name or image_name.endswith(":latest"):
        raise EnvironmentImageError("Environment consumer lock imageName must be immutable-reference safe")
    reference = exact_reference(lock)
    if ":latest" in reference or not re.fullmatch(r"ghcr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}", reference):
        raise EnvironmentImageError("Environment consumer lock does not render a valid exact GHCR reference")

    reject_sensitive_or_local_text(lock, "Environment consumer lock")
    return lock


def read_consumer_lock(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    return validate_consumer_lock(load_json_object(path), spec)


def consumer_outputs(lock: dict[str, Any]) -> dict[str, str]:
    return {
        "image_reference": exact_reference(lock),
        "image_name": str(lock["imageName"]),
        "image_digest": str(lock["imageDigest"]),
        "image_platform": str(lock["platform"]),
        "environment_version": str(lock["environmentVersion"]),
        "environment_contract_sha256": str(lock["environmentContractSha256"]),
        "published_from_commit_sha": str(lock["publishedFromCommitSha"]),
        "human_tag": str(lock["humanTag"]),
        "environment_publication_run_id": str(lock["publicationRunId"]),
        "environment_reuse_verification_run_id": str(lock["idempotentVerificationRunId"]),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the digest-pinned E2E environment consumer lock.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-consumer-lock")
    validate_parser.add_argument("--spec", type=Path, required=True)
    validate_parser.add_argument("--lock", type=Path, required=True)
    validate_parser.add_argument("--github-output", type=Path)

    render_parser = subparsers.add_parser("render-consumer-reference")
    render_parser.add_argument("--spec", type=Path, required=True)
    render_parser.add_argument("--lock", type=Path, required=True)
    render_parser.add_argument("--github-output", type=Path)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        spec = read_spec(args.spec)
        lock = read_consumer_lock(args.lock, spec)
        outputs = consumer_outputs(lock)
        append_github_output(args.github_output, outputs)
        if args.command == "validate-consumer-lock":
            print(f"Validated GHCR consumer lock for {outputs['image_reference']}.")
            return 0
        if args.command == "render-consumer-reference":
            print(outputs["image_reference"])
            return 0
        parser.error(f"Unsupported command: {args.command}")
    except (EnvironmentImageError, OSError) as exc:
        print(f"E2E environment consumer validation error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
