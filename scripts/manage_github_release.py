"""Create, verify, and finalize GitHub Releases without mutating published assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any
from urllib.parse import quote

from release_common import APPROVED_ARTIFACT_NAME, ReleaseError, SemVer, sha256_file


ASSET_NAMES = (APPROVED_ARTIFACT_NAME, "SHA256SUMS.txt", "release-manifest.json")
TOKEN_RE = re.compile(r"\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_]{12,}")
PUBLISHED_LOOKUP_DELAYS = (1, 2, 4)


def sanitize_diagnostic(value: object) -> str:
    message = str(value).replace("\r", " ").replace("\n", " ")
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "ANKIWEB_EMAIL", "ANKIWEB_PASSWORD"):
        secret = os.environ.get(name)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    if home := os.path.expanduser("~"):
        message = message.replace(home, "[HOME]")
    message = TOKEN_RE.sub("[REDACTED]", message)
    message = re.sub(r"(?i)([?&]|&amp;)token=[^\s&]+", "", message)
    return message[:500] or "GitHub operation failed"


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and result.returncode != 0:
        detail = sanitize_diagnostic(result.stderr.strip() or result.stdout.strip())
        raise ReleaseError(f"GitHub CLI operation failed (exit {result.returncode}): {detail}")
    return result


def gh_bytes(*args: str) -> bytes:
    result = subprocess.run(["gh", *args], capture_output=True)
    if result.returncode != 0:
        detail = sanitize_diagnostic(result.stderr.decode("utf-8", errors="replace"))
        raise ReleaseError(f"GitHub asset download failed (exit {result.returncode}): {detail}")
    return result.stdout


def log_event(phase: str, **fields: object) -> None:
    safe = {"phase": phase}
    safe.update(fields)
    print(json.dumps(safe, ensure_ascii=False, sort_keys=True), flush=True)


def repository() -> str:
    value = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not value or value.count("/") != 1:
        raise ReleaseError("GITHUB_REPOSITORY must identify owner/repository")
    return value


def parse_json_object(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"{label} returned malformed JSON") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"{label} must return a JSON object")
    return value


def is_http_404(result: subprocess.CompletedProcess[str]) -> bool:
    detail = f"{result.stderr}\n{result.stdout}"
    return result.returncode != 0 and bool(re.search(r"(?:HTTP|status(?: code)?)\s*404\b", detail, re.I))


def validate_release_record(release: dict[str, Any], *, expected_tag: str | None = None) -> dict[str, Any]:
    release_id = release.get("id")
    if isinstance(release_id, bool) or not isinstance(release_id, int) or release_id <= 0:
        raise ReleaseError("GitHub release record has an invalid release ID")
    if not isinstance(release.get("tag_name"), str) or not release["tag_name"]:
        raise ReleaseError(f"GitHub release {release_id} has an invalid tag_name")
    if expected_tag is not None and release["tag_name"] != expected_tag:
        raise ReleaseError(f"GitHub release {release_id} tag mismatch")
    if not isinstance(release.get("draft"), bool) or not isinstance(release.get("prerelease"), bool):
        raise ReleaseError(f"GitHub release {release_id} has invalid channel state")
    if not isinstance(release.get("target_commitish"), str) or not release["target_commitish"]:
        raise ReleaseError(f"GitHub release {release_id} has an invalid target_commitish")
    if not isinstance(release.get("assets", []), list):
        raise ReleaseError(f"GitHub release {release_id} has malformed assets")
    return release


def list_authenticated_releases(repo: str) -> list[dict[str, Any]]:
    result = gh(
        "api", "--method", "GET", "--paginate", "--slurp",
        f"repos/{repo}/releases?per_page=100",
    )
    try:
        pages = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseError("Authenticated release listing returned malformed JSON") from exc
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ReleaseError("Authenticated release listing returned malformed pagination data")
    releases: list[dict[str, Any]] = []
    for page in pages:
        for release in page:
            if not isinstance(release, dict):
                raise ReleaseError("Authenticated release listing contains a malformed record")
            releases.append(validate_release_record(release))
    return releases


def find_release(repo: str, tag: str, *, include_drafts: bool = True) -> dict[str, Any] | None:
    matches = [
        release for release in list_authenticated_releases(repo)
        if release["tag_name"] == tag and (include_drafts or not release["draft"])
    ]
    if len(matches) > 1:
        ids = sorted(release["id"] for release in matches)
        raise ReleaseError(f"Ambiguous GitHub releases for exact tag {tag}: release IDs {ids}")
    return matches[0] if matches else None


def get_release_by_id(repo: str, release_id: int, *, expected_tag: str | None = None) -> dict[str, Any]:
    result = gh("api", "--method", "GET", f"repos/{repo}/releases/{release_id}")
    release = validate_release_record(parse_json_object(result.stdout, "Get release by ID"), expected_tag=expected_tag)
    if release["id"] != release_id:
        raise ReleaseError(f"GitHub release ID changed from {release_id} to {release['id']}")
    return release


def get_published_release_by_tag(repo: str, tag: str) -> dict[str, Any] | None:
    result = gh("api", "--method", "GET", f"repos/{repo}/releases/tags/{tag}", check=False)
    if is_http_404(result):
        return None
    if result.returncode != 0:
        detail = sanitize_diagnostic(result.stderr.strip() or result.stdout.strip())
        raise ReleaseError(f"Published release lookup failed (exit {result.returncode}): {detail}")
    release = validate_release_record(parse_json_object(result.stdout, "Published release lookup"), expected_tag=tag)
    if release["draft"]:
        raise ReleaseError("Published-by-tag endpoint unexpectedly returned a draft")
    return release


def wait_for_published_release(repo: str, tag: str) -> dict[str, Any]:
    release = get_published_release_by_tag(repo, tag)
    for attempt, delay in enumerate(PUBLISHED_LOOKUP_DELAYS, start=1):
        if release is not None:
            return release
        log_event(
            "published-lookup-retry", repository=repo, tag=tag,
            attempt=attempt, delaySeconds=delay, reason="post-publish-404",
        )
        time.sleep(delay)
        release = get_published_release_by_tag(repo, tag)
    if release is None:
        raise ReleaseError(
            f"Release {tag} remained unavailable from the published-by-tag endpoint "
            "after bounded post-publish verification retries"
        )
    return release


def release_summary(release: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": release["id"],
        "tag": release["tag_name"],
        "draft": release["draft"],
        "prerelease": release["prerelease"],
        "targetCommitish": release["target_commitish"],
        "assets": [
            {
                "id": asset.get("id"),
                "name": asset.get("name"),
                "state": asset.get("state"),
                "size": asset.get("size"),
                "digest": asset.get("digest"),
            }
            for asset in release.get("assets", [])
        ],
    }


def asset_map(release: dict[str, Any], *, require_exact: bool) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for asset in release.get("assets", []):
        if not isinstance(asset, dict):
            raise ReleaseError(f"GitHub release {release['id']} contains a malformed asset")
        name = asset.get("name")
        if not isinstance(name, str) or not name:
            raise ReleaseError(f"GitHub release {release['id']} contains an asset with an invalid name")
        if name in result:
            raise ReleaseError(f"GitHub release {release['id']} contains duplicate asset {name}")
        if name not in ASSET_NAMES:
            raise ReleaseError(f"GitHub release {release['id']} contains unexpected asset {name}")
        asset_id = asset.get("id")
        size = asset.get("size")
        if isinstance(asset_id, bool) or not isinstance(asset_id, int) or asset_id <= 0:
            raise ReleaseError(f"GitHub release asset {name} has an invalid asset ID")
        if asset.get("state") != "uploaded":
            raise ReleaseError(f"GitHub release asset {name} is not uploaded (state={asset.get('state')!r})")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ReleaseError(f"GitHub release asset {name} has an invalid size")
        result[name] = asset
    if require_exact and set(result) != set(ASSET_NAMES):
        missing = sorted(set(ASSET_NAMES) - set(result))
        raise ReleaseError(f"GitHub release {release['id']} is missing required assets: {missing}")
    return result


def read_manifest(bundle: Path, version: str, channel: str, commit_sha: str) -> dict[str, Any]:
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
        path = bundle / name
        if not path.is_file() or path.stat().st_size <= 0:
            raise ReleaseError(f"Release asset is missing or empty: {name}")
    return manifest


def download_release_asset(repo: str, asset_id: int) -> bytes:
    return gh_bytes(
        "api", "--method", "GET", "-H", "Accept: application/octet-stream",
        f"repos/{repo}/releases/assets/{asset_id}",
    )


def verify_uploaded_assets(repo: str, release: dict[str, Any], bundle: Path, manifest: dict[str, Any]) -> dict[str, str]:
    assets = asset_map(release, require_exact=True)
    verified: dict[str, str] = {}
    for name in ASSET_NAMES:
        asset = assets[name]
        expected_path = bundle / name
        expected_hash = sha256_file(expected_path)
        if asset["size"] != expected_path.stat().st_size:
            raise ReleaseError(f"GitHub release asset size mismatch: {name}")
        digest = asset.get("digest")
        if digest is not None and digest != f"sha256:{expected_hash}":
            raise ReleaseError(f"GitHub release asset metadata digest mismatch: {name}")
        downloaded = download_release_asset(repo, asset["id"])
        actual_hash = hashlib.sha256(downloaded).hexdigest()
        if len(downloaded) != expected_path.stat().st_size or actual_hash != expected_hash:
            raise ReleaseError(f"Downloaded GitHub release asset hash mismatch: {name}")
        verified[name] = actual_hash
        log_event(
            "asset-verified", releaseId=release["id"], assetId=asset["id"],
            name=name, state=asset["state"], size=asset["size"], sha256=actual_hash,
        )
    if verified[APPROVED_ARTIFACT_NAME] != manifest["artifactSha256"]:
        raise ReleaseError("Verified GitHub artifact hash differs from release manifest")
    return verified


def assert_release_state(
    release: dict[str, Any], *, tag: str, draft: bool, prerelease: bool,
    target_commitish: str, title: str,
) -> None:
    validate_release_record(release, expected_tag=tag)
    if release["draft"] is not draft:
        raise ReleaseError(f"GitHub release {release['id']} draft state mismatch")
    if release["prerelease"] is not prerelease:
        raise ReleaseError(f"GitHub release {release['id']} prerelease state mismatch")
    if release["target_commitish"] != target_commitish:
        raise ReleaseError(
            f"GitHub release {release['id']} target mismatch: expected {target_commitish}, "
            f"got {release['target_commitish']}"
        )
    if release.get("name") != title:
        raise ReleaseError(f"GitHub release {release['id']} title mismatch")


def prepare_draft(
    repo: str, tag: str, title: str, notes_file: Path, channel: str, commit_sha: str,
) -> tuple[dict[str, Any], str]:
    expected_prerelease = channel == "prerelease"
    release = find_release(repo, tag, include_drafts=True)
    action = "reused"
    if release is None:
        args = [
            "release", "create", tag, "--repo", repo, "--target", commit_sha,
            "--title", title, "--notes-file", str(notes_file), "--draft",
        ]
        if expected_prerelease:
            args.append("--prerelease")
        gh(*args)
        release = find_release(repo, tag, include_drafts=True)
        if release is None:
            raise ReleaseError(f"Draft release {tag} was created but not found by authenticated listing")
        action = "created"
    if not release["draft"]:
        raise ReleaseError(f"Refusing to modify published GitHub release {release['id']} in draft mode")
    asset_map(release, require_exact=False)
    log_event(
        "draft-discovered", repository=repo, tag=tag, releaseId=release["id"],
        action=action, draft=True, prerelease=release["prerelease"],
        targetCommitish=release["target_commitish"], assets=release_summary(release)["assets"],
    )
    gh(
        "release", "edit", tag, "--repo", repo, "--target", commit_sha,
        "--title", title, "--notes-file", str(notes_file), "--draft=true",
        f"--prerelease={'true' if expected_prerelease else 'false'}",
    )
    refreshed = get_release_by_id(repo, release["id"], expected_tag=tag)
    assert_release_state(
        refreshed, tag=tag, draft=True, prerelease=expected_prerelease,
        target_commitish=commit_sha, title=title,
    )
    log_event(
        "draft-refreshed", repository=repo, tag=tag, releaseId=refreshed["id"],
        action=action, targetCommitish=refreshed["target_commitish"],
    )
    return refreshed, action


def upload_release_assets(repo: str, tag: str, bundle: Path) -> None:
    gh(
        "release", "upload", tag, "--repo", repo, "--clobber",
        *(str(bundle / name) for name in ASSET_NAMES),
    )


def create_or_refresh_draft(bundle: Path, version: str, channel: str, commit_sha: str) -> dict[str, Any]:
    repo = repository()
    tag = f"v{version}"
    title = f"Anki Study Report {version}"
    manifest = read_manifest(bundle, version, channel, commit_sha)
    release, action = prepare_draft(repo, tag, title, bundle / "release-notes.md", channel, commit_sha)
    upload_release_assets(repo, tag, bundle)
    verified_release = get_release_by_id(repo, release["id"], expected_tag=tag)
    assert_release_state(
        verified_release, tag=tag, draft=True, prerelease=channel == "prerelease",
        target_commitish=commit_sha, title=title,
    )
    hashes = verify_uploaded_assets(repo, verified_release, bundle, manifest)
    log_event(
        "draft-verified", repository=repo, tag=tag, releaseId=verified_release["id"],
        action=action, targetCommitish=commit_sha,
    )
    return {
        "status": "draft-verified", "action": action, "tag": tag,
        "artifactSha256": manifest["artifactSha256"],
        "release": release_summary(verified_release), "verifiedAssetSha256": hashes,
    }


def resolve_tag_commit(repo: str, tag: str) -> str:
    encoded = quote(tag, safe="")
    result = gh("api", "--method", "GET", f"repos/{repo}/git/ref/tags/{encoded}")
    ref = parse_json_object(result.stdout, "Git tag lookup")
    obj = ref.get("object")
    if not isinstance(obj, dict) or obj.get("type") not in {"commit", "tag"} or not isinstance(obj.get("sha"), str):
        raise ReleaseError(f"Git tag {tag} has a malformed target")
    if obj["type"] == "commit":
        return obj["sha"]
    tag_result = gh("api", "--method", "GET", f"repos/{repo}/git/tags/{obj['sha']}")
    tag_object = parse_json_object(tag_result.stdout, "Annotated Git tag lookup").get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or not isinstance(tag_object.get("sha"), str):
        raise ReleaseError(f"Annotated Git tag {tag} does not resolve directly to a commit")
    return tag_object["sha"]


def finalize(bundle: Path, version: str, channel: str, commit_sha: str) -> dict[str, Any]:
    repo = repository()
    tag = f"v{version}"
    title = f"Anki Study Report {version}"
    expected_prerelease = channel == "prerelease"
    manifest = read_manifest(bundle, version, channel, commit_sha)
    release = find_release(repo, tag, include_drafts=True)
    if release is None:
        raise ReleaseError(f"GitHub release {tag} does not exist")
    action = "already-published"
    if release["draft"]:
        assert_release_state(
            release, tag=tag, draft=True, prerelease=expected_prerelease,
            target_commitish=commit_sha, title=title,
        )
        verify_uploaded_assets(repo, release, bundle, manifest)
        log_event(
            "finalize-preflight", repository=repo, tag=tag, releaseId=release["id"],
            targetCommitish=commit_sha, assets=release_summary(release)["assets"],
        )
        gh(
            "release", "edit", tag, "--repo", repo, "--target", commit_sha,
            "--draft=false", f"--prerelease={'true' if expected_prerelease else 'false'}",
            f"--latest={'false' if expected_prerelease else 'true'}",
        )
        action = "published"
    published = (
        wait_for_published_release(repo, tag)
        if action == "published"
        else get_published_release_by_tag(repo, tag)
    )
    if published is None:
        raise ReleaseError(f"Published release {tag} is missing from the published-by-tag endpoint")
    if published["id"] != release["id"]:
        raise ReleaseError(f"Published release ID changed from {release['id']} to {published['id']}")
    assert_release_state(
        published, tag=tag, draft=False, prerelease=expected_prerelease,
        target_commitish=commit_sha, title=title,
    )
    hashes = verify_uploaded_assets(repo, published, bundle, manifest)
    tag_commit = resolve_tag_commit(repo, tag)
    if tag_commit != commit_sha:
        raise ReleaseError(f"Published Git tag {tag} points to {tag_commit}, expected {commit_sha}")
    log_event(
        "release-published-verified", repository=repo, tag=tag, releaseId=published["id"],
        action=action, targetCommitish=commit_sha, tagCommit=tag_commit,
    )
    return {
        "status": action, "tag": tag, "tagCommit": tag_commit,
        "artifactSha256": manifest["artifactSha256"],
        "release": release_summary(published), "verifiedAssetSha256": hashes,
    }


def failure_snapshot(repo: str | None, tag: str) -> dict[str, Any] | None:
    if not repo:
        return None
    try:
        release = find_release(repo, tag, include_drafts=True)
        return release_summary(release) if release else None
    except Exception:
        return None


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("draft", "finalize"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", choices=("stable", "prerelease"), required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tag = f"v{args.version}"
    repo: str | None = None
    base_report: dict[str, Any] = {
        "schemaVersion": 2, "operation": args.mode, "repository": None,
        "version": args.version, "channel": args.channel, "tag": tag,
        "commitSha": args.commit_sha, "status": "failure",
    }
    try:
        parsed = SemVer.parse(args.version)
        if (args.channel == "stable") == bool(parsed.prerelease):
            raise ReleaseError("Version and channel do not agree")
        if not re.fullmatch(r"[0-9a-f]{40}", args.commit_sha):
            raise ReleaseError("commit SHA must be a lowercase full 40-character Git SHA")
        repo = repository()
        base_report["repository"] = repo
        bundle = args.bundle.resolve()
        report = (
            create_or_refresh_draft(bundle, args.version, args.channel, args.commit_sha)
            if args.mode == "draft"
            else finalize(bundle, args.version, args.channel, args.commit_sha)
        )
        final_report = {**base_report, **report}
        write_report(args.output, final_report)
        print(f"GitHub Release {report['status']}: {report['tag']}")
        return 0
    except (ReleaseError, OSError) as exc:
        safe_error = sanitize_diagnostic(exc)
        failure = {
            **base_report, "repository": repo, "error": safe_error,
            "release": failure_snapshot(repo, tag),
        }
        write_report(args.output, failure)
        print(f"GitHub Release operation failed: {safe_error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
