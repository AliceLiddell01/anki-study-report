from __future__ import annotations

import json
from typing import Any

from .validation import dataclass_to_dict


def to_dict(value: Any) -> Any:
    return dataclass_to_dict(value)


def to_json(value: Any, *, indent: int = 2) -> str:
    return json.dumps(to_dict(value), ensure_ascii=False, indent=indent, sort_keys=True)
