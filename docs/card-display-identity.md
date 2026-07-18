# Card display identity

## Status

**Stage:** C1.5R.1 — Implemented, focused verification pending

**Branch:** `core`

**Implementation:** `anki_study_report/card_display_identity.py`

**Public contracts:** Search schema v2, Triage schema v3

C1.5R.1 replaces note-centric card labels with one backend-owned, bounded card
identity across Search, Triage, and the current Cards surfaces. The implementation
candidate is committed, but this stage is not Complete until the focused local
verification contour passes.

Recovery context: [`../reports/core/c1-5r-0-recovery-baseline.md`](../reports/core/c1-5r-0-recovery-baseline.md).
Implementation report: [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md).

## Scope

The same compact identity is consumed by:

- Search card result row;
- Search card Inspector heading;
- canonical Triage item;
- Cards queue item;
- Cards Inspector heading.

Note-mode Search remains a note projection and keeps `primaryText`. C1.5R.1 does
not implement the declarative formatter, front/back preview correction,
candidate-source redesign, Cards inbox redesign, 1024 px drawer, Inspection
Profiles redesign, or C1.6 actions.

## Authoritative projector

`project_card_display_identity(card)` owns exact-card compact identity. It does
not scan the note sort field or arbitrary non-empty note fields.

Source precedence:

1. native Browser question: `card.question(reload=True, browser=True)`;
2. native reviewer front: `card.question(reload=True, browser=False)`;
3. explicit `media_only` or `unavailable` state.

C1.5R.2 may later add an exact declarative formatter above Browser Appearance.
No formatter storage, schema, runtime, or UI exists in C1.5R.1.

The projector never renders `card.answer()`, reads media files, loads remote
resources, executes template JavaScript, or exposes raw renderer exceptions.

## Plain-text projection

The compact projection is intentionally not a generic HTML-to-text utility.
It is line-aware and identity-specific:

- `[sound:...]` and `[anki:play:...]` are removed and count as media;
- image/audio/video/source/picture elements count as media but contribute no
  filename or URL;
- script, style, iframe, object, embed, SVG, MathML, template, form, audio,
  video, and picture contents are dropped;
- `<br>` and block boundaries separate candidate lines;
- inline nodes are concatenated without invented spaces;
- entities are decoded and whitespace is collapsed inside each line;
- the first meaningful line wins;
- output is bounded to 240 characters with one terminal ellipsis;
- malformed blocked markup fails closed.

The exact media-heavy Japanese fixture therefore projects:

```text
【に】（する）
```

It never falls through to an unrelated sort-field value such as
`「Существительное」`.

## Wire contract

Card identity is a flat exact object fragment:

```json
{
  "displayText": "【に】（する）",
  "displaySource": "reviewer_front",
  "displayStatus": "available",
  "displayTruncated": false
}
```

`displaySource`:

```text
browser_question | reviewer_front | none
```

`displayStatus`:

```text
available | media_only | unavailable
```

Coherence rules:

- `available`: non-empty text; source is Browser question or reviewer front;
- `media_only`: empty text, no truncation; rendered source is retained;
- `unavailable`: empty text, source `none`, no truncation.

No `primaryText` alias remains on card rows, card details, or Triage items.
Unknown keys, old schemas, aliases, incoherent state/source/text combinations,
and overlong text fail closed in the TypeScript parsers.

## Search schema v2

Search query and inspect requests require exact `schemaVersion: 2`. Query and
inspect responses also use schema v2.

Card rows/details carry the four display fields and do not carry `primaryText`.
Note rows/details keep `primaryText` and do not gain card display fields. Search
metadata remains a separate schema v1 variant.

The same Python `project_card_row()` path serves normal Search, Search inspect,
and exact-card resolution used by Triage.

## Triage schema v3

Triage requests and responses require exact `schemaVersion: 3`. Triage items
carry the same four display fields and do not carry `primaryText`.

Available exact cards copy the Search-owned display projection. Missing cards
use the explicit unavailable identity. Triage does not reuse legacy
`attention.frontPreview` or invent another fallback.

## UI behavior

Search rows, Search Inspector, Cards queue, and Cards Inspector call one shared
frontend presentation helper. Backend text is shown unchanged for `available`.
The two explicit fallback states are localized:

| State | RU | EN |
| --- | --- | --- |
| `media_only` | Карточка только с медиа | Card with media only |
| `unavailable` | Текст карточки недоступен | Card text unavailable |

This stage changes identity only. The current Cards table/split workspace remains
product-rejected historical C1.5 UI and is not accepted by this implementation.

## Security and privacy

The existing loopback/token boundary, sanitizer, validated media API, Shadow DOM
preview, action allowlists, and frontend collection isolation remain unchanged.
Compact identity is local and is not added to telemetry or normal logs. Public
artifacts must not contain raw note dumps, media filenames, absolute paths,
renderer exceptions, or tokens.

## Verification boundary

Focused commands required before C1.5R.1 can become Complete:

```powershell
python -m pytest -q tests/test_card_display_identity.py tests/test_search_service.py tests/test_search_metadata.py tests/test_search_runtime.py tests/test_triage_service.py tests/test_triage_runtime.py tests/test_dashboard_server.py
cd web-dashboard
pnpm exec vitest run src/lib/cardDisplayText.test.ts src/lib/searchApi.test.ts src/lib/triageApi.test.ts src/hooks/useCardsTriageWorkspace.test.tsx src/pages/SearchPage.test.tsx src/pages/SearchMetadataIntegration.test.tsx src/pages/CardsPage.test.tsx
pnpm run typecheck
```

Fast CI, Docker, real-Anki E2E, package validation, PR, merge, and release are not
part of C1.5R.1 connector-only implementation.
