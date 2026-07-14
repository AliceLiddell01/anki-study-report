from __future__ import annotations

import importlib.util
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
