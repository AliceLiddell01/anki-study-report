from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

from ankiweb_description import render_ankiweb_description
from release_common import (
    APPROVED_ARTIFACT_NAME,
    ReleaseError,
    release_notes,
    sha256_file,
    sha256_text,
    validate_release,
)


def load_package_module():
    path = Path(__file__).resolve().parent / "package_addon.py"
    spec = importlib.util.spec_from_file_location("release_package_addon", path)
    if spec is None or spec.loader is None:
        raise ReleaseError("Could not load package validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def create_bundle(
    version: str,
    channel: str,
    artifact: Path,
    output_dir: Path,
    commit_sha: str,
    *,
    allow_existing_tag: bool = False,
) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise ReleaseError("commit SHA must be a lowercase full 40-character Git SHA")
    artifact = artifact.resolve()
    output_dir = output_dir.resolve()
    if artifact.name != APPROVED_ARTIFACT_NAME or artifact.parent != output_dir:
        raise ReleaseError(f"Artifact must be {output_dir / APPROVED_ARTIFACT_NAME}")
    validation = validate_release(
        version,
        channel,
        artifact=artifact,
        allow_existing_tag=allow_existing_tag,
    )
    package = load_package_module()
    archive = package.validate_archive(artifact)
    if not archive.ok or archive.canonical_version != version:
        raise ReleaseError("Release package validation failed or packaged version differs")
    notes = release_notes(version)
    description = render_ankiweb_description(version)
    artifact_sha = sha256_file(artifact)
    report = {
        **validation,
        "commitSha": commit_sha,
        "artifactSha256": artifact_sha,
        "descriptionSha256": sha256_text(description),
        "package": {
            "entryCount": len(archive.names),
            "entries": archive.names,
            "zipTestResult": archive.testzip_result,
            "canonicalVersion": archive.canonical_version,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "SHA256SUMS.txt").write_text(
        f"{artifact_sha}  {APPROVED_ARTIFACT_NAME}\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "release-notes.md").write_text(notes, encoding="utf-8", newline="\n")
    (output_dir / "ankiweb-description.md").write_text(description, encoding="utf-8", newline="\n")
    (output_dir / "ankiweb-description.sha256").write_text(
        report["descriptionSha256"] + "\n", encoding="utf-8", newline="\n"
    )
    (output_dir / "release-manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic release metadata around one exact add-on artifact.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", choices=("stable", "prerelease"), required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--allow-existing-tag", action="store_true")
    args = parser.parse_args()
    try:
        report = create_bundle(
            args.version,
            args.channel,
            args.artifact,
            args.output_dir,
            args.commit_sha,
            allow_existing_tag=args.allow_existing_tag,
        )
    except (ReleaseError, OSError, json.JSONDecodeError) as exc:
        print(f"Release bundle creation failed: {exc}")
        return 1
    print(f"Created release bundle for v{args.version} (artifact sha256={report['artifactSha256']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
