from __future__ import annotations

import hashlib
import json
from typing import Any

from .validation import dataclass_to_dict


def canonical_dumps(value: Any) -> str:
    return json.dumps(
        dataclass_to_dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_dumps(value).encode("utf-8")).hexdigest()
