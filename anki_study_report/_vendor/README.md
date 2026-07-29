# Vendored runtime dependencies

This directory is packaged with the add-on so Anki does not need to install
Python packages at runtime.

- `tinycss2` 1.4.0 — parser used by the card CSS allowlist policy.
- `webencodings` 0.5.1 — upstream dependency of `tinycss2`.

The source files are unmodified upstream Python modules. `_vendor/__init__.py`
only exposes `webencodings` under the top-level import name expected by
`tinycss2`. License texts are stored in `licenses/`.
