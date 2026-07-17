from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docker" / "anki-e2e" / "environment-image-spec.json"
DOCKERFILE = ROOT / "docker" / "anki-e2e" / "environment.Dockerfile"
DOCKERIGNORE = ROOT / "docker" / "anki-e2e" / "environment.Dockerfile.dockerignore"
INSTALLER = ROOT / "docker" / "anki-e2e" / "install-anki.sh"
ATTRIBUTES = ROOT / ".gitattributes"

PRODUCTION_CONTRACT = "sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447"
PUBLISHED_IMAGE = "sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475"
SOURCE_COMMIT = "298be46ffe84bffa612dd6322dc0421b1ff0955e"
PRODUCER_RUN_ID = 29561205765


def load_validator():
    path = ROOT / "scripts" / "validate_e2e_environment_image.py"
    spec = importlib.util.spec_from_file_location("validate_e2e_environment_image_portability", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def contract_paths() -> dict[str, Path]:
    return {
        "spec_path": SPEC,
        "dockerfile_path": DOCKERFILE,
        "dockerignore_path": DOCKERIGNORE,
        "installer_path": INSTALLER,
    }


def write_variant(directory: Path, ending: str) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for argument, source in contract_paths().items():
        text = source.read_text(encoding="utf-8")
        if ending == "lf":
            variant = text
        elif ending == "crlf":
            variant = text.replace("\n", "\r\n")
        elif ending == "mixed":
            lines = text.splitlines(keepends=True)
            variant = "".join(
                line[:-1] + ("\r\n" if index % 2 == 0 else "\n")
                if line.endswith("\n")
                else line
                for index, line in enumerate(lines)
            )
        elif ending == "cr":
            variant = text.replace("\n", "\r")
        else:
            raise AssertionError(ending)
        destination = directory / source.name
        destination.write_bytes(variant.encode("utf-8"))
        paths[argument] = destination
    return paths


def reference_hash(inputs: tuple[tuple[str, bytes], ...]) -> str:
    digest = hashlib.sha256()
    digest.update(b"anki-study-report-e2e-environment-contract-v1\0")
    for label, data in inputs:
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


@pytest.mark.parametrize("ending", ["lf", "crlf", "mixed", "cr"])
def test_contract_hash_is_cross_platform_eol_invariant(tmp_path: Path, ending: str) -> None:
    validator = load_validator()
    paths = write_variant(tmp_path / ending, ending)

    assert validator.compute_contract_hash(**paths) == PRODUCTION_CONTRACT


def test_current_contract_files_match_published_production_hash() -> None:
    validator = load_validator()

    assert validator.compute_contract_hash(**contract_paths()) == PRODUCTION_CONTRACT


@pytest.mark.parametrize(
    ("mutation", "expected_suffix"),
    [
        (lambda data: data + b"x", "added character"),
        (lambda data: data[:-1], "removed character"),
        (lambda data: data[:-1] + b" \n", "trailing space"),
        (lambda data: data.rstrip(b"\n"), "final newline"),
    ],
)
def test_meaningful_text_changes_remain_hash_sensitive(
    tmp_path: Path,
    mutation,
    expected_suffix: str,
) -> None:
    validator = load_validator()
    changed = tmp_path / "environment.Dockerfile"
    changed.write_bytes(mutation(DOCKERFILE.read_bytes()))
    paths = contract_paths()
    paths["dockerfile_path"] = changed

    assert validator.compute_contract_hash(**paths) != PRODUCTION_CONTRACT, expected_suffix


def test_dockerfile_instruction_and_spec_identity_changes_affect_hash(tmp_path: Path) -> None:
    validator = load_validator()

    dockerfile = tmp_path / "environment.Dockerfile"
    dockerfile.write_text(
        DOCKERFILE.read_text(encoding="utf-8").replace("CMD [\"bash\"]", "CMD [\"sh\"]"),
        encoding="utf-8",
        newline="\n",
    )
    dockerfile_paths = contract_paths()
    dockerfile_paths["dockerfile_path"] = dockerfile
    assert validator.compute_contract_hash(**dockerfile_paths) != PRODUCTION_CONTRACT

    spec_document = json.loads(SPEC.read_text(encoding="utf-8"))
    spec_document["pnpmVersion"] = "9.15.8"
    spec = tmp_path / "environment-image-spec.json"
    spec.write_text(json.dumps(spec_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    spec_paths = contract_paths()
    spec_paths["spec_path"] = spec
    assert validator.compute_contract_hash(**spec_paths) != PRODUCTION_CONTRACT


def test_framing_labels_and_input_order_remain_meaningful() -> None:
    validator = load_validator()
    inputs = tuple(
        (label, validator.read_canonical_contract_bytes(path))
        for label, path in (
            ("environment-image-spec.json", SPEC),
            ("environment.Dockerfile", DOCKERFILE),
            ("environment.Dockerfile.dockerignore", DOCKERIGNORE),
            ("install-anki.sh", INSTALLER),
        )
    )

    assert reference_hash(inputs) == PRODUCTION_CONTRACT
    assert reference_hash((("environment-spec.json", inputs[0][1]), *inputs[1:])) != PRODUCTION_CONTRACT
    assert reference_hash((inputs[1], inputs[0], *inputs[2:])) != PRODUCTION_CONTRACT


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"\xef\xbb\xbftext\n", "UTF-8 BOM"),
        (b"text\0more\n", "NUL"),
        (b"\xff\xfe\n", "valid UTF-8"),
    ],
)
def test_contract_text_reader_fails_closed(
    tmp_path: Path,
    payload: bytes,
    message: str,
) -> None:
    validator = load_validator()
    path = tmp_path / "invalid.txt"
    path.write_bytes(payload)

    with pytest.raises(validator.EnvironmentImageError, match=message):
        validator.read_canonical_contract_bytes(path)


def test_contract_text_reader_preserves_non_eol_text_semantics(tmp_path: Path) -> None:
    validator = load_validator()
    path = tmp_path / "contract.txt"
    path.write_bytes("é  \r\nnext\rfinal".encode("utf-8"))

    assert validator.read_canonical_contract_bytes(path) == "é  \nnext\nfinal".encode("utf-8")


def test_contract_files_have_explicit_lf_attributes() -> None:
    lines = {
        line
        for line in ATTRIBUTES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    assert "docker/anki-e2e/environment-image-spec.json text eol=lf" in lines
    assert "docker/anki-e2e/environment.Dockerfile text eol=lf" in lines
    assert "docker/anki-e2e/environment.Dockerfile.dockerignore text eol=lf" in lines
    assert "docker/anki-e2e/*.sh text eol=lf" in lines


def test_published_stage5_identity_matches_sanitized_evidence() -> None:
    validator = load_validator()
    spec = validator.read_spec(SPEC)
    metadata = {
        "schemaVersion": 1,
        "repository": "AliceLiddell01/anki-study-report",
        "workflowName": "E2E Environment Image",
        "workflowPath": ".github/workflows/e2e-environment-image.yml",
        "producerJob": "environment-image",
        "sourceCommitSha": SOURCE_COMMIT,
        "imageRevision": SOURCE_COMMIT,
        "runId": PRODUCER_RUN_ID,
        "runAttempt": 1,
        "imageName": spec["imageName"],
        "humanTag": validator.human_tag(spec),
        "imageDigest": PUBLISHED_IMAGE,
        "platform": "linux/amd64",
        "environmentVersion": "env-v1",
        "environmentContractSha256": PRODUCTION_CONTRACT,
        "playwrightBaseDigest": spec["playwrightBaseDigest"],
        "attestationStatus": "created",
        "smokeStatus": "success",
        "createdAt": "2026-07-17T06:53:59Z",
        "environmentSpec": spec,
    }

    assert validator.validate_published_metadata(metadata, spec) == metadata
