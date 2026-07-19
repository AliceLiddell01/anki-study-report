from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WORKSPACE_ENV = "GAMIFICATION_SIM_RESEARCH_ROOT"
OUTPUT_ENV = "GAMIFICATION_SIM_OUTPUT_DIR"

_REQUIRED_MARKERS = (
    Path("pyproject.toml"),
    Path("schemas/review-scenario-v0.2.schema.json"),
    Path("schemas/review-longitudinal-v0.1.schema.json"),
    Path("schemas/review-sweep-v0.1.schema.json"),
    Path("schemas/review-persona-v0.1.schema.json"),
    Path("fixtures/golden_cases.json"),
    Path("rust-toolchain.toml"),
    Path("rust-oracle/Cargo.toml"),
    Path("rust-oracle/Cargo.lock"),
)


@dataclass(frozen=True, slots=True)
class ResearchWorkspace:
    root: Path

    @classmethod
    def validated(cls, root: Path) -> "ResearchWorkspace":
        candidate = root.expanduser()
        if candidate.is_symlink():
            raise ValueError(f"research workspace must not be a symlink: {candidate}")
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise ValueError(f"research workspace does not exist: {candidate}") from exc
        if not resolved.is_dir():
            raise ValueError(f"research workspace must be a directory: {resolved}")
        missing = [marker.as_posix() for marker in _REQUIRED_MARKERS if not (resolved / marker).is_file()]
        if missing:
            raise ValueError(
                f"invalid research workspace {resolved}: missing marker(s): {', '.join(missing)}"
            )
        return cls(resolved)

    def path(self, relative: str | Path) -> Path:
        requested = Path(relative)
        if requested.is_absolute() or ".." in requested.parts:
            raise ValueError(f"workspace path must be relative and bounded: {relative}")
        resolved = (self.root / requested).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError(f"workspace path escapes root: {relative}")
        current = self.root
        for part in requested.parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ValueError(f"workspace path traverses a symlink: {relative}")
        return resolved

    @property
    def schemas(self) -> Path:
        return self.path("schemas")

    @property
    def fixtures(self) -> Path:
        return self.path("fixtures")

    @property
    def scenarios(self) -> Path:
        return self.path("scenarios")

    @property
    def personas(self) -> Path:
        return self.path("personas")

    @property
    def configs(self) -> Path:
        return self.path("configs")

    @property
    def contracts(self) -> Path:
        return self.path("contracts")

    @property
    def rust_manifest(self) -> Path:
        return self.path("rust-oracle/Cargo.toml")


def _candidate_roots(anchor: Path) -> Iterable[Path]:
    candidate = anchor.expanduser()
    if candidate.exists() and candidate.is_file():
        candidate = candidate.parent
    try:
        resolved = candidate.resolve()
    except OSError:
        return
    for current in (resolved, *resolved.parents):
        yield current
        yield current / "research" / "gamification-sim"


def resolve_research_workspace(
    explicit: ResearchWorkspace | Path | str | None = None,
    *,
    anchors: Iterable[Path] = (),
) -> ResearchWorkspace:
    if isinstance(explicit, ResearchWorkspace):
        return explicit
    if explicit is not None:
        return ResearchWorkspace.validated(Path(explicit))

    configured = os.environ.get(WORKSPACE_ENV)
    if configured:
        return ResearchWorkspace.validated(Path(configured))

    seen: set[Path] = set()
    for anchor in (*anchors, Path.cwd()):
        for candidate in _candidate_roots(Path(anchor)):
            key = candidate.absolute()
            if key in seen:
                continue
            seen.add(key)
            try:
                return ResearchWorkspace.validated(candidate)
            except ValueError:
                continue

    raise ValueError(
        "unable to locate the Gamification research workspace; "
        f"pass --research-root or set {WORKSPACE_ENV}"
    )


def default_output_root() -> Path:
    configured = os.environ.get(OUTPUT_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return (
        Path(tempfile.gettempdir())
        / "anki-study-report"
        / "gamification-sim"
        / "outputs"
    ).resolve()


def cargo_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.setdefault("CARGO_TERM_COLOR", "never")
    return environment


def cargo_run_command(
    workspace: ResearchWorkspace | Path | str,
    *program_args: str,
) -> list[str]:
    resolved = resolve_research_workspace(workspace)
    cargo = shutil.which("cargo")
    if cargo is None:
        raise ValueError("cargo is not available through the active rustup environment")
    return [
        cargo,
        "run",
        "--quiet",
        "--locked",
        "--offline",
        "--manifest-path",
        str(resolved.rust_manifest),
        "--",
        *program_args,
    ]
