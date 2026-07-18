from __future__ import annotations

import math
from dataclasses import fields, is_dataclass
from typing import Any


TOLERANCE = 1e-9


def require_finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must not be NaN or infinity")
    return value


def require_range(name: str, value: float, minimum: float, maximum: float) -> float:
    value = require_finite(name, value)
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
    return value


def require_non_negative(name: str, value: float) -> float:
    value = require_finite(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def require_positive(name: str, value: float) -> float:
    value = require_finite(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def require_int(
    name: str,
    value: Any,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer without coercion")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return value


def require_non_negative_int(name: str, value: Any) -> int:
    return require_int(name, value, minimum=0)


def require_binary_int(name: str, value: Any) -> int:
    return require_int(name, value, minimum=0, maximum=1)


def close(a: float, b: float, tolerance: float = TOLERANCE) -> bool:
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)


def dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: dataclass_to_dict(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): dataclass_to_dict(item) for key, item in value.items()}
    if isinstance(value, frozenset):
        return sorted(dataclass_to_dict(item) for item in value)
    if hasattr(value, "value"):
        return value.value
    return value
