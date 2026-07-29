#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import zipfile
from typing import Any

FINAL_NAME = "cards-final-av-media-fidelity-evidence.zip"
REQUIRED_REPORTS = (
    "exact-scenario.json",
    "exact-api.json",
    "exact-browser.json",
    "page-console-summary.json",
    "request-ledger.json",
    "geometry-metrics.json",
)
CONTENT_DIRS = ("oracle", "production", "comparisons", "semantic", "diagnostics", "provenance")


def required_env(name: str) -> str:
    value = str(os.environ.get(name, "")).strip()
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Required JSON is missing: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Required JSON is not an object: {path.name}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_exact(source: Path, destination: Path, expected_sha: str | None = None) -> dict[str, Any]:
    if not source.is_file():
        raise RuntimeError(f"Required source is missing or not a file: {source.name}")
    actual = sha256_file(source)
    if expected_sha and actual != expected_sha:
        raise RuntimeError(
            f"Source SHA mismatch for {source.name}: expected={expected_sha} actual={actual}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {"artifactName": destination.name, "sizeBytes": destination.stat().st_size, "sha256": actual}


def command_version(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"unavailable:{type(error).__name__}"
    line = (completed.stdout or "").strip().splitlines()
    return line[0][:240] if line else f"exit={completed.returncode}"


def safe_zip_name(value: str) -> str:
    path = Path(str(value).replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or any(part in {"", "."} for part in path.parts):
        raise RuntimeError(f"Unsafe ZIP member path: {value}")
    return path.as_posix()


def file_inventory(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    exclude = exclude or set()
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in exclude:
            continue
        rows.append(
            {
                "path": relative,
                "sizeBytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def write_manifest(root: Path) -> dict[str, Any]:
    rows = file_inventory(root, exclude={"manifest.json", "SHA256SUMS"})
    manifest = {
        "schemaVersion": 1,
        "artifact": FINAL_NAME,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hashAlgorithm": "sha256",
        "fileCount": len(rows),
        "files": rows,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checksummed = file_inventory(root, exclude={"SHA256SUMS"})
    (root / "SHA256SUMS").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in checksummed),
        encoding="utf-8",
    )
    return manifest


def build_zip(root: Path, output: Path) -> None:
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())


def verify_extracted(root: Path) -> dict[str, Any]:
    manifest = read_json(root / "manifest.json")
    expected_rows = manifest.get("files")
    if not isinstance(expected_rows, list):
        raise RuntimeError("manifest.files is missing")
    expected = {str(row["path"]): row for row in expected_rows if isinstance(row, dict)}
    actual_content = {
        row["path"]: row
        for row in file_inventory(root, exclude={"manifest.json", "SHA256SUMS"})
    }
    missing = sorted(set(expected) - set(actual_content))
    unexpected = sorted(set(actual_content) - set(expected))
    mismatches = sorted(
        path
        for path in set(expected) & set(actual_content)
        if int(expected[path].get("sizeBytes", -1)) != actual_content[path]["sizeBytes"]
        or str(expected[path].get("sha256")) != actual_content[path]["sha256"]
    )

    sums: dict[str, str] = {}
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if not separator:
            raise RuntimeError(f"Malformed SHA256SUMS line: {line!r}")
        sums[safe_zip_name(name)] = digest
    actual_sums = {
        row["path"]: row["sha256"]
        for row in file_inventory(root, exclude={"SHA256SUMS"})
    }
    sums_missing = sorted(set(actual_sums) - set(sums))
    sums_unexpected = sorted(set(sums) - set(actual_sums))
    sums_mismatches = sorted(
        path for path in set(sums) & set(actual_sums) if sums[path] != actual_sums[path]
    )
    result = {
        "status": "PASS"
        if not (missing or unexpected or mismatches or sums_missing or sums_unexpected or sums_mismatches)
        else "FAIL",
        "manifest": {
            "missing": missing,
            "unexpected": unexpected,
            "mismatches": mismatches,
        },
        "sha256sums": {
            "missing": sums_missing,
            "unexpected": sums_unexpected,
            "mismatches": sums_mismatches,
        },
    }
    if result["status"] != "PASS":
        raise RuntimeError(f"Final artifact self-verification failed: {json.dumps(result)}")
    return result


def verify_zip(output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cards-exact-verify-") as temp:
        extraction = Path(temp)
        with zipfile.ZipFile(output, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"ZIP CRC failure: {bad}")
            for member in archive.infolist():
                safe_zip_name(member.filename)
            archive.extractall(extraction)
        result = verify_extracted(extraction)
        result.update(
            {
                "zipCrc": "PASS",
                "zipSha256": sha256_file(output),
                "zipSizeBytes": output.stat().st_size,
                "zipMemberCount": len(list(extraction.rglob("*"))),
            }
        )
        return result


def sanitized_environment() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "status": "PASS",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "runtime": {
            "python": platform.python_version(),
            "node": command_version(["node", "--version"]),
            "pnpm": command_version(["pnpm", "--version"]),
            "playwright": command_version(["node", "-e", "console.log(require('playwright/package.json').version)"]),
            "anki": os.environ.get("ANKI_VERSION", "unknown"),
        },
        "browser": {
            "headless": True,
            "locale": "en-US",
            "timezone": "UTC",
            "deviceScaleFactor": 1,
        },
        "container": {
            "imageReference": os.environ.get("ANKI_E2E_IMAGE_REFERENCE", "unknown"),
            "imageId": os.environ.get("ANKI_E2E_IMAGE_ID", "unknown"),
        },
        "git": {
            "packageTestedCommitSha": required_env("ANKI_E2E_FAST_CI_TESTED_SHA"),
            "harnessCommitSha": required_env("ANKI_E2E_HARNESS_SHA"),
            "reuseMode": os.environ.get("ANKI_E2E_REUSE_MODE", "harness-only"),
        },
    }


def copy_reference_zip(source: Path, destination: Path, expected_sha: str, label: str) -> dict[str, Any]:
    row = copy_exact(source, destination, expected_sha)
    with zipfile.ZipFile(source, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"{label} ZIP CRC failure: {bad}")
        unsafe = []
        for member in archive.infolist():
            try:
                safe_zip_name(member.filename)
            except RuntimeError:
                unsafe.append(member.filename)
        if unsafe:
            raise RuntimeError(f"{label} ZIP contains unsafe members: {unsafe}")
        row.update({"memberCount": len(archive.infolist()), "crc": "PASS"})
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the final Cards exact AV/media evidence ZIP.")
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--profile-dir", required=True, type=Path)
    args = parser.parse_args()

    artifacts = args.artifacts.resolve()
    reports = artifacts / "reports"
    screenshots = artifacts / "screenshots"
    diagnostics = artifacts / "diagnostics"
    package = artifacts / "package" / "anki_study_report.ankiaddon"
    output = artifacts / FINAL_NAME

    exact = {name: read_json(reports / name) for name in REQUIRED_REPORTS}
    for name, value in exact.items():
        if value.get("status") != "PASS":
            raise RuntimeError(f"Cannot package non-PASS report: {name}")

    package_source = os.environ.get("ANKI_E2E_PACKAGE_SOURCE", "source-build")
    actual_package_sha = sha256_file(package)
    if package_source == "source-build":
        exact_package_sha = actual_package_sha
        tested_commit_sha = required_env("ANKI_E2E_HARNESS_SHA")
        fast_ci_run_id = None
    else:
        exact_package_sha = required_env("ANKI_E2E_FAST_CI_PACKAGE_SHA256")
        tested_commit_sha = required_env("ANKI_E2E_FAST_CI_TESTED_SHA")
        fast_ci_run_id = required_env("ANKI_E2E_FAST_CI_RUN_ID")
    exact_apkg = Path(required_env("ANKI_E2E_EXACT_APKG_PATH"))
    exact_apkg_sha = required_env("ANKI_E2E_EXACT_APKG_SHA256")
    media_dir = args.profile_dir / "collection.media"
    media_contract = {
        required_env("ANKI_E2E_EXACT_GIF_NAME"): required_env("ANKI_E2E_EXACT_GIF_SHA256"),
        required_env("ANKI_E2E_EXACT_MP3_NAME"): required_env("ANKI_E2E_EXACT_MP3_SHA256"),
        required_env("ANKI_E2E_EXACT_PNG_NAME"): required_env("ANKI_E2E_EXACT_PNG_SHA256"),
    }
    reference_audit = Path(required_env("ANKI_E2E_EXACT_REFERENCE_AUDIT_ZIP"))
    reference_prototype = Path(required_env("ANKI_E2E_EXACT_REFERENCE_PROTOTYPE_ZIP"))

    with tempfile.TemporaryDirectory(prefix="cards-exact-evidence-") as temp:
        root = Path(temp) / "cards-final-av-media-fidelity-evidence"
        for directory in CONTENT_DIRS:
            (root / directory).mkdir(parents=True, exist_ok=True)

        copy_exact(package, root / "production/anki_study_report.ankiaddon", exact_package_sha)
        copy_exact(exact_apkg, root / "oracle/words-n1.apkg", exact_apkg_sha)

        media_rows = {}
        for name, expected_sha in media_contract.items():
            media_rows[name] = copy_exact(
                media_dir / name,
                root / "oracle/media" / name,
                expected_sha,
            )

        reference_rows = {
            "visualAudit": copy_reference_zip(
                reference_audit,
                root / "oracle/cards-visual-parity-and-profiles-audit-evidence.zip",
                required_env("ANKI_E2E_EXACT_REFERENCE_AUDIT_SHA256"),
                "visual audit reference",
            ),
            "prototype": copy_reference_zip(
                reference_prototype,
                root / "oracle/pr130_visual_prototype_v3_2_3.zip",
                required_env("ANKI_E2E_EXACT_REFERENCE_PROTOTYPE_SHA256"),
                "prototype reference",
            ),
        }

        semantic_map = {
            "exact-scenario.json": "semantic/exact-scenario.json",
            "exact-api.json": "semantic/exact-api.json",
            "exact-browser.json": "semantic/exact-browser.json",
            "geometry-metrics.json": "semantic/geometry-metrics.json",
            "page-console-summary.json": "diagnostics/page-console-summary.json",
            "request-ledger.json": "diagnostics/request-ledger.json",
        }
        for source_name, destination in semantic_map.items():
            copy_exact(reports / source_name, root / destination)

        if diagnostics.is_dir():
            for source in sorted(diagnostics.rglob("*")):
                if not source.is_file() or source.is_symlink():
                    continue
                relative = source.relative_to(diagnostics)
                if any(part in {"..", ""} for part in relative.parts):
                    continue
                copy_exact(source, root / "diagnostics/runtime" / relative)

        production_screenshots = root / "production/screenshots"
        exact_screenshots = screenshots / "cards/exact-av-media"
        for source in sorted(exact_screenshots.rglob("*.png")):
            relative_screenshot = source.relative_to(exact_screenshots)
            copy_exact(source, production_screenshots / relative_screenshot)
        contact_source = reports / "cards-exact-contact-sheet.png"
        copy_exact(contact_source, root / "contact-sheet.png")

        environment = sanitized_environment()
        (root / "provenance/environment.json").write_text(
            json.dumps(environment, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        provenance = {
            "schemaVersion": 1,
            "status": "PASS",
            "cardId": int(required_env("ANKI_E2E_EXACT_CARD_ID")),
            "word": required_env("ANKI_E2E_EXACT_WORD"),
            "package": {
                "source": package_source,
                "sha256": exact_package_sha,
                "testedCommitSha": tested_commit_sha,
                "fastCiRunId": fast_ci_run_id,
            },
            "harness": {
                "sha": required_env("ANKI_E2E_HARNESS_SHA"),
                "scope": "cards-exact-av-media",
                "reuseMode": os.environ.get("ANKI_E2E_REUSE_MODE", "harness-only"),
            },
            "apkg": {"name": exact_apkg.name, "sha256": exact_apkg_sha},
            "media": media_rows,
            "references": reference_rows,
            "render": {
                "frontHtmlSha256": exact["exact-api.json"]["renderedPreview"]["frontHtmlSha256"],
                "backHtmlSha256": exact["exact-api.json"]["renderedPreview"]["backHtmlSha256"],
                "cssSha256": exact["exact-api.json"]["renderedPreview"]["cssSha256"],
            },
        }
        (root / "provenance/provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        browser = exact["exact-browser.json"]
        comparison = {
            "schemaVersion": 1,
            "status": "PASS",
            "policy": (
                "Production screenshots and deterministic frame are preserved byte-for-byte. "
                "Historical visual-audit and prototype references are preserved as validated source ZIPs; "
                "no screenshot-specific transform or synthetic media substitution is applied."
            ),
            "productionScreenshots": [
                row.get("path") for row in browser.get("screenshots", []) if isinstance(row, dict)
            ],
            "responsiveMatrix": browser.get("responsiveMatrix"),
            "interactionGallery": browser.get("interactionGallery"),
            "deterministicGifFrame": browser.get("deterministicFrame"),
            "animatedGif": browser.get("animation"),
            "referenceArtifacts": reference_rows,
        }
        (root / "comparisons/comparison-index.json").write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        known = """# Известные различия

- Визуальный raster зависит от зафиксированного Playwright Chromium/Linux/font окружения; это не подменяет native Anki render provenance.
- Реальная GIF-анимация доказана временными browser captures, а детерминированное сравнение использует отдельно декодированный frame 0 без изменения production media.
- Historical prototype и visual-audit evidence сохраняются как исходные проверенные ZIP. Final artifact не модифицирует их изображения.
- Acceptance владельца и переход к Inspection Profiles не входят в этот запуск.
"""
        (root / "known-differences.md").write_text(known, encoding="utf-8")

        summary_path = root / "targeted-run-summary.json"
        summary = {
            "schemaVersion": 1,
            "status": "PASS",
            "scope": "cards-exact-av-media",
            "cardId": int(required_env("ANKI_E2E_EXACT_CARD_ID")),
            "scenarios": len(browser.get("scenarios", [])),
            "screenshots": len(browser.get("screenshots", [])),
            "responsiveMatrix": browser.get("responsiveMatrix"),
            "interactionGallery": browser.get("interactionGallery"),
            "audioReplay": browser.get("replay"),
            "gifAnimation": browser.get("animation"),
            "deterministicFrame": browser.get("deterministicFrame"),
            "externalRequests": browser.get("externalRequests"),
            "inspectionProfilesRequests": browser.get("inspectionProfilesRequests"),
            "pageErrors": browser.get("pageErrors"),
            "consoleErrors": browser.get("consoleErrors"),
            "failedRequests": browser.get("failedRequests"),
            "selfVerification": {"status": "PENDING"},
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        readme = f"""# Cards final exact AV/media fidelity evidence

- Status: PASS
- Scope: `cards-exact-av-media`
- Card: `{required_env("ANKI_E2E_EXACT_CARD_ID")}` (`{required_env("ANKI_E2E_EXACT_WORD")}`)
- Package SHA-256: `{exact_package_sha}`
- Harness SHA: `{required_env("ANKI_E2E_HARNESS_SHA")}`
- Responsive matrix: `1920x1080`, `2560x1440`, `3840x2160` at DSF 1, viewport-only, light theme
- Interaction gallery: primary `1920x1080` viewport plus expanded-answer and refresh close-ups
- Inspection Profiles requests: `0`
- External requests: `0`

This package contains exact real-Anki API/browser results, production screenshots,
audio/GIF/media provenance, geometry, diagnostics, validated historical references,
and a self-verifying manifest/checksum contract.
"""
        (root / "README.md").write_text(readme, encoding="utf-8")

        write_manifest(root)
        build_zip(root, output)
        first_verification = verify_zip(output)

        summary["selfVerification"] = {
            "status": first_verification["status"],
            "zipCrc": first_verification["zipCrc"],
            "manifest": first_verification["manifest"],
            "sha256sums": first_verification["sha256sums"],
        }
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        write_manifest(root)
        build_zip(root, output)
        final_verification = verify_zip(output)

    external_report = {
        "schemaVersion": 1,
        "status": "PASS",
        "artifact": FINAL_NAME,
        "sha256": sha256_file(output),
        "sizeBytes": output.stat().st_size,
        "verification": final_verification,
    }
    (reports / "cards-exact-av-media-self-verification.json").write_text(
        json.dumps(external_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"[cards-exact] evidence PASS zip={FINAL_NAME} size={output.stat().st_size} "
        f"sha256={external_report['sha256']} missing=0 unexpected=0 mismatches=0",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
