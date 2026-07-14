from __future__ import annotations

import subprocess

from conftest import ROOT


def test_ankiweb_publisher_node_contracts():
    subprocess.run(
        ["node", "--test", "tests/publish_ankiweb.test.mjs"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_publisher_has_no_secret_or_authenticated_artifact_outputs():
    source = (ROOT / "scripts" / "publish_ankiweb.mjs").read_text(encoding="utf-8")
    assert "process.env.ANKIWEB_EMAIL" in source
    assert "process.env.ANKIWEB_PASSWORD" in source
    assert "process.env.RUNNER_TEMP || os.tmpdir()" in source
    for forbidden in ("storageState", "screenshot(", "tracing.start", "recordVideo", "page.content("):
        assert forbidden not in source
    assert "Add New Branch" in source
    assert ".click()" not in source.split('name: "Add New Branch"', 1)[1].split("return", 1)[0]
