# Code scanning remediation record — 2026-07-13

## Status

The functional remediation is complete on commit
`095b5c22ffb8dff515301d2ea0f0e46a03f12fad`.

This record covers the eight High CodeQL findings reported against `master`:

- one `py/bad-tag-filter` finding;
- seven `py/path-injection` findings.

All findings were treated as valid security defects or valid unsafe trust-boundary
signals. No finding was dismissed, suppressed, marked `won't fix`, or hidden with a
CodeQL annotation.

The original default-branch alerts can only transition to closed after this PR is
merged and GitHub rescans the updated default branch. The PR scan has no unresolved
CodeQL review thread on the functional head.

## Remediation summary

### Rendered card HTML

Rendered card HTML no longer relies on regular expressions as the primary active
HTML filter. `note_intelligence.py` now parses the input with `HTMLParser`, emits
only an explicit tag and attribute allowlist, removes active/foreign content,
normalizes safe local media references, and restricts inline styles to an explicit
property/value policy.

The sanitizer rejects or removes, among other cases:

- `script`, `style`, `iframe`, `object`, `embed`, `svg`, `math`, `template`,
  `noscript`, and form content;
- inline event handlers and `srcset`;
- `javascript:`, `vbscript:`, `data:`, `file:`, remote URLs, and local paths;
- unsafe CSS constructs such as `url(...)`, `expression(...)`, `@import`,
  `behavior`, `position`, and `z-index`.

Legitimate Anki formatting, ruby markup, local image/audio references, replay
controls, and approved inline presentation styles remain supported.

### Dashboard media boundary

The HTTP server no longer accepts a provider-controlled filesystem path. The media
provider returns `(bytes, suffix)`, and the request handler writes those bytes
without performing a second path lookup.

The collection media lookup uses `TrustedLeafName`, which deliberately does not
implement `os.PathLike`. A request-derived name is only a validated leaf selector;
it resolves by exact match against a filesystem-discovered inventory of direct
regular files under the trusted collection media directory. Resolved targets are
rechecked for containment and file type. Traversal, absolute paths, Windows drive
or UNC forms, mixed separators, NUL bytes, nested files, missing files, and symlink
escapes fail closed.

### Dashboard static boundary

Request paths are decoded and validated before lookup. API paths, traversal,
absolute and UNC-like paths, Windows drive forms, mixed separators, empty/dot path
segments, encoded traversal, and NUL-bearing values are rejected.

Static responses are selected from a filesystem-discovered trusted inventory. SPA
fallback can return only the trusted `index.html`; missing `assets/...` requests do
not fall back to the application shell.

## Per-alert disposition

| Alert | Original sink | Disposition |
| --- | --- | --- |
| `Bad HTML filtering regexp #1` | `anki_study_report/note_intelligence.py`, regex removal of `script` near the former line 338 | **Fixed.** Replaced the regex security boundary with parser-based allowlist serialization and adversarial HTML tests. |
| `Uncontrolled data used in path expression #2` | `DashboardServerManager.media_file()`, former `target.is_file()` near `dashboard_server.py:453` | **Fixed.** The provider contract now returns bytes and a suffix, not a path. Legacy path-returning providers fail closed. |
| `Uncontrolled data used in path expression #3` | collection media path construction near former `__init__.py:2521` | **Fixed.** A validated `TrustedLeafName` selects an already discovered direct file from the trusted media inventory; request data is not joined into a filesystem path. |
| `Uncontrolled data used in path expression #4` | collection media file check near former `__init__.py:2526` | **Fixed.** Only a contained inventory target can be resolved and read; missing, nested, or escaped targets return no media. |
| `Uncontrolled data used in path expression #5` | `_send_file()` read near former `dashboard_server.py:1247` | **Fixed for the reported media flow.** Media uses `_send_bytes()`. Remaining static-file reads receive only trusted inventory targets. |
| `Uncontrolled data used in path expression #6` | static target construction near former `dashboard_server.py:1313` | **Fixed.** Removed request-derived path joining and replaced it with exact trusted-inventory selection. |
| `Uncontrolled data used in path expression #7` | static `target.is_dir()` near former `dashboard_server.py:1319` | **Fixed.** The directory-probing branch was removed; only indexed regular files can be returned. |
| `Uncontrolled data used in path expression #8` | static `target.is_file()` near former `dashboard_server.py:1321` | **Fixed.** File type and containment are established while building and rechecking the trusted inventory. |

GitHub Advanced Security raised two follow-up PR findings against the first version
of the media fix at `__init__.py:2523` and `__init__.py:2525`. The trusted leaf
selector removed the remaining request-data path expression. GitHub automatically
resolved both review threads after rescanning functional head
`095b5c22ffb8dff515301d2ea0f0e46a03f12fad`.

## Regression coverage

Security-focused tests cover:

- traversal and sibling-prefix attacks;
- encoded and double-encoded traversal at the HTTP boundary;
- POSIX absolute paths, Windows drive-relative/absolute paths, UNC forms, mixed
  separators, dot segments, and NUL bytes;
- symlink escape and nested-file rejection;
- provider attempts to return legacy filesystem paths;
- inventory refresh after media-directory changes;
- mixed-case and malformed active HTML, comments, foreign content, event handlers,
  obfuscated schemes, dangerous styles, and bounded output;
- preservation of legitimate Anki ruby, image, audio, replay, and inline-style
  behavior.

## Verification evidence

### Fast CI on the functional head

- Functional head: `095b5c22ffb8dff515301d2ea0f0e46a03f12fad`
- Run: `29266809711`
- Job: `86874322380`
- Result: success
- Frontend: 25 files, 149 tests passed
- Python: 248 passed, one expected package-artifact prebuild skip
- Package verification: passed
- Largest production chunk: 304,087 bytes, below the 500 kB guard

### Targeted real-Anki Cards gate

- Run: `29267131476`
- Job: `86875350437`
- Mode/scope: `standard/cards`
- Commit: `095b5c22ffb8dff515301d2ea0f0e46a03f12fad`
- Artifact digest:
  `sha256:f6bf9116b3cc4a7d5a02fdccb3936de57a591ea8eb59663ea3ca09814eb44863`
- Manifest: success
- Screenshots: 12/12
- APKG cards: 10/10 rendered through `anki_native`
- APKG media: 13/13 imported; checked image/audio responses loaded
- Console errors, page errors, actionable request failures: 0
- Card layout clipping/overlap failures: 0
- Document-level note CSS leakage after route changes: 0

### Final real-Anki full gate

- Run: `29267546355`
- Job: `86876740305`
- Mode/scope: `standard/full`
- Commit: `095b5c22ffb8dff515301d2ea0f0e46a03f12fad`
- Artifact digest:
  `sha256:03ccb24f73a851275052736784d011074b47ef193f399837f602f1ebf6f352e0`
- Manifest: success
- Anki: 26.05
- Screenshots: 86/86
  - 40 page captures;
  - 22 state captures;
  - 12 Cards captures;
  - 10 captures at 125% scale;
  - 2 navigation captures.
- First-start and restart health/asset/media smokes: passed
- APKG cards after first start and restart: 10/10 `anki_native`
- FSRS visual contract: 80/80 checks passed
- Console errors, page errors, actionable request failures: 0
- Visual review: no security-related or layout regression found

The raw server log contains five `BrokenPipeError` traces caused by Playwright
cancelling in-flight FSRS requests during navigation. The same five traces are
present in the preceding accepted full artifact, while the browser classifier
reports zero actionable request failures. They are not introduced by this security
change.

## Merge condition

The functional E2E evidence is tied exactly to
`095b5c22ffb8dff515301d2ea0f0e46a03f12fad`. Any later commit in this PR must be
documentation-only unless the affected checks are repeated. After this record is
committed, Fast CI must pass on the final documentation HEAD before merge.
