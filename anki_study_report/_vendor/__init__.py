"""Private, packaged third-party dependencies used by the add-on runtime."""

from __future__ import annotations

import sys

from . import webencodings as _webencodings


# tinycss2 imports its small webencodings dependency by its upstream top-level
# name. Keep both projects private to the add-on while preserving upstream code.
sys.modules.setdefault("webencodings", _webencodings)
