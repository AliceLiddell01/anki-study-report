# C1.5R.2 — Declarative compact formatter runtime

## Status

**Baseline branch:** `core`

**Initial HEAD:** `d9eed2d057a8c74ae8a694aa9f4a1e8309931421`

**Initial synchronization:** `origin/core 0 behind / 0 ahead`

**Initial master divergence:** `0 behind / 72 ahead`

**Open PRs from core:** none

**Current stage status:** `Implemented, canonical non-Docker verification pending`

This report records the reviewed implementation candidate built from the exact
tracked HEAD archive supplied by the owner. It does not declare Complete before
the patch is applied and all required checks pass on the owner's local checkout.

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

## Verification performed in tracked-snapshot reconstruction

The reconstruction contains tracked source only and does not contain ignored
built dashboard assets. Results are implementation evidence, not the final
owner-checkout completion gate.

```text
Python compile:
python -m compileall -q anki_study_report
PASS

Focused formatter/Search/Triage backend contour:
104 passed

Focused formatter/Inspection HTTP endpoint subset:
2 passed, 20 deselected

Existing Search/Triage regression contour before additional hardening:
61 passed

Isolated strict production TypeScript check:
tsc --noEmit --strict ... cardDisplayFormatters types/client
PASS
```

Two full `test_dashboard_server.py` cases and one real package-build case cannot
be accepted from the tracked archive because generated `web_dashboard` assets
are intentionally absent there. The new formatter endpoint test itself passes.
`pnpm` cannot fetch Corepack metadata in the isolated environment, so focused
Vitest and full project typecheck remain owner-checkout gates.

## Required verification still pending

Run on the owner's local `core` checkout after patch application:

```text
Python compile
full focused Python contour
focused formatter/search/triage Vitest contour
pnpm run typecheck
package validation
.\scripts\run_full_check.ps1 -SkipDocker
git diff --check and final hygiene
```

Fast CI, Docker, real-Anki E2E, visual acceptance and owner private profile are
not required for R2 and remain deliberately untested.

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

C1.5R.3 remains blocked until R2 focused frontend, package and canonical
non-Docker verification pass, the report receives exact final-HEAD evidence, and
changes are pushed to `origin/core`.
