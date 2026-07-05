from __future__ import annotations

import argparse
from html.parser import HTMLParser
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = ROOT / "anki_study_report"
DEFAULT_OUTPUT = ROOT / "anki_study_report.ankiaddon"

REQUIRED_FILES = {
    "__init__.py",
    "manifest.json",
    "config.json",
    "dashboard_server.py",
    "web_dashboard/index.html",
}

FORBIDDEN_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "tests",
}

FORBIDDEN_PREFIXES = {
    "anki_study_report/",
    "web-dashboard/node_modules/",
    "web-dashboard/src/",
}

FORBIDDEN_SUFFIXES = {
    ".ankiaddon",
    ".pyc",
    ".pyo",
    ".zip",
}

DASHBOARD_CSS_MARKERS = (
    "[data-theme=light]",
    ".topbar-surface",
    ".shadow-panel",
    ".cards-risk-table",
    ".anki-card-shadow-preview",
)

MIN_DASHBOARD_ASSET_SIZE_BYTES = 1


@dataclass(frozen=True)
class ArchiveValidation:
    names: list[str]
    missing: list[str]
    forbidden: list[str]
    has_js_asset: bool
    has_css_asset: bool
    linked_assets: list[str]
    missing_linked_assets: list[str]
    empty_linked_assets: list[str]
    unreferenced_dashboard_assets: list[str]
    css_markers_missing: list[str]
    testzip_result: str | None

    @property
    def ok(self) -> bool:
        return (
            not self.missing
            and not self.forbidden
            and self.has_js_asset
            and self.has_css_asset
            and not self.missing_linked_assets
            and not self.empty_linked_assets
            and not self.unreferenced_dashboard_assets
            and not self.css_markers_missing
            and self.testzip_result is None
        )


def should_include(path: Path) -> bool:
    relative = path.relative_to(ADDON_DIR)
    parts = relative.parts
    if any(part in FORBIDDEN_DIR_NAMES for part in parts):
        return False
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return False
    if parts and parts[0] == "user_files":
        return False
    return path.is_file()


def build_archive(output: Path = DEFAULT_OUTPUT) -> Path:
    output = output.resolve()
    if not ADDON_DIR.is_dir():
        raise FileNotFoundError(f"Add-on directory not found: {ADDON_DIR}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    files = sorted(path for path in ADDON_DIR.rglob("*") if should_include(path))
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ADDON_DIR).as_posix())
    return output


def validate_archive(path: Path = DEFAULT_OUTPUT) -> ArchiveValidation:
    with ZipFile(path) as archive:
        names = sorted(archive.namelist())
        testzip_result = archive.testzip()
        index_html = archive.read("web_dashboard/index.html").decode("utf-8", errors="replace") if "web_dashboard/index.html" in names else ""
        sizes = {info.filename: info.file_size for info in archive.infolist()}
        linked_assets = sorted(extract_dashboard_asset_refs(index_html))
        css_payload = "\n".join(
            archive.read(name).decode("utf-8", errors="replace")
            for name in linked_assets
            if name.endswith(".css") and name in names
        )

    name_set = set(names)
    missing = sorted(REQUIRED_FILES - name_set)
    has_js_asset = any(
        name.startswith("web_dashboard/assets/") and name.endswith(".js")
        for name in names
    )
    has_css_asset = any(
        name.startswith("web_dashboard/assets/") and name.endswith(".css")
        for name in names
    )
    forbidden = [name for name in names if is_forbidden_archive_name(name)]
    missing_linked_assets = [name for name in linked_assets if name not in name_set]
    empty_linked_assets = [
        name
        for name in linked_assets
        if name in sizes and sizes[name] <= MIN_DASHBOARD_ASSET_SIZE_BYTES
    ]
    dashboard_assets = sorted(
        name
        for name in names
        if name.startswith("web_dashboard/assets/") and PurePosixPath(name).suffix.lower() in {".css", ".js"}
    )
    unreferenced_dashboard_assets = [name for name in dashboard_assets if name not in linked_assets]
    css_markers_missing = [marker for marker in DASHBOARD_CSS_MARKERS if marker not in css_payload]
    return ArchiveValidation(
        names=names,
        missing=missing,
        forbidden=forbidden,
        has_js_asset=has_js_asset,
        has_css_asset=has_css_asset,
        linked_assets=linked_assets,
        missing_linked_assets=missing_linked_assets,
        empty_linked_assets=empty_linked_assets,
        unreferenced_dashboard_assets=unreferenced_dashboard_assets,
        css_markers_missing=css_markers_missing,
        testzip_result=testzip_result,
    )


def is_forbidden_archive_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return True
    path = PurePosixPath(normalized)
    if any(part in FORBIDDEN_DIR_NAMES for part in path.parts):
        return True
    return path.suffix.lower() in FORBIDDEN_SUFFIXES


class DashboardAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.refs.append(values["src"] or "")
        if tag == "link" and values.get("href"):
            rel = str(values.get("rel") or "").lower()
            if "stylesheet" in rel:
                self.refs.append(values["href"] or "")


def extract_dashboard_asset_refs(index_html: str) -> list[str]:
    parser = DashboardAssetParser()
    parser.feed(index_html)
    refs: list[str] = []
    for raw_ref in parser.refs:
        ref = raw_ref.split("#", 1)[0].split("?", 1)[0].strip()
        if not ref:
            continue
        if ref.startswith("/"):
            ref = ref.lstrip("/")
        if ref.startswith("./"):
            ref = ref[2:]
        normalized = PurePosixPath(ref)
        if normalized.parts and normalized.parts[0] == "assets":
            refs.append(str(PurePosixPath("web_dashboard") / normalized))
    return sorted(set(refs))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate anki_study_report.ankiaddon.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Validate after building.")
    parser.add_argument("--check-only", action="store_true", help="Validate an existing archive without rebuilding.")
    args = parser.parse_args()

    output = args.output
    if not args.check_only:
        output = build_archive(output)
        print(f"Built {output}")

    if args.check or args.check_only:
        validation = validate_archive(output)
        print(f"Archive entries: {len(validation.names)}")
        print(f"Missing required entries: {validation.missing}")
        print(f"Forbidden entries: {validation.forbidden}")
        print(f"JS asset present: {validation.has_js_asset}")
        print(f"CSS asset present: {validation.has_css_asset}")
        print(f"Linked dashboard assets: {validation.linked_assets}")
        print(f"Missing linked dashboard assets: {validation.missing_linked_assets}")
        print(f"Empty linked dashboard assets: {validation.empty_linked_assets}")
        print(f"Unreferenced dashboard JS/CSS assets: {validation.unreferenced_dashboard_assets}")
        print(f"Missing dashboard CSS markers: {validation.css_markers_missing}")
        print(f"Zip test result: {validation.testzip_result}")
        if not validation.ok:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
