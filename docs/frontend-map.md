# Карта frontend dashboard

Снимок документации: 2026-07-19.

Current contracts live in `docs/`; sequencing lives in `roadmap/`; historical
reports and audits live in `reports/`.

## Source of truth

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/app/App.tsx
web-dashboard/src/layout/TopNav.tsx
web-dashboard/src/layout/SettingsLayout.tsx
web-dashboard/src/layout/GlobalUtilityDock.tsx
web-dashboard/src/pages/
web-dashboard/src/components/
web-dashboard/src/hooks/
web-dashboard/src/lib/
web-dashboard/src/types/
web-dashboard/src/i18n/
```

`App.tsx` reads the token from `window.location.search` and loads
`/api/report?token=<token>`. The frontend never reads Anki collection directly.
Theme and RU/EN language preferences remain independent local preferences.

## Primary routes

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

Profile, Settings, Tools and Support are outside primary study navigation.
Diagnostics remain inside Settings. Unknown hashes resolve safely to Home.

| Route | Component | Primary data/API | Main risk |
| --- | --- | --- | --- |
| `#/home` | `HomePage` | `StudyReport.today` | current-day slice vs historical report |
| `#/profile` | `ProfilePage` | `StudyReport.profile`, `/api/profile` | all-collection lifetime semantics |
| `#/calendar` | `CalendarPage` | `activityHub` | date/scope availability |
| `#/stats` and nested routes | `StatisticsPage`, `FsrsStatisticsPage` | statistics/FSRS query APIs | bounded queries, stale/latest-wins |
| `#/decks` | `DecksPage` | `deckHub`, Browser action | direct/subtree semantics |
| `#/search` | `SearchPage` | Search v2, metadata v1, Safe Actions | strict parsing, selection, exact IDs |
| `#/cards` | `CardsPage` | Triage v3, Search inspect v2 | identity parity, active preview, rejected C1.5 UI |
| `#/settings/inspection-profiles` | `InspectionProfilesSettingsPage` | Inspection Profiles APIs | exact refs, lifecycle, local drafts |
| settings/diagnostics routes | settings pages | narrow settings/status APIs | token and lifecycle safety |

## Canonical card display identity

C1.5R.1 introduces one card-display flow:

```text
Python exact-card projector
  → Search card row v2
  → Search card inspect v2
  → Triage exact-card resolution v3
  → Search row / Search Inspector / Cards queue / Cards Inspector
```

Backend module:

```text
anki_study_report/card_display_identity.py
```

Frontend model and validation:

```text
web-dashboard/src/types/search.ts
web-dashboard/src/lib/searchApi.ts
web-dashboard/src/types/triage.ts
web-dashboard/src/lib/triageApi.ts
```

Frontend presentation fallback:

```text
web-dashboard/src/lib/cardDisplayText.ts
```

The flat identity fragment is:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

`cardDisplayText()` returns backend text for `available` and only localizes the
two explicit fallback states. It does not extract or transform card content.

Card rows/details and Triage items do not contain `primaryText`. Note rows and
note details retain note-mode `primaryText`.


## Formatter contract client without UI

C1.5R.2 adds only strict contract code:

```text
types/cardDisplayFormatters.ts          formatter/store/API types
lib/cardDisplayFormattersApi.ts         query/validate/update client and parsers
lib/cardDisplayFormattersApi.test.ts    strict response/request regression
```

The parser rejects old/future schemas, unknown keys, malformed IDs and dates,
duplicate formatter keys, invalid enums/limits, nullable template mismatch,
coherence drift and unexpected error envelopes. It sends exact JSON bodies to
token-protected local endpoints.

There is deliberately no route, page, hook, Settings item, form control, live
preview, import/export UI or formatter-applied wire flag in R2.

## Search page

`useSearchWorkspace.ts` owns query/session/selection/inspect/action state.
Normal query and inspect requests send exact `schemaVersion: 2`. Metadata remains
an independent v1 request.

```text
SearchResultsTable.tsx  card row uses cardDisplayText(row)
SearchInspector.tsx     card heading uses cardDisplayText(details)
```

Notes continue to display `primaryText`. Selection remains explicit decimal IDs
and `open-search-selection` never derives a query from display text.

`searchApi.ts` rejects unknown keys, old schemas, card `primaryText` aliases and
incoherent display states. Search card row and Search card details require the
same display fields.

## Cards page

`useCardsTriageWorkspace.ts` sends automatic Triage schema v3 and loads active
card details through Search inspect schema v2. It preserves latest-wins and
exact-ID Browser handoff.

`CardsPage.tsx` uses `cardDisplayText(item)` for:

- client-side visible-text filtering;
- queue row identity;
- Inspector heading.

The active `SearchCardDetails` identity is also available to preview metadata.
Queue rows never fetch full HTML or media.

The current native table + persistent Inspector remains historical C1.5 UI and
is still product-rejected. C1.5R.1 changes identity only; dense inbox redesign,
1024 px drawer and acceptance package remain later C1.5R stages.

## Preview boundary

Only the active card calls:

```text
POST /api/search/inspect
AnkiCardShadowPreview
```

Compact identity and full preview are separate. C1.5R.1 does not change
Inspector-front or expanded-preview side behavior. Shadow DOM, sanitizer,
validated token-protected media and no-iframe/no-template-JS boundaries remain.

## Important helpers

```text
lib/actionsApi.ts                    dashboard action transport
lib/cardDisplayText.ts               RU/EN display-state fallback only
lib/searchApi.ts                     strict Search v2 + metadata v1 client
lib/triageApi.ts                     strict Triage v3 client
lib/entityActionsApi.ts              strict card/note Safe Actions
hooks/useSearchWorkspace.ts          Search orchestration
hooks/useCardsTriageWorkspace.ts     Triage/active inspect orchestration
lib/inspectionProfilesApi.ts         strict profile client/import parser
lib/statisticsApi.ts                 typed statistics query client
lib/theme.ts                         theme preference
 i18n/index.ts                       bundled RU/EN initialization
```

## Payload and API ownership

| Data | Owner/consumer |
| --- | --- |
| `StudyReport.today` | Home |
| `profile` | Profile |
| `activityHub` | Activity |
| `deckHub` | Decks and scoped selectors |
| `statisticsHub` | Statistics |
| Search metadata v1 | Search controls |
| Search query/inspect v2 | Search rows/details and active Cards preview |
| Triage v3 | Cards queue/reasons/source state |
| `attentionCards` | legacy report consumers, not canonical Cards queue |

## Focused tests for C1.5R.1

```text
web-dashboard/src/lib/cardDisplayText.test.ts
web-dashboard/src/lib/searchApi.test.ts
web-dashboard/src/lib/triageApi.test.ts
web-dashboard/src/hooks/useCardsTriageWorkspace.test.tsx
web-dashboard/src/pages/SearchPage.test.tsx
web-dashboard/src/pages/SearchMetadataIntegration.test.tsx
web-dashboard/src/pages/CardsPage.test.tsx
```

These tests are committed but not executed in the GitHub connector environment.
Typecheck evidence is also pending.

## Current status

```text
C1.5R.0 — Complete
C1.5R.1 — Complete
C1.5R.2 — Implemented, canonical non-Docker verification pending
C1.6 — Blocked
Core C1 — In progress
```

No formatter UI, preview-side correction, candidate-source redesign, Cards
inbox redesign or Inspection Profiles redesign is implied by
this map.
