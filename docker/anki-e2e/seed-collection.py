#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an empty disposable Anki E2E collection.")
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    args = parser.parse_args()

    profile_dir = args.profile_dir
    artifacts_dir = args.artifacts_dir
    profile_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    collection_path = profile_dir / "collection.anki2"
    media_dir = profile_dir / "collection.media"

    for path in (
        collection_path,
        collection_path.with_suffix(".anki2-wal"),
        collection_path.with_suffix(".anki2-shm"),
    ):
        path.unlink(missing_ok=True)
    shutil.rmtree(media_dir, ignore_errors=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    from anki.collection import Collection

    col = Collection(str(collection_path))
    close = getattr(col, "close", None)
    if callable(close):
        try:
            close(save=True)
        except TypeError:
            close()

    summary = {
        "schemaVersion": 1,
        "status": "PASS",
        "collection": "collection.anki2",
        "content": {
            "decksCreatedByHarness": 0,
            "noteTypesCreatedByHarness": 0,
            "notesCreatedByHarness": 0,
            "cardsCreatedByHarness": 0,
            "templatesCreatedByHarness": 0,
            "mediaCreatedByHarness": 0,
            "revlogRowsCreatedByHarness": 0,
        },
        "nextStage": "mandatory real-deck import",
        "syntheticFallback": False,
    }
    (artifacts_dir / "empty-collection-bootstrap.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[real-decks] empty collection created: {collection_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
