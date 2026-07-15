from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ci_package_metadata", ROOT / "scripts" / "write_ci_package_metadata.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

METADATA_NAME = MODULE.METADATA_NAME
PACKAGE_NAME = MODULE.PACKAGE_NAME
PUBLIC_FIELDS = MODULE.PUBLIC_FIELDS
MetadataError = MODULE.MetadataError
create_package_artifact = MODULE.create_package_artifact
verify_package_artifact = MODULE.verify_package_artifact


TESTED = "A" * 40
HEAD = "B" * 40
BASE = "C" * 40
CREATED_AT = "2026-07-16T12:34:56Z"


def make_package(tmp_path: Path, name: str = PACKAGE_NAME, payload: bytes = b"exact package bytes") -> Path:
    package = tmp_path / name
    package.write_bytes(payload)
    return package


def create_valid(tmp_path: Path, **overrides: object) -> tuple[Path, Path, dict]:
    source = overrides.get("package")
    if source is None:
        source_dir = tmp_path / "source"
        source_dir.mkdir(exist_ok=True)
        source = make_package(source_dir)
    output = tmp_path / "nested" / "ci-package"
    values = {
        "package": source,
        "output_directory": output,
        "repository": "AliceLiddell01/anki-study-report",
        "event_name": "pull_request",
        "ref": "refs/pull/32/merge",
        "tested_commit_sha": TESTED,
        "source_head_sha": HEAD,
        "source_base_sha": BASE,
        "run_id": 123456789,
        "run_attempt": 1,
        "artifact_name": f"ci-package-{TESTED.lower()}-123456789-1",
        "created_at": CREATED_AT,
    }
    values.update(overrides)
    metadata = create_package_artifact(**values)
    return source, output, metadata


def test_valid_pr_metadata_has_unambiguous_commit_identity(tmp_path: Path) -> None:
    _, output, metadata = create_valid(tmp_path)

    assert metadata["testedCommitSha"] == TESTED.lower()
    assert metadata["sourceHeadSha"] == HEAD.lower()
    assert metadata["sourceBaseSha"] == BASE.lower()
    assert metadata["eventName"] == "pull_request"
    assert metadata["ref"] == "refs/pull/32/merge"
    assert verify_package_artifact(output) == metadata


def test_valid_dispatch_metadata_uses_null_base(tmp_path: Path) -> None:
    _, _, metadata = create_valid(
        tmp_path,
        event_name="workflow_dispatch",
        ref="refs/heads/chatgpt/ci-optimization-stage-2-fast-ci-package-artifact",
        source_head_sha=TESTED,
        source_base_sha="null",
    )

    assert metadata["sourceHeadSha"] == TESTED.lower()
    assert metadata["sourceBaseSha"] is None


def test_package_hash_and_size_are_computed_from_staged_bytes(tmp_path: Path) -> None:
    payload = b"\x00\x01exact\xffpackage"
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = make_package(source_dir, payload=payload)
    _, output, metadata = create_valid(tmp_path, package=source)

    assert metadata["packageSha256"] == hashlib.sha256(payload).hexdigest()
    assert metadata["packageSizeBytes"] == len(payload)
    assert (output / PACKAGE_NAME).read_bytes() == payload


def test_sha_inputs_are_normalized_to_lowercase(tmp_path: Path) -> None:
    _, _, metadata = create_valid(tmp_path)

    assert metadata["testedCommitSha"] == TESTED.lower()
    assert metadata["sourceHeadSha"] == HEAD.lower()
    assert metadata["sourceBaseSha"] == BASE.lower()


def test_missing_package_fails(tmp_path: Path) -> None:
    with pytest.raises(MetadataError, match="does not exist"):
        create_valid(tmp_path, package=tmp_path / PACKAGE_NAME)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tested_commit_sha", "1234", "testedCommitSha"),
        ("source_head_sha", "g" * 40, "sourceHeadSha"),
        ("source_base_sha", "f" * 39, "sourceBaseSha"),
    ],
)
def test_invalid_commit_sha_fails(tmp_path: Path, field: str, value: str, message: str) -> None:
    with pytest.raises(MetadataError, match=message):
        create_valid(tmp_path, **{field: value})


@pytest.mark.parametrize(("field", "value", "message"), [("run_id", 0, "runId"), ("run_attempt", -1, "runAttempt")])
def test_invalid_run_identity_fails(tmp_path: Path, field: str, value: int, message: str) -> None:
    with pytest.raises(MetadataError, match=message):
        create_valid(tmp_path, **{field: value})


def test_unexpected_package_filename_fails(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    package = make_package(source_dir, name="anki_study_report-ci.ankiaddon")

    with pytest.raises(MetadataError, match="filename"):
        create_valid(tmp_path, package=package)


def test_output_parent_is_created_and_inventory_is_exact(tmp_path: Path) -> None:
    _, output, _ = create_valid(tmp_path)

    assert output.is_dir()
    assert sorted(path.name for path in output.iterdir()) == sorted([METADATA_NAME, PACKAGE_NAME])
    assert all(path.is_file() and not path.is_symlink() for path in output.iterdir())


def test_json_contains_only_expected_public_fields(tmp_path: Path) -> None:
    _, output, _ = create_valid(tmp_path)
    raw = json.loads((output / METADATA_NAME).read_text(encoding="utf-8"))

    assert set(raw) == PUBLIC_FIELDS
    assert "artifactDigest" not in raw
    assert "artifactUrl" not in raw
    assert "token" not in raw
    assert "workspace" not in raw


def test_artifact_name_must_match_tested_sha_and_run_identity(tmp_path: Path) -> None:
    with pytest.raises(MetadataError, match="artifactName"):
        create_valid(tmp_path, artifact_name="ci-package-wrong")


def test_source_package_bytes_are_not_modified(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = make_package(source_dir, payload=b"immutable source")
    before = source.read_bytes()

    create_valid(tmp_path, package=source)

    assert source.read_bytes() == before


def test_verify_rejects_extra_files_and_hash_tampering(tmp_path: Path) -> None:
    _, output, _ = create_valid(tmp_path)
    (output / "extra.log").write_text("unexpected", encoding="utf-8")
    with pytest.raises(MetadataError, match="exactly"):
        verify_package_artifact(output)

    (output / "extra.log").unlink()
    (output / PACKAGE_NAME).write_bytes(b"tampered")
    with pytest.raises(MetadataError, match="packageSha256"):
        verify_package_artifact(output)
