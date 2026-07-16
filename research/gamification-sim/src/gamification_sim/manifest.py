from __future__ import annotations

import sys

SIMULATOR_VERSION = "scenario-runner-v0.1"
SCENARIO_SCHEMA_VERSION = "review-scenario-v0.1"


def python_major_minor() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"
