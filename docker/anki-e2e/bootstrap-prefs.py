#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import pickle
import random
import sqlite3
import time
from typing import Any

from artifact_paths import ArtifactPaths


DEFAULT_PROFILE = "E2E"
PICKLE_PROTOCOL = 4


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Anki prefs21.db for Docker E2E.")
    parser.add_argument("--base-dir", type=Path, default=Path(os.environ.get("ANKI_BASE", "/e2e/anki-data")))
    parser.add_argument("--profile", default=os.environ.get("ANKI_PROFILE", DEFAULT_PROFILE))
    parser.add_argument("--profile-dir", type=Path)
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=ArtifactPaths.from_env().diagnostics,
    )
    parser.add_argument("--fresh", action="store_true", help="Remove stale prefs DB files before bootstrapping.")
    args = parser.parse_args()

    base_dir = args.base_dir
    profile = args.profile
    profile_dir = args.profile_dir or base_dir / profile
    artifacts_dir = args.artifacts_dir

    base_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if args.fresh:
        remove_stale_prefs(base_dir)

    prefs_path = base_dir / "prefs21.db"
    now = int(time.time())
    meta = build_meta(profile, now)
    profile_data = build_profile(now)

    with sqlite3.connect(prefs_path) as conn:
        conn.execute(
            """
            create table if not exists profiles (
                name text primary key collate nocase,
                data blob not null
            )
            """
        )
        conn.execute(
            "insert or replace into profiles (name, data) values (?, ?)",
            ("_global", pickle.dumps(meta, protocol=PICKLE_PROTOCOL)),
        )
        conn.execute(
            "insert or replace into profiles (name, data) values (?, ?)",
            (profile, pickle.dumps(profile_data, protocol=PICKLE_PROTOCOL)),
        )
        conn.commit()

    summary = summarize_prefs(prefs_path)
    summary["profileDir"] = str(profile_dir)
    summary["collectionPath"] = str(profile_dir / "collection.anki2")
    summary["globalKeys"] = sorted(meta)
    summary["profileKeys"] = sorted(profile_data)
    write_summary(artifacts_dir / "prefs21-summary.txt", summary)
    print(f"Bootstrapped Anki prefs: {prefs_path}")
    print(f"Profiles: {', '.join(row['name'] for row in summary['profiles'])}")
    return 0


def remove_stale_prefs(base_dir: Path) -> None:
    for name in (
        "prefs.db",
        "prefs.db-journal",
        "prefs21.db",
        "prefs21.db-journal",
        "prefs21.db-wal",
        "prefs21.db-shm",
    ):
        try:
            (base_dir / name).unlink()
        except FileNotFoundError:
            pass


def build_meta(profile: str, now: int) -> dict[str, Any]:
    return {
        "ver": 0,
        "updates": False,
        "created": now,
        "id": random.SystemRandom().randrange(1, 2**63),
        "lastMsg": 0,
        "suppressUpdate": True,
        "firstRun": False,
        "defaultLang": "en",
        "last_loaded_profile_name": profile,
        "check_for_updates": False,
        "check_for_addon_updates": False,
        "last_addon_update_check": now,
        "legacy_import": False,
    }


def build_profile(now: int) -> dict[str, Any]:
    return {
        "mainWindowGeom": None,
        "mainWindowState": None,
        "numBackups": 0,
        "lastOptimize": now,
        "searchHistory": [],
        "syncKey": None,
        "syncMedia": False,
        "autoSync": False,
        "allowHTML": False,
        "importMode": 1,
        "lastColour": "#00f",
        "stripHTML": True,
        "deleteMedia": False,
        "networkTimeout": 5,
        "browserTableTooltips": False,
        "autoSyncMediaMinutes": 0,
        "hostNum": 0,
        "syncUser": None,
        "currentSyncUrl": None,
        "customSyncUrl": None,
    }


def summarize_prefs(prefs_path: Path) -> dict[str, Any]:
    with sqlite3.connect(prefs_path) as conn:
        rows = conn.execute(
            """
            select name, length(cast(data as blob)) as blob_bytes
            from profiles
            order by case when name = '_global' then 0 else 1 end, name
            """
        ).fetchall()
    return {
        "prefsPath": str(prefs_path),
        "exists": prefs_path.is_file(),
        "pickleProtocol": PICKLE_PROTOCOL,
        "profiles": [{"name": name, "blobBytes": int(blob_bytes or 0)} for name, blob_bytes in rows],
    }


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "Anki E2E prefs21.db summary",
        f"prefsPath: {summary['prefsPath']}",
        f"exists: {summary['exists']}",
        f"pickleProtocol: {summary['pickleProtocol']}",
        "profiles:",
    ]
    for row in summary["profiles"]:
        lines.append(f"  - {row['name']}: blobBytes={row['blobBytes']}")
    lines.extend(
        [
            f"profileDir: {summary['profileDir']}",
            f"collectionPath: {summary['collectionPath']}",
            f"globalKeys: {json.dumps(summary['globalKeys'])}",
            f"profileKeys: {json.dumps(summary['profileKeys'])}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
