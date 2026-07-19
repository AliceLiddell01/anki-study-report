# C1.5R.2 — Declarative compact formatter runtime

## Status

**Baseline branch:** `core`

**Initial HEAD:** `d9eed2d057a8c74ae8a694aa9f4a1e8309931421`

**Initial synchronization:** `origin/core 0 behind / 0 ahead`

**Initial master divergence:** `0 behind / 72 ahead`

**Open PRs from core:** none

**Verified implementation commit:** `edad09e8ffae443b94e192b266084abb66c37adf`

**Post-push synchronization:** `origin/core 0 behind / 0 ahead`

**Verified implementation master divergence:** `0 behind / 73 ahead`

**Current stage status:** `Complete`

This report records the completed implementation and owner-checkout
verification of C1.5R.2. The verified implementation tree was committed unchanged
and pushed to `origin/core` as `edad09e8ffae443b94e192b266084abb66c37adf`. No PR, merge, release,
deployment, AnkiWeb publication or work outside Core was performed.

## Scope implemented

### Independent schema and store

- `schemas/card-display-formatter-v1.schema.json`, Draft 2020-12;
- root/nested `additionalProperties: false`;
- independent schema version and no Inspection Profile v1 extension;
- strict positive signed-64 IDs, template ordinal/null coherence, enums,
  timestamps and bounded strings/lines/characters;
- duplicate `(noteTypeId, templateOrdinal)` and 33-per-note-type enforcement;
- 1 MiB/1000-entry document bounds;
- deterministic UTF-8 JSON and same-directory temp/flush/fsync/replace writes;
- monotonic revision and expected-revision conflicts;
- missing/empty, corrupt quarantine, future preserve/reject-write and unavailable
  states.

### Resolver and compact runtime

- immutable request snapshot resolver;
- exact enabled precedence;
- exact disabled inheritance suppression;
- note-type default fallback;
- canonical R1 fallback for absent/disabled/bad store or invalid/empty output;
- ordered `text`, `line_break`, `image`, `audio` tokens;
- allowlisted text/image/audio modes and fixed 🖼/🔊 markers;
- bounded safe flat local media filename/stem extraction after entity decoding;
- no file existence/read, path resolution or remote load;
- Browser/reviewer render cache with at most one render per source;
- no `card.answer()` call.

### Search/Triage integration

- formatter store read once per Search query/inspect request;
- formatter store read once per Triage request;
- resolver explicitly threaded to Search exact-card projection;
- Triage reuses Search-owned `resolve_card_rows()` path;
- Search query/inspect remains schema v2;
- Search metadata remains v1;
- Triage remains schema v3;
- no formatter keys or card `primaryText` alias added to wire payloads.

### Local API and frontend contract

Token-protected POST-only JSON endpoints:

```text
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
```

They use exact schema v1, strict actions, 64 KiB cap, generic errors and current
revision conflicts. Validate performs no collection read and no persistence.

Frontend adds strict types/parser/client and tests only. No route, page, hook,
Settings navigation, form, suggestion, preview API or import/export UI is added.

### Package integration

The package builder requires and includes:

```text
card_display_formatter_store.py
card_display_formatter_service.py
card_display_formatter_runtime.py
schemas/card-display-formatter-v1.schema.json
```

Generated dashboard assets remain build outputs and are not edited manually.

## Exact acceptance examples

```text
default:
【に】（する）

configured:
【に】感謝（する）

Programming note type without an ID-bound formatter:
unchanged
```

## Security properties

```text
no arbitrary code
no regex/query language
no dynamic import/callback/subprocess
no media file reads or existence checks
no remote loads
no raw HTML/note values in formatter store
no path or token leaks
no filename/generated displayText telemetry
```

## Verification

### Tracked-snapshot reconstruction

The initial implementation was reviewed against the exact tracked archive from
`d9eed2d057a8c74ae8a694aa9f4a1e8309931421`. Before owner-checkout execution:

```text
Python compile: PASS
Focused formatter/Search/Triage backend: 104 passed
Formatter/Inspection HTTP subset: 2 passed, 20 deselected
Existing Search/Triage regression contour: 61 passed
Isolated strict production TypeScript check: PASS
```

### Owner-checkout focused verification

The owner applied the baseline-specific patch on `core`. One legacy test double in
`tests/test_search_metadata.py` still accepted two arguments while production now
passes the explicit formatter resolver as a third argument. The correction changed
the test only; production behavior did not change.

```text
Python compile: PASS — 162 ms
Focused backend rerun: 142 passed — 12,103 ms
Focused frontend: 6 files, 49 tests passed — 9,267 ms
TypeScript typecheck: PASS — 11,086 ms
Vite production build: PASS — 2,258 modules
Bundle guard: PASS — 17 JS chunks
Dashboard asset synchronization: PASS
```

Independent package validation also passed:

```text
archive entries: 72
missing required entries: []
forbidden entries: []
missing/empty/unreferenced linked assets: []
asset graph/unsafe reference/CSS marker errors: []
ZIP test result: None
canonical package version: 1.2.0
validated package SHA-256:
8B723B2E1ED5883B895A9A36018C8D7CE5E2388971C622CB47A0C076B3EF10C0
```

### Canonical non-Docker gate

The first `run_full_check.ps1 -SkipDocker` attempt reached the full Python suite
and reported one hygiene failure because the earlier explicit `compileall` command
had created `anki_study_report/__pycache__`. The generated bytecode directory was
removed; no production or test behavior was changed. The clean rerun passed:

```text
frontend typecheck: PASS
frontend tests: 55 files, 279 tests passed
production build and bundle guard: PASS
Python tests: 772 passed, 5 environment-only skips
package build and verification: PASS
full check exit code: 0
duration: 68,916 ms
git diff --check: PASS
```

The remaining pytest cache warning was environment-only: Windows denied creation
of the repository-level `.pytest_cache`. It did not affect the successful exit
code or test results.

### Git closeout

The verified tree was staged through an explicit 42-path allowlist with no
unexpected or missing paths and no unstaged tracked changes. It was committed and
pushed as:

```text
edad09e8ffae443b94e192b266084abb66c37adf — feat: add declarative compact formatter runtime
origin/core synchronization: 0 behind / 0 ahead
tracked working tree: clean
index: clean
```

Fast CI, Docker, real-Anki E2E, visual acceptance and owner private-profile review
were not required for R2 and were deliberately not run. C1.5R.2 technical
completion does not grant product acceptance to later C1.5R UI stages.

## Scope explicitly not implemented

```text
front/back preview semantics
candidate-source changes
Cards inbox/drawer redesign
guided Inspection Profiles UX
automatic formatter suggestions
live formatter preview API
C1.6 actions/recheck/resolution
PR, merge, release or deployment
```

## Git boundary

The candidate is based only on exact tracked HEAD. The unrelated untracked
Gamification helper scripts reported by the owner are outside the patch and must
remain untouched. No PR, merge, rebase, force-push, release, deployment or
AnkiWeb publication is part of this stage.

## Next stage

C1.5R.3 is now **Next, not started**. It owns front/back preview semantics while
preserving sanitizer, media validation, Shadow DOM and single-active-card reads.
C1.6 remains blocked until the complete C1.5R remediation and separate owner
product acceptance are finished.
