"""Create, verify, and finalize a GitHub Release without mutating published assets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from release_common import APPROVED_ARTIFACT_NAME, ReleaseError, SemVer, sha256_file


ASSET_NAMES = (APPROVED_ARTIFACT_NAME, "SHA256SUMS.txt", "release-manifest.json")


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args], check=check, capture_output=True, text=True, encoding="utf-8"
    )


def repository() -> str:
    value = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not value or value.count("/") != 1:
        raise ReleaseError("GITHUB_REPOSITORY must identify owner/repository")
    return value


def read_manifest(bundle: Path, version: str, channel: str, commit_sha: str) -> dict:
    try:
        manifest = json.loads((bundle / "release-manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"Could not read release manifest: {exc}") from exc
    expected = {
        "version": version,
        "channel": channel,
        "tag": f"v{version}",
        "commitSha": commit_sha,
        "artifactName": APPROVED_ARTIFACT_NAME,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ReleaseError(f"Release manifest mismatch for {key}")
    artifact = bundle / APPROVED_ARTIFACT_NAME
    if not artifact.is_file() or sha256_file(artifact) != manifest.get("artifactSha256"):
        raise ReleaseError("Release artifact does not match release manifest")
    for name in ASSET_NAMES:
        if not (bundle / name).is_file():
            raise ReleaseError(f"Release asset is missing: {name}")
    return manifest


def release_json(repo: str, tag: str) -> dict | None:
    result = gh("api", f"repos/{repo}/releases/tags/{tag}", check=False)
    if result.returncode != 0:
        if "HTTP 404" in result.stderr:
            return None
        raise ReleaseError("Could not inspect GitHub Release")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseError("GitHub Release response was not valid JSON") from exc


def verify_uploaded_assets(repo: str, tag: str, bundle: Path, manifest: dict) -> None:
    release = release_json(repo, tag)
    if release is None:
        raise ReleaseError("GitHub Release disappeared during verification")
    actual_names = {asset.get("name") for asset in release.get("assets", [])}
    if set(ASSET_NAMES) != actual_names:
        raise ReleaseError(f"GitHub Release assets mismatch: {sorted(actual_names)}")
    with tempfile.TemporaryDirectory(prefix="asr-release-verify-") as temp:
        destination = Path(temp)
        gh("release", "download", tag, "--repo", repo, "--dir", str(destination))
        for name in ASSET_NAMES:
            if sha256_file(destination / name) != sha256_file(bundle / name):
                raise ReleaseError(f"Downloaded GitHub Release asset hash mismatch: {name}")
    if sha256_file(bundle / APPROVED_ARTIFACT_NAME) != manifest["artifactSha256"]:
        raise ReleaseError("Release artifact hash changed during GitHub upload")


def create_or_refresh_draft(bundle: Path, version: str, channel: str, commit_sha: str) -> dict:
    repo = repository()
    tag = f"v{version}"
    manifest = read_manifest(bundle, version, channel, commit_sha)
    release = release_json(repo, tag)
    if release is not None and not release.get("draft"):
        raise ReleaseError("Refusing to modify an already published GitHub Release")
    if release is None:
        args = [
            "release", "create", tag, "--repo", repo, "--target", commit_sha,
            "--title", f"Anki Study Report {version}", "--notes-file", str(bundle / "release-notes.md"),
            "--draft",
        ]
        if channel == "prerelease":
            args.append("--prerelease")
        gh(*args)
    else:
        gh(
            "release", "edit", tag, "--repo", repo,
            "--title", f"Anki Study Report {version}",
            "--notes-file", str(bundle / "release-notes.md"),
            "--draft=true", f"--prerelease={'true' if channel == 'prerelease' else 'false'}",
        )
    gh(
        "release", "upload", tag, "--repo", repo, "--clobber",
        *(str(bundle / name) for name in ASSET_NAMES),
    )
    verify_uploaded_assets(repo, tag, bundle, manifest)
    return {"status": "draft-verified", "tag": tag, "artifactSha256": manifest["artifactSha256"]}


def finalize(version: str, channel: str) -> dict:
    repo = repository()
    tag = f"v{version}"
    release = release_json(repo, tag)
    if release is None:
        raise ReleaseError("GitHub Release draft does not exist")
    expected_prerelease = channel == "prerelease"
    if not release.get("draft"):
        if bool(release.get("prerelease")) != expected_prerelease:
            raise ReleaseError("Published GitHub Release channel mismatch")
        return {"status": "already-published", "tag": tag}
    gh(
        "release", "edit", tag, "--repo", repo, "--draft=false",
        f"--prerelease={'true' if expected_prerelease else 'false'}",
        f"--latest={'false' if expected_prerelease else 'true'}",
    )
    verified = release_json(repo, tag)
    if verified is None or verified.get("draft") or bool(verified.get("prerelease")) != expected_prerelease:
        raise ReleaseError("GitHub Release finalization verification failed")
    return {"status": "published", "tag": tag, "url": verified.get("html_url")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("draft", "finalize"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", choices=("stable", "prerelease"), required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--commit-sha")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        parsed = SemVer.parse(args.version)
        if (args.channel == "stable") == bool(parsed.prerelease):
            raise ReleaseError("Version and channel do not agree")
        if args.mode == "draft":
            if args.bundle is None or not args.commit_sha:
                raise ReleaseError("draft mode requires --bundle and --commit-sha")
            report = create_or_refresh_draft(args.bundle.resolve(), args.version, args.channel, args.commit_sha)
        else:
            report = finalize(args.version, args.channel)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"GitHub Release {report['status']}: {report['tag']}")
        return 0
    except (ReleaseError, OSError, subprocess.CalledProcessError) as exc:
        print(f"GitHub Release operation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
