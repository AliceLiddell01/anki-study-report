from __future__ import annotations

import os
from pathlib import Path

import pytest

from conftest import import_addon_module


def test_trusted_leaf_selector_resolves_existing_direct_file(tmp_path):
    path_safety = import_addon_module("path_safety")
    media_root = tmp_path / "collection.media"
    media_root.mkdir()
    media_file = media_root / "要望.mp3"
    media_file.write_bytes(b"audio")

    selector = path_safety.safe_leaf_name("要望.mp3")

    assert selector is not None
    assert selector == "要望.mp3"
    assert str(selector) == "要望.mp3"
    assert media_root / selector == media_file.resolve()
    assert (media_root / selector).read_bytes() == b"audio"


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "../front.gif",
        "nested/front.gif",
        "nested\\front.gif",
        "/tmp/front.gif",
        "C:/tmp/front.gif",
        "C:\\tmp\\front.gif",
        "C:front.gif",
        "\\\\server\\share\\front.gif",
        "front.gif\x00.txt",
    ],
)
def test_trusted_leaf_selector_rejects_non_leaf_values(value):
    path_safety = import_addon_module("path_safety")

    assert path_safety.safe_leaf_name(value) is None


def test_trusted_leaf_selector_fails_closed_for_missing_file(tmp_path):
    path_safety = import_addon_module("path_safety")
    media_root = tmp_path / "collection.media"
    media_root.mkdir()
    selector = path_safety.safe_leaf_name("missing.gif")

    assert selector is not None
    with pytest.raises(FileNotFoundError):
        _ = media_root / selector


def test_trusted_leaf_inventory_rejects_nested_and_symlink_escape(tmp_path):
    path_safety = import_addon_module("path_safety")
    media_root = tmp_path / "collection.media"
    nested = media_root / "nested"
    nested.mkdir(parents=True)
    (nested / "nested.gif").write_bytes(b"nested")

    nested_selector = path_safety.safe_leaf_name("nested.gif")
    assert nested_selector is not None
    with pytest.raises(FileNotFoundError):
        _ = media_root / nested_selector

    outside = tmp_path / "outside.gif"
    outside.write_bytes(b"outside")
    link = media_root / "linked.gif"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable in this environment")

    path_safety._trusted_leaf_inventory.cache_clear()
    linked_selector = path_safety.safe_leaf_name("linked.gif")
    assert linked_selector is not None
    with pytest.raises(FileNotFoundError):
        _ = media_root / linked_selector


def test_trusted_leaf_inventory_refreshes_after_directory_change(tmp_path):
    path_safety = import_addon_module("path_safety")
    media_root = tmp_path / "collection.media"
    media_root.mkdir()
    first = media_root / "first.gif"
    first.write_bytes(b"first")

    first_selector = path_safety.safe_leaf_name("first.gif")
    assert first_selector is not None
    assert media_root / first_selector == first.resolve()

    second = media_root / "second.gif"
    second.write_bytes(b"second")
    stat = media_root.stat()
    os.utime(
        media_root,
        ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000),
    )

    second_selector = path_safety.safe_leaf_name("second.gif")
    assert second_selector is not None
    assert media_root / second_selector == second.resolve()
