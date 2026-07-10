from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class ArtifactPaths:
    root: Path
    runtime: Path
    diagnostics: Path
    reports: Path
    html: Path
    screenshots: Path
    package: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "ArtifactPaths":
        resolved = Path(root)
        return cls(
            root=resolved,
            runtime=resolved / "runtime",
            diagnostics=resolved / "diagnostics",
            reports=resolved / "reports",
            html=resolved / "html",
            screenshots=resolved / "screenshots",
            package=resolved / "package",
        )

    @classmethod
    def from_env(cls) -> "ArtifactPaths":
        return cls.from_root(os.environ.get("ANKI_STUDY_REPORT_E2E_ARTIFACTS", "/e2e/artifacts"))

    def ensure(self) -> None:
        for directory in (
            self.root,
            self.runtime,
            self.diagnostics,
            self.reports,
            self.html,
            self.screenshots,
            self.package,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def relative(self, path: str | Path) -> str:
        return Path(path).relative_to(self.root).as_posix()

