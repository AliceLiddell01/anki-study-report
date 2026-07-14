from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from conftest import ROOT


def load_release_common():
    path = ROOT / "scripts" / "release_common.py"
    spec = importlib.util.spec_from_file_location("release_common", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_release_manager():
    load_release_common()
    path = ROOT / "scripts" / "manage_github_release.py"
    spec = importlib.util.spec_from_file_location("manage_github_release", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(["gh"], returncode, stdout, stderr)


def release_record(
    release_id: int = 101,
    *,
    tag: str = "v1.0.0",
    draft: bool = True,
    prerelease: bool = False,
    target: str = "a" * 40,
    assets: list[dict] | None = None,
) -> dict:
    return {
        "id": release_id,
        "tag_name": tag,
        "name": "Anki Study Report 1.0.0",
        "draft": draft,
        "prerelease": prerelease,
        "target_commitish": target,
        "assets": list(assets or []),
    }


def asset_record(asset_id: int, name: str, data: bytes, *, state: str = "uploaded") -> dict:
    return {
        "id": asset_id,
        "name": name,
        "state": state,
        "size": len(data),
        "digest": f"sha256:{hashlib.sha256(data).hexdigest()}",
    }


def release_bundle(tmp_path: Path) -> tuple[Path, dict[str, bytes], dict]:
    data = {
        "anki_study_report.ankiaddon": b"addon-bytes",
        "SHA256SUMS.txt": b"checksum-line\n",
        "release-manifest.json": b'{"fixture":true}\n',
    }
    for name, content in data.items():
        (tmp_path / name).write_bytes(content)
    (tmp_path / "release-notes.md").write_text("notes\n", encoding="utf-8")
    manifest = {"artifactSha256": hashlib.sha256(data["anki_study_report.ankiaddon"]).hexdigest()}
    return tmp_path, data, manifest


def test_canonical_version_is_pure_semver_and_packaged_source():
    release = load_release_common()

    assert release.read_version() == "1.0.0"
    source = (ROOT / "anki_study_report" / "version.py").read_text(encoding="utf-8")
    assert "aqt" not in source
    assert "__version__ = \"1.0.0\"" in source


@pytest.mark.parametrize("invalid", ["01.0.0", "1.00.0", "1.0", "v1.0.0", "1.0.0-01"])
def test_semver_rejects_invalid_or_leading_zero_versions(invalid: str):
    release = load_release_common()

    with pytest.raises(release.ReleaseError):
        release.SemVer.parse(invalid)


def test_release_notes_and_ankiweb_description_share_only_current_section():
    release = load_release_common()

    notes = release.release_notes("1.0.0")
    description = release.render_ankiweb_description("1.0.0")

    assert notes.rstrip() in description
    assert description.count("## What's new in 1.0.0") == 1
    assert "[Unreleased]" not in notes
    assert "[Unreleased]" not in description
    assert "#/search" not in description.lower()
    assert release.sha256_text(description) == release.sha256_text(description.replace("\n", "\r\n"))


def test_ankiweb_metadata_is_strict_and_ordered(tmp_path: Path):
    release = load_release_common()
    metadata = release.validate_metadata()
    assert metadata["tags"] == [
        "stats", "report", "review", "deck", "study-time", "dashboard",
        "analytics", "forecast", "workload", "fsrs",
    ]
    with pytest.raises(release.ReleaseError, match="keys mismatch"):
        release.validate_metadata({**metadata, "password": "forbidden"})

    malformed = tmp_path / "metadata.yml"
    malformed.write_text("schema_version:\n    nested: no\n", encoding="utf-8")
    with pytest.raises(release.ReleaseError, match="Unsupported YAML"):
        release.parse_simple_yaml(malformed)


@pytest.mark.parametrize(
    "unsafe",
    ["TODO", "https://example.com/?token=secret", "password=hunter2", "C:/Users/Alice/private.txt", "Stage 8.1"],
)
def test_public_renderer_guards_reject_private_or_internal_content(unsafe: str):
    release = load_release_common()

    with pytest.raises(release.ReleaseError):
        release.assert_public_text(unsafe, "fixture")


def test_release_validation_checks_artifact_name_and_writes_no_secrets(tmp_path: Path):
    release = load_release_common()
    artifact = tmp_path / "anki_study_report.ankiaddon"
    artifact.write_bytes(b"release-bytes")

    report = release.validate_release("1.0.0", "stable", artifact=artifact, check_remote_tag=False)

    assert report["artifactName"] == artifact.name
    assert report["artifactSha256"] == release.sha256_file(artifact)
    assert "password" not in json.dumps(report).lower()
    wrong = tmp_path / "other.ankiaddon"
    wrong.write_bytes(b"release-bytes")
    with pytest.raises(release.ReleaseError, match="Release artifact"):
        release.validate_release("1.0.0", "stable", artifact=wrong, check_remote_tag=False)


def test_prepared_release_check_is_read_only():
    before = subprocess.run(["git", "status", "--short"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    result = subprocess.run(
        ["node", "scripts/run_python.mjs", "scripts/prepare_release.py", "--version", "1.0.0", "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    after = subprocess.run(["git", "status", "--short"], cwd=ROOT, check=True, capture_output=True, text=True).stdout

    assert "prepared and untagged" in result.stdout
    assert after == before


def test_published_tag_404_does_not_hide_authenticated_draft(monkeypatch):
    manager = load_release_manager()
    draft = release_record()

    def fake_gh(*args, check=True):
        if "/releases/tags/" in " ".join(args):
            return completed(stderr="HTTP 404: Not Found", returncode=1)
        return completed(json.dumps([[draft]]))

    monkeypatch.setattr(manager, "gh", fake_gh)
    assert manager.get_published_release_by_tag("owner/repo", "v1.0.0") is None
    assert manager.find_release("owner/repo", "v1.0.0")["id"] == draft["id"]


def test_authenticated_release_listing_flattens_all_paginated_pages(monkeypatch):
    manager = load_release_manager()
    calls = []

    def fake_gh(*args, check=True):
        calls.append(args)
        return completed(json.dumps([[release_record(1)], [release_record(2, tag="v2.0.0")]]))

    monkeypatch.setattr(manager, "gh", fake_gh)
    assert [item["id"] for item in manager.list_authenticated_releases("owner/repo")] == [1, 2]
    assert "--paginate" in calls[0] and "--slurp" in calls[0]
    assert "per_page=100" in calls[0][-1]


def test_find_release_returns_none_without_exact_tag(monkeypatch):
    manager = load_release_manager()
    monkeypatch.setattr(manager, "list_authenticated_releases", lambda repo: [release_record(tag="v2.0.0")])
    assert manager.find_release("owner/repo", "v1.0.0") is None


def test_malformed_authenticated_release_listing_fails(monkeypatch):
    manager = load_release_manager()
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: completed("{}"))
    with pytest.raises(manager.ReleaseError, match="malformed pagination"):
        manager.list_authenticated_releases("owner/repo")


def test_ambiguous_duplicate_exact_tag_fails(monkeypatch):
    manager = load_release_manager()
    monkeypatch.setattr(
        manager,
        "list_authenticated_releases",
        lambda repo: [release_record(10), release_record(11)],
    )
    with pytest.raises(manager.ReleaseError, match=r"Ambiguous.*\[10, 11\]"):
        manager.find_release("owner/repo", "v1.0.0")


def test_draft_creation_is_resolved_by_authenticated_listing(monkeypatch, tmp_path):
    manager = load_release_manager()
    commit = "b" * 40
    created = release_record(target=commit)
    sequence = iter([None, created])
    calls = []
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: next(sequence))
    monkeypatch.setattr(manager, "get_release_by_id", lambda *args, **kwargs: created)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())
    notes = tmp_path / "release-notes.md"
    notes.write_text("notes", encoding="utf-8")

    release, action = manager.prepare_draft(
        "owner/repo", "v1.0.0", "Anki Study Report 1.0.0", notes, "stable", commit
    )

    assert action == "created" and release["id"] == created["id"]
    assert any(call[:2] == ("release", "create") for call in calls)


def test_existing_draft_is_reused_without_create(monkeypatch, tmp_path):
    manager = load_release_manager()
    commit = "c" * 40
    existing = release_record(target="a" * 40)
    refreshed = release_record(target=commit)
    calls = []
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: existing)
    monkeypatch.setattr(manager, "get_release_by_id", lambda *args, **kwargs: refreshed)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())
    notes = tmp_path / "release-notes.md"
    notes.write_text("notes", encoding="utf-8")

    release, action = manager.prepare_draft(
        "owner/repo", "v1.0.0", "Anki Study Report 1.0.0", notes, "stable", commit
    )

    assert action == "reused" and release["target_commitish"] == commit
    assert not any(call[:2] == ("release", "create") for call in calls)


def test_existing_draft_refreshes_exact_target_sha(monkeypatch, tmp_path):
    manager = load_release_manager()
    commit = "d" * 40
    existing = release_record(target="a" * 40)
    refreshed = release_record(target=commit)
    calls = []
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: existing)
    monkeypatch.setattr(manager, "get_release_by_id", lambda *args, **kwargs: refreshed)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())
    notes = tmp_path / "release-notes.md"
    notes.write_text("notes", encoding="utf-8")

    manager.prepare_draft("owner/repo", "v1.0.0", "Anki Study Report 1.0.0", notes, "stable", commit)

    edit = next(call for call in calls if call[:2] == ("release", "edit"))
    assert edit[edit.index("--target") + 1] == commit


def test_published_release_is_never_modified_in_draft_mode(monkeypatch, tmp_path):
    manager = load_release_manager()
    published = release_record(draft=False)
    calls = []
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: published)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())
    notes = tmp_path / "release-notes.md"
    notes.write_text("notes", encoding="utf-8")

    with pytest.raises(manager.ReleaseError, match="Refusing to modify published"):
        manager.prepare_draft("owner/repo", "v1.0.0", "Anki Study Report 1.0.0", notes, "stable", "e" * 40)
    assert calls == []


def test_exact_asset_set_and_release_id_download_hashes_pass(monkeypatch, tmp_path):
    manager = load_release_manager()
    bundle, data, manifest = release_bundle(tmp_path)
    assets = [asset_record(index + 1, name, content) for index, (name, content) in enumerate(data.items())]
    release = release_record(222, assets=assets)
    downloaded_ids = []

    def download(repo, asset_id):
        downloaded_ids.append(asset_id)
        name = next(asset["name"] for asset in assets if asset["id"] == asset_id)
        return data[name]

    monkeypatch.setattr(manager, "download_release_asset", download)
    verified = manager.verify_uploaded_assets("owner/repo", release, bundle, manifest)
    assert set(verified) == set(manager.ASSET_NAMES)
    assert downloaded_ids == [1, 2, 3]


@pytest.mark.parametrize("case", ["missing", "extra"])
def test_missing_or_extra_release_asset_fails(case: str):
    manager = load_release_manager()
    data = b"x"
    assets = [asset_record(1, "anki_study_report.ankiaddon", data)]
    if case == "extra":
        assets.append(asset_record(2, "unexpected.zip", data))
    release = release_record(assets=assets)
    with pytest.raises(manager.ReleaseError, match="missing required|unexpected asset"):
        manager.asset_map(release, require_exact=True)


def test_non_uploaded_asset_fails_closed():
    manager = load_release_manager()
    release = release_record(assets=[asset_record(1, "anki_study_report.ankiaddon", b"x", state="starter")])
    with pytest.raises(manager.ReleaseError, match="not uploaded"):
        manager.asset_map(release, require_exact=False)


def test_asset_download_uses_release_asset_id_endpoint(monkeypatch):
    manager = load_release_manager()
    calls = []
    monkeypatch.setattr(manager, "gh_bytes", lambda *args: calls.append(args) or b"asset")
    assert manager.download_release_asset("owner/repo", 987) == b"asset"
    assert calls[0][-1] == "repos/owner/repo/releases/assets/987"
    assert "Accept: application/octet-stream" in calls[0]


def test_asset_hash_mismatch_fails_once_without_retry_or_recreation(monkeypatch, tmp_path):
    manager = load_release_manager()
    bundle, data, manifest = release_bundle(tmp_path)
    assets = [asset_record(index + 1, name, content) for index, (name, content) in enumerate(data.items())]
    release = release_record(assets=assets)
    calls = []
    monkeypatch.setattr(manager, "download_release_asset", lambda *args: calls.append(args) or b"wrong")
    with pytest.raises(manager.ReleaseError, match="hash mismatch"):
        manager.verify_uploaded_assets("owner/repo", release, bundle, manifest)
    assert len(calls) == 1


def test_finalize_resolves_draft_then_verifies_published_release(monkeypatch, tmp_path):
    manager = load_release_manager()
    commit = "f" * 40
    bundle, _, manifest = release_bundle(tmp_path)
    draft = release_record(333, target=commit)
    published = release_record(333, draft=False, target=commit)
    calls = []
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(manager, "read_manifest", lambda *args: manifest)
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: draft)
    monkeypatch.setattr(manager, "verify_uploaded_assets", lambda *args: {name: "hash" for name in manager.ASSET_NAMES})
    monkeypatch.setattr(manager, "get_published_release_by_tag", lambda *args: published)
    monkeypatch.setattr(manager, "resolve_tag_commit", lambda *args: commit)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())

    report = manager.finalize(bundle, "1.0.0", "stable", commit)

    assert report["status"] == "published"
    edit = next(call for call in calls if call[:2] == ("release", "edit"))
    assert "--draft=false" in edit and edit[edit.index("--target") + 1] == commit


def test_post_publish_lookup_retries_only_bounded_draft_visibility_404(monkeypatch):
    manager = load_release_manager()
    published = release_record(333, draft=False)
    sequence = iter([None, None, published])
    sleeps = []
    monkeypatch.setattr(manager, "get_published_release_by_tag", lambda *args: next(sequence))
    monkeypatch.setattr(manager.time, "sleep", lambda delay: sleeps.append(delay))
    assert manager.wait_for_published_release("owner/repo", "v1.0.0") == published
    assert sleeps == [1, 2]


def test_finalize_accepts_already_published_exact_release_without_mutation(monkeypatch, tmp_path):
    manager = load_release_manager()
    commit = "f" * 40
    bundle, _, manifest = release_bundle(tmp_path)
    published = release_record(555, draft=False, target=commit)
    calls = []
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(manager, "read_manifest", lambda *args: manifest)
    monkeypatch.setattr(manager, "find_release", lambda *args, **kwargs: published)
    monkeypatch.setattr(manager, "verify_uploaded_assets", lambda *args: {name: "hash" for name in manager.ASSET_NAMES})
    monkeypatch.setattr(manager, "get_published_release_by_tag", lambda *args: published)
    monkeypatch.setattr(manager, "resolve_tag_commit", lambda *args: commit)
    monkeypatch.setattr(manager, "gh", lambda *args, **kwargs: calls.append(args) or completed())

    report = manager.finalize(bundle, "1.0.0", "stable", commit)

    assert report["status"] == "already-published"
    assert calls == []


def test_partial_draft_rerun_reuses_release_and_clobbers_expected_assets(monkeypatch, tmp_path):
    manager = load_release_manager()
    commit = "1" * 40
    bundle, _, manifest = release_bundle(tmp_path)
    partial = release_record(444, target=commit, assets=[])
    complete = release_record(444, target=commit, assets=[])
    uploaded = []
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(manager, "read_manifest", lambda *args: manifest)
    monkeypatch.setattr(manager, "prepare_draft", lambda *args: (partial, "reused"))
    monkeypatch.setattr(manager, "upload_release_assets", lambda *args: uploaded.append(args))
    monkeypatch.setattr(manager, "get_release_by_id", lambda *args, **kwargs: complete)
    monkeypatch.setattr(manager, "verify_uploaded_assets", lambda *args: {name: "hash" for name in manager.ASSET_NAMES})

    report = manager.create_or_refresh_draft(bundle, "1.0.0", "stable", commit)

    assert report["action"] == "reused"
    assert len(uploaded) == 1 and uploaded[0][1] == "v1.0.0"


def test_failure_report_and_logs_do_not_contain_secrets(monkeypatch, tmp_path, capsys):
    manager = load_release_manager()
    secret = "gho_secret-value-that-must-not-leak"
    output = tmp_path / "report.json"
    monkeypatch.setenv("GH_TOKEN", secret)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(manager, "create_or_refresh_draft", lambda *args: (_ for _ in ()).throw(manager.ReleaseError(f"bad {secret}")))
    monkeypatch.setattr(manager, "failure_snapshot", lambda *args: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "manage_github_release.py", "draft", "--version", "1.0.0", "--channel", "stable",
            "--bundle", str(tmp_path), "--commit-sha", "2" * 40, "--output", str(output),
        ],
    )

    assert manager.main() == 1
    combined = output.read_text(encoding="utf-8") + capsys.readouterr().out
    assert secret not in combined
    assert "[REDACTED]" in combined
