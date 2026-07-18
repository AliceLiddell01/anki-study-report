# C1.5R.1 — Canonical card display identity

**Date:** 2026-07-19

**Branch:** `core`

**Baseline:** `219fe515ef58e55bc3b8866b4ec4832148126df3`

**Implementation/docs head before this report:** `a3f5b515ebc8c313d0806d7e7bcedb8bad16b2c3`

**Status:** Implemented, focused verification pending

## Purpose

C1.5R.1 corrects compact card identity without absorbing later remediation
stages. One exact-card backend projector now supplies Search, Triage and current
Cards surfaces. Arbitrary note sort/first-non-empty fields are no longer used as
card identity.

This report is implementation evidence, not stage completion or owner product
acceptance.

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

### Repository review

- branch baseline confirmed before implementation;
- changes restricted to `core`;
- backend, frontend types/parsers, focused tests and docs updated together;
- Search metadata remains v1;
- current Cards layout was not redesigned;
- no formatter, preview-side, candidate-source, Profiles or C1.6 implementation
  was added;
- compare against the C1.5R.0 baseline showed the branch ahead with no rebase or
  merge from `master`.

### Preliminary isolated check

An isolated local reconstruction of the Python projector/Search/Triage focused
subset reported:

```text
74 passed
```

This was not an exact-final-branch verification run and does not include the
final HTTP file, frontend tests or typecheck. It is therefore not accepted as
the C1.5R.1 completion gate.

## Required verification still pending

Exact final branch checks:

```powershell
python -m pytest -q tests/test_card_display_identity.py tests/test_search_service.py tests/test_search_metadata.py tests/test_search_runtime.py tests/test_triage_service.py tests/test_triage_runtime.py tests/test_dashboard_server.py
cd web-dashboard
pnpm exec vitest run src/lib/cardDisplayText.test.ts src/lib/searchApi.test.ts src/lib/triageApi.test.ts src/hooks/useCardsTriageWorkspace.test.tsx src/pages/SearchPage.test.tsx src/pages/SearchMetadataIntegration.test.tsx src/pages/CardsPage.test.tsx
pnpm run typecheck
```

Not run or not accepted as evidence:

```text
exact-final-HEAD focused Python contour
focused Vitest contour
TypeScript typecheck
Fast CI
full non-Docker check
package validation/build
Docker
real-Anki E2E
PR/merge/rebase
release/deployment/AnkiWeb publication
owner product acceptance
```

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
C1.5R.1 — Implemented, focused verification pending
C1.5R.2 — Blocked
C1.6 — Blocked
Core C1 — In progress
```

The exact next action is focused C1.5R.1 verification, not C1.5R.2.
