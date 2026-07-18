from __future__ import annotations

import math

import pytest

from gamification_sim.canonical_json import canonical_digest, canonical_dumps
from gamification_sim.strict_json import StrictJsonError, load_strict_json, loads_strict


def test_duplicate_key_rejected():
    with pytest.raises(StrictJsonError, match="duplicate object key: a"):
        loads_strict('{"a":1,"a":2}')


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_standard_numbers_rejected(constant):
    with pytest.raises(StrictJsonError, match="non-standard JSON number"):
        loads_strict(f'{{"value":{constant}}}')


def test_invalid_utf8_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_bytes(b"\xff")
    with pytest.raises(StrictJsonError, match="invalid UTF-8"):
        load_strict_json(path)


def test_bom_rejected(tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf{}")
    with pytest.raises(StrictJsonError, match="BOM"):
        load_strict_json(path)


def test_empty_file_rejected(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(" \n", encoding="utf-8")
    with pytest.raises(StrictJsonError, match="empty"):
        load_strict_json(path)


def test_oversized_file_rejected(tmp_path):
    path = tmp_path / "large.json"
    path.write_text('{"x":"12345"}', encoding="utf-8")
    with pytest.raises(StrictJsonError, match="exceeds 4 bytes"):
        load_strict_json(path, max_bytes=4)


def test_canonical_json_is_order_invariant_and_forbids_nan():
    assert canonical_dumps({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert canonical_digest({"b": 2, "a": 1}) == canonical_digest({"a": 1, "b": 2})
    with pytest.raises(ValueError):
        canonical_dumps({"value": math.nan})


def test_file_errors_include_source_path(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(StrictJsonError) as exc_info:
        load_strict_json(path)
    assert str(path) in str(exc_info.value)
    assert "duplicate object key" in str(exc_info.value)
