# C1.5R.1 — Canonical card display identity

**Date:** 2026-07-19

**Branch:** `core`

**Baseline:** `219fe515ef58e55bc3b8866b4ec4832148126df3`

**Tested implementation HEAD:** `a46116e43756eceb3820f4eca76b28645a54a3ff`

**Documentation closeout HEAD:** recorded by the Markdown-only closeout commit

**Status:** Complete

## Purpose

C1.5R.1 corrects compact card identity without absorbing later remediation
stages. One exact-card backend projector now supplies Search, Triage and current
Cards surfaces. Arbitrary note sort/first-non-empty fields are no longer used as
card identity.

This report is the focused verification closeout for C1.5R.1. It does not
constitute owner product acceptance for the complete C1.5R remediation.

## Scope completed

### Backend projector

Added:

```text
anki_study_report/card_display_identity.py
```

The projector uses this precedence:

```text
native Browser question
→ native reviewer front
→ explicit media_only or unavailable state
```

It:

- projects the first meaningful rendered line;
- removes sound/Anki playback markers;
- treats media elements as media without exposing filenames or URLs;
- drops scripts, styles and unsafe embedded content;
- preserves adjacent inline Japanese text without invented spaces;
- collapses whitespace and decodes entities;
- bounds text to 240 characters with one ellipsis;
- fails closed for malformed blocked markup;
- never scans arbitrary note fields;
- never renders answer/back;
- never reads media files;
- never exposes renderer exceptions.

The exact media-heavy Japanese fixture produces:

```text
【に】（する）
```

and not the unrelated sort-field value:

```text
「Существительное」
```

### Search schema v2

Normal Search query and inspect requests/responses now require exact
`schemaVersion: 2`.

Card rows/details contain:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

Card `primaryText` is removed. Note rows/details retain note-mode `primaryText`.
Search metadata remains an independent schema v1 variant.

Search card rows, Search card inspect and exact-card resolution all reuse the
same Python card projector.

### Triage schema v3

Triage request/response now require exact `schemaVersion: 3`.

Triage items carry the same four display fields and no `primaryText`. Available
items copy Search exact-card identity. Missing or malformed resolver items use
the explicit unavailable state. Legacy `attention.frontPreview` is not used as
a fallback.

### Strict frontend parsing

Search and Triage runtime parsers reject:

- old schemas;
- unknown top-level, item or nested keys;
- card `primaryText` aliases;
- missing display fields;
- invalid source/status enums;
- overlong text;
- incoherent text/source/status/truncation combinations;
- count, ID and nested-shape drift.

### Shared UI presentation

Added:

```text
web-dashboard/src/lib/cardDisplayText.ts
```

The helper returns backend text unchanged for `available` and localizes only the
two explicit fallback states:

| State | RU | EN |
| --- | --- | --- |
| `media_only` | Карточка только с медиа | Card with media only |
| `unavailable` | Текст карточки недоступен | Card text unavailable |

It is used by:

```text
Search card row
Search card Inspector heading
Cards visible-text filter
Cards queue item
Cards Inspector heading
```

The current Cards table/split workspace was not redesigned and remains
product-rejected historical C1.5 UI.

## Tests added or updated

Python:

```text
tests/test_card_display_identity.py
tests/test_search_service.py
tests/test_search_metadata.py
tests/test_search_runtime.py
tests/test_triage_service.py
tests/test_triage_runtime.py
tests/test_dashboard_server.py
```

Frontend:

```text
web-dashboard/src/lib/cardDisplayText.test.ts
web-dashboard/src/lib/searchApi.test.ts
web-dashboard/src/lib/triageApi.test.ts
web-dashboard/src/hooks/useCardsTriageWorkspace.test.tsx
web-dashboard/src/pages/SearchPage.test.tsx
web-dashboard/src/pages/SearchMetadataIntegration.test.tsx
web-dashboard/src/pages/CardsPage.test.tsx
web-dashboard/src/pages/SearchPageActions.test.tsx
```

Covered behavior includes Browser/reviewer precedence, media-only/unavailable
states, exact Japanese fixture, unsafe markup removal, truncation, no answer or
media-file read, Search/Triage parity, schema rejection, unknown-key rejection,
RU/EN fallback, exact-ID handoff and active-card-only inspect.

## Documentation synchronized

```text
docs/card-display-identity.md
docs/search-query-foundation.md
docs/search-v1-and-safe-actions.md
docs/cards-v2-triage-read-api.md
docs/dashboard-api.md
docs/frontend-map.md
docs/ai-handoff.md
roadmap/README.md
roadmap/core/README.md
```

## Verification performed

### Tested implementation

```text
branch: core
tested implementation HEAD: a46116e43756eceb3820f4eca76b28645a54a3ff
origin/core synchronization: 0 behind / 0 ahead
origin/master divergence: 0 behind / 71 ahead
open pull requests from core: none
```

The focused contour was executed on the exact tested implementation HEAD after
the only verification defect had been corrected and pushed.

### Python compile

```powershell
node scripts/run_python.mjs -m compileall -q anki_study_report
```

Result:

```text
exit code: 0
duration: 2.75 s
remaining __pycache__ / .pyc / .pyo: 0
```

### Focused Python

```powershell
node scripts/run_python.mjs -m pytest -q `
  tests/test_card_display_identity.py `
  tests/test_search_service.py `
  tests/test_search_metadata.py `
  tests/test_search_runtime.py `
  tests/test_triage_service.py `
  tests/test_triage_runtime.py `
  tests/test_dashboard_server.py
```

Result on the tested implementation HEAD:

```text
85 passed
0 failed
1 warning
pytest duration: 10.83 s
command duration: 12.69 s
exit code: 0
```

The warning was an environment-only `PytestCacheWarning`: Windows denied
creation of `.pytest_cache`. Test execution and exit status were unaffected,
and no cache artifact entered Git.

### Focused frontend Vitest

```powershell
pnpm exec vitest run `
  src/lib/cardDisplayText.test.ts `
  src/lib/searchApi.test.ts `
  src/lib/triageApi.test.ts `
  src/hooks/useCardsTriageWorkspace.test.tsx `
  src/pages/SearchPage.test.tsx `
  src/pages/SearchMetadataIntegration.test.tsx `
  src/pages/CardsPage.test.tsx `
  src/pages/SearchPageActions.test.tsx
```

Result on the tested implementation HEAD:

```text
8 test files passed
54 tests passed
0 failed
Vitest duration: 3.60 s
command duration: 7.29 s
exit code: 0
```

`SearchPageActions.test.tsx` passed and retained pagination, cross-page
selection, the 200-item cap, action refresh, duplicate-submit protection and
the remaining Search Safe Actions regressions required by this closeout.

### TypeScript typecheck

```powershell
pnpm run typecheck
```

Result on the tested implementation HEAD:

```text
tsc --noEmit
0 errors
duration: 10.60 s
exit code: 0
```

### Verification defect and fix

The first typecheck on implementation candidate
`52c03c340c7a98b72d869ea42d6a9a46d56233e7` found 12 TypeScript errors in
three test files. Runtime tests were green; the mocks had inferred zero- or
one-argument tuples while the assertions inspected the optional second
`RequestInit` argument.

The fix changed no production behavior. It typed the affected mocks as
`typeof fetch` in:

```text
web-dashboard/src/lib/searchApi.test.ts
web-dashboard/src/lib/triageApi.test.ts
web-dashboard/src/pages/SearchPage.test.tsx
```

Fix commit:

```text
a46116e43756eceb3820f4eca76b28645a54a3ff — test: type fetch mocks for strict contract checks
```

After the fix:

```text
affected narrow Vitest: 3 files / 39 tests passed
full focused Python: 85 passed
full focused Vitest: 8 files / 54 tests passed
typecheck: passed
```

No further verification defects were found.

### Git hygiene

```text
tracked working-tree changes before closeout: 0
staged changes before closeout: 0
prohibited tracked artifacts: 0
git diff --check: passed
merge in progress: no
rebase in progress: no
cherry-pick in progress: no
```

Two unrelated untracked Gamification helper files were preserved and excluded:

```text
g0_6a_run.ps1
g0_6a_tool.py
```

### Deliberately not run

```text
full Python suite
full frontend suite
frontend build
package validation/build
run_full_check.ps1 -SkipDocker
Fast CI
Docker
real-Anki E2E
release verification
owner product acceptance
```

These were outside the focused C1.5R.1V verification policy. Heavy integrated
verification remains C1.5R.7 work.

## Scope explicitly not implemented

```text
C1.5R.2 declarative compact formatter runtime
C1.5R.3 front/back preview semantics
C1.5R.4 independent candidate sources and explicit period state
C1.5R.5 dense inbox and 1024 px non-modal drawer
C1.5R.6 guided Inspection Profiles UX
C1.5R.7 integrated acceptance package
C1.6 actions/recheck/resolution loop
```

## Git boundary

No PR, merge, rebase, force-push, release, deployment, `.ankiaddon` publication
or AnkiWeb update was performed. Generated assets, screenshots, logs, caches,
profile data, tokens and E2E outputs were not committed.

## Final stage state

```text
C1.5R.0 — Complete
C1.5R.1 — Complete
C1.5R.2 — Next, not started
C1.5R.3–R.7 — Not started
C1.6 — Blocked
Core C1 — In progress
```

The exact next Core increment is C1.5R.2. It was not started during this
closeout.
