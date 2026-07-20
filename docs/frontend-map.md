# Карта frontend dashboard

Снимок документации: 2026-07-20.

Current contracts live in `docs/`; sequencing lives in `roadmap/`; historical
reports and audits live in `reports/`.

## Source of truth

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/app/App.tsx
web-dashboard/src/layout/
web-dashboard/src/pages/
web-dashboard/src/components/
web-dashboard/src/hooks/
web-dashboard/src/lib/
web-dashboard/src/types/
web-dashboard/src/i18n/
```

`App.tsx` reads the dashboard token from `window.location.search`. Frontend never
reads the Anki collection directly. Theme and RU/EN preferences remain local and
independent.

## Primary routes

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

| Route | Component | Primary data/API | Main risk |
| --- | --- | --- | --- |
| `#/home` | `HomePage` | `StudyReport.today` | current-day vs historical scope |
| `#/calendar` | `CalendarPage` | `activityHub` | date/scope availability |
| `#/stats` | statistics pages | statistics/FSRS APIs | bounded latest-wins queries |
| `#/decks` | `DecksPage` | `deckHub`, Browser action | direct/subtree semantics |
| `#/search` | `SearchPage` | Search v2, metadata v1 | strict parsing, exact IDs |
| `#/cards` | `CardsPage` | Triage v4, Search inspect v2 | bounded accumulation, active preview, responsive detail |
| `#/settings/inspection-profiles` | `InspectionProfilesSettingsPage` | Inspection Profiles APIs | exact refs, lifecycle, local drafts |

## Canonical card identity and preview

One backend exact-card projector supplies Search row/details and Triage item
identity. Frontend `cardDisplayText()` localizes only explicit `media_only` and
`unavailable` states; it does not inspect arbitrary note fields.

```text
Search query/inspect: schema v2
Search metadata: schema v1
Triage automatic/search workset: schema v4
```

Only the active Cards item requests Search inspect. `AnkiCardShadowPreview`
shows sanitized native front in the Inspector/drawer. The existing
`AccessibleModal` shows the cached answer/back. Queue items render no full HTML
and perform no media reads.

## Cards attention inbox

Current topology:

```text
CardsPage
├─ compact summary + priority/reason/deck/text/period controls
├─ source/profile coverage warnings and disclosure
└─ CardsInbox semantic ordered list
   ├─ >= 1200 px: one persistent CardsDetail Inspector
   └─ < 1200 px: full-width queue; explicit activation opens CardsDetailDrawer
```

Durable modules:

```text
components/cards/CardsInbox.tsx
components/cards/CardsDetail.tsx
components/cards/CardsDetailDrawer.tsx
hooks/useCardsTriageWorkspace.ts
hooks/useMediaQuery.ts
lib/triageOrdering.ts
lib/triagePagination.ts
lib/triagePresentation.ts
styles/cardsInbox.css
```

The queue is an ordinary `<ol>` with one native button per item. It is not a
`table`, ARIA `grid`, `listbox` or roving-tabindex composite. Focus and active
item remain separate.

Wide mode selects the first inspectable item without moving focus. At 1024 px
there is no persistent Inspector and no automatic preview request. Activation
opens a labelled non-modal drawer with no backdrop, `aria-modal`, inert shell or
focus trap. The answer preview remains the only modal.

## Period and continuation state

The hook owns explicit session-local 7/30/90-day learning scope. Period changes
restart one automatic v4 request with `contentCursor: null`, abort stale work and
clear accumulated content pages while preserving local filters.

Manual content continuation is available only for coherent v4 cursor state. One
activation sends one request. Accumulation deduplicates items/reasons/sources,
keeps canonical ordering and is bounded to 500 unique items and 10 additional
pages. Errors retain prior usable items and retry the same cursor. There is no
automatic cursor loop.

## Security and action boundary

- frontend has no collection access;
- strict v4/v2 parsers reject unknown or incoherent payloads;
- exact card IDs drive inspect and Open-in-Anki handoff;
- no display text becomes a native query;
- sanitizer, validated media URLs and Shadow DOM isolation are unchanged;
- R5 adds no mutation, selection, resolve/recheck or editor surface.

## Focused tests

```text
pages/CardsPage.test.tsx
hooks/useCardsTriageWorkspace.test.tsx
components/cards/CardsInbox.test.tsx
components/cards/CardsDetailDrawer.test.tsx
lib/triagePagination.test.ts
lib/triageOrdering.test.ts
hooks/useMediaQuery.test.tsx
components/AnkiCardShadowPreview.test.tsx
pages/LocalizationSmoke.test.tsx
```

R5 focused verification passed 9 files / 25 Vitest tests, TypeScript typecheck,
production build/bundle guard and 92 focused backend regressions. The exact
implementation commit is `a30f4db66e73f3f836e69ba90cfc06974ce3df47`; full evidence is in
[`../reports/core/c1-5r-5-cards-attention-inbox-redesign.md`](../reports/core/c1-5r-5-cards-attention-inbox-redesign.md).

## Current status

```text
C1.5R.0–R.5 — Complete
C1.5R.6 — Next, not started
C1.5R.7 — Not started
C1.6 — Blocked
Core C1 — In progress
```

## Guided Inspection Profiles workspace

`InspectionProfilesSettingsPage` composes `BasicProfileEditor`,
`ProfileValidationResult` and `AdvancedProfileDisclosure` over
`useInspectionProfilesWorkspace`. `inspectionProfileBasicView.ts` is the pure
friendly projection over strict v1. The hook owns origin/baseline/user-edit state,
latest-wins reads, validation cancellation, serialized mutations and conflicts.
Dedicated visual rules live in `styles/inspectionProfiles.css`.
