#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    from anki.collection import Collection

    profile_dir = Path(os.environ.get("ANKI_PROFILE_DIR", "/e2e/anki-data/E2E"))
    reports = Path(os.environ.get("ANKI_STUDY_REPORT_E2E_REPORTS_DIR", "/e2e/artifacts/reports"))
    collection_path = profile_dir / "collection.anki2"
    col = Collection(str(collection_path))
    try:
        model = next(
            (item for item in col.models.all() if str(item.get("name") or "") == "E2E Japanese Vocabulary"),
            None,
        )
        if not isinstance(model, dict):
            raise RuntimeError("E2E Japanese Vocabulary note type is missing")
        templates = model.get("tmpls")
        if not isinstance(templates, list) or not templates or not isinstance(templates[0], dict):
            raise RuntimeError("E2E Japanese Vocabulary template is missing")
        before = str(templates[0].get("qfmt") or "")
        if "{{Пример}}" not in before:
            templates[0]["qfmt"] = before + "\n<div>{{Пример}}</div>"
            update = getattr(col.models, "update_dict", None)
            if not callable(update):
                raise RuntimeError("Anki model update API is unavailable")
            update(model)
        proof = {
            "ok": True,
            "noteTypeName": "E2E Japanese Vocabulary",
            "change": "front_template_field_reference_added",
            "fieldReference": "Пример",
        }
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "inspection-profile-structure-mutation.json").write_text(
            json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    finally:
        close = getattr(col, "close", None)
        if callable(close):
            try:
                close(save=True)
            except TypeError:
                close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
