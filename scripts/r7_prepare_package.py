from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import zipfile


SHA_RE = __import__("re").compile(r"^[0-9a-f]{40}$")
FORBIDDEN_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "tests",
    "docker",
    "artifacts",
    "screenshots",
    "logs",
    "profiles",
    "user_files",
    "e2e-artifacts",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".log", ".ankiaddon", ".zip"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_empty_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise ValueError(f"output directory must be absent or empty: {path}")
    else:
        path.mkdir(parents=True)


def package_manifest(package: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(package) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"ZIP integrity failed at {bad}")
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"unsafe package path: {info.filename}")
            if {part.lower() for part in path.parts} & FORBIDDEN_PARTS:
                raise ValueError(f"forbidden package entry: {info.filename}")
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise ValueError(f"forbidden package entry: {info.filename}")
            data = b"" if info.is_dir() else archive.read(info.filename)
            rows.append(
                {
                    "path": path.as_posix(),
                    "size": info.file_size,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    return rows


def write_output(path: Path | None, values: dict[str, object]) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the exact temporary R7 package and provenance.")
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--package-directory", required=True, type=Path)
    parser.add_argument("--provenance-directory", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--tested-sha", required=True)
    parser.add_argument("--source-base-sha", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    package = args.package.resolve()
    if not package.is_file() or package.name != "anki_study_report.ankiaddon":
        raise ValueError("expected anki_study_report.ankiaddon")
    if package.is_symlink():
        raise ValueError("package must not be a symlink")
    for label, value in (("tested SHA", args.tested_sha), ("source base SHA", args.source_base_sha)):
        if not SHA_RE.fullmatch(value):
            raise ValueError(f"{label} must be an exact lowercase SHA")
    if args.run_id <= 0 or args.run_attempt <= 0:
        raise ValueError("run identity must be positive")
    if not args.repository or "/" not in args.repository:
        raise ValueError("repository identity is invalid")
    if not args.ref or any(char in args.ref for char in "\r\n\0"):
        raise ValueError("ref is invalid")
    if not args.artifact_name or any(char in args.artifact_name for char in "\r\n\0"):
        raise ValueError("artifact name is invalid")

    require_empty_directory(args.package_directory)
    require_empty_directory(args.provenance_directory)

    staged_package = args.package_directory / package.name
    shutil.copyfile(package, staged_package)
    package_hash = sha256(staged_package)
    if package_hash != sha256(package) or staged_package.stat().st_size != package.stat().st_size:
        raise ValueError("staged package bytes differ from source")

    metadata = {
        "schemaVersion": 1,
        "repository": args.repository,
        "workflowName": "R7 temporary integrated acceptance v3",
        "workflowPath": ".github/workflows/r7-integrated-acceptance-v3.yml",
        "producerJob": "fast",
        "eventName": "pull_request",
        "ref": args.ref,
        "testedCommitSha": args.tested_sha,
        "sourceHeadSha": args.tested_sha,
        "sourceBaseSha": args.source_base_sha,
        "runId": args.run_id,
        "runAttempt": args.run_attempt,
        "artifactName": args.artifact_name,
        "packageName": package.name,
        "packageSha256": package_hash,
        "packageSizeBytes": staged_package.stat().st_size,
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    (args.package_directory / "r7-package-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = package_manifest(staged_package)
    manifest_bytes = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    (args.provenance_directory / "package-manifest.json").write_bytes(manifest_bytes)
    verification = {
        "ankiaddonFilename": package.name,
        "ankiaddonSha256": package_hash,
        "packageManifestSha256": manifest_hash,
        "packageEntryCount": len(manifest),
        "zipIntegrityResult": "pass",
    }
    (args.provenance_directory / "package-verification.json").write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    package_names = sorted(path.name for path in args.package_directory.iterdir())
    if package_names != ["anki_study_report.ankiaddon", "r7-package-metadata.json"]:
        raise ValueError(f"unexpected package artifact inventory: {package_names}")

    outputs = {
        "package_sha256": package_hash,
        "manifest_sha256": manifest_hash,
        "entry_count": len(manifest),
        "artifact_name": args.artifact_name,
    }
    write_output(args.github_output, outputs)
    print(json.dumps(outputs, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"R7 package preparation error: {exc}", file=sys.stderr)
        raise SystemExit(1)
