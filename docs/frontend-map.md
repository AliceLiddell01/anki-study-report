# Карта frontend dashboard

**Снимок документации:** 2026-07-22

Актуальные contracts находятся в `docs/`, sequencing — в `roadmap/`, historical reports и audits — в `reports/`.

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

`App.tsx` читает dashboard token из `window.location.search`. Frontend не читает Anki collection напрямую. Theme и RU/EN preferences остаются local и independent.

## Основные routes

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

| Route | Component | Data/API | Главный риск |
| --- | --- | --- | --- |
| `#/home` | `HomePage` | `StudyReport.today` | current-day vs historical scope |
| `#/calendar` | `CalendarPage` | `activityHub` | date/scope availability |
| `#/stats` | statistics pages | Statistics/FSRS API | bounded latest-wins queries |
| `#/decks` | `DecksPage` | `deckHub`, Browser action | direct/subtree semantics |
| `#/search` | `SearchPage` | Search v2, metadata v1 | strict parsing, exact IDs |
| `#/cards` | lazy `CardsPage` | Triage query v4, recheck v1, Search inspect v2 | bounded accumulation, action/recheck races, focus, responsive detail |
| `#/settings/inspection-profiles` | `InspectionProfilesSettingsPage` | Inspection Profiles API | exact refs, lifecycle, local drafts |

## Canonical card identity и preview

Один backend exact-card projector предоставляет identity Search row/details и Triage item.

`cardDisplayText()` локализует только explicit states `media_only` и `unavailable` и не анализирует arbitrary note fields.

```text
Search query/inspect: schema v2
Search metadata: schema v1
Triage query: schema v4
Triage exact-card recheck: schema v1
```

Только active Cards item запрашивает Search inspect. `AnkiCardShadowPreview` показывает sanitized native front в Inspector/drawer. `AccessibleModal` показывает cached answer/back.

Queue items не рендерят full HTML и не читают media.

## Cards attention inbox topology

```text
CardsPage
├─ compact summary + controls priority/reason/deck/text/period
├─ source/profile coverage warnings
└─ CardsInbox semantic ordered list
   ├─ >= 1200 px: persistent CardsDetail Inspector
   └─ < 1200 px: full-width queue + CardsDetailDrawer
```

Основные modules:

```text
components/cards/CardsInbox.tsx
components/cards/CardsDetail.tsx
components/cards/CardsDetailDrawer.tsx
hooks/useCardsTriageWorkspace.ts
hooks/useMediaQuery.ts
lib/triageApi.ts
lib/triageOrdering.ts
lib/triagePagination.ts
lib/triagePresentation.ts
styles/cardsInbox.css
```

Queue — обычный `<ol>` с одной native button на item. Это не `table`, ARIA `grid`, `listbox` или roving-tabindex composite. Focus и active item раздельны.

Wide mode выбирает первый inspectable item без перемещения focus. На 1024 px persistent Inspector и automatic preview request отсутствуют; explicit activation открывает labelled non-modal drawer без backdrop, `aria-modal`, inert shell и focus trap.

Answer preview остаётся единственным modal.

## Period и continuation state

Hook владеет session-local learning period:

```text
7 дней
30 дней
90 дней
```

Period change запускает один automatic query v4 с `contentCursor: null`, abort-ит stale work, очищает accumulated content pages и сохраняет local filters.

Manual continuation доступен только при coherent cursor state. Одна activation отправляет один request.

Accumulation:

- дедуплицирует items/reasons/sources;
- сохраняет canonical ordering;
- bounded до 500 unique items;
- bounded до 10 additional pages;
- сохраняет prior usable items после error;
- не запускает automatic cursor loop.

## C1.6 lifecycle state

`useCardsTriageWorkspace` владеет one-card lifecycle:

```text
idle
→ action/open handoff
→ awaiting_recheck
→ rechecking
→ still_active | partially_resolved | resolved | failed | stale
```

- mutations serialized и не abort-ятся;
- reads latest-wins и guarded sequence IDs;
- action success не удаляет item;
- `recheckTriageCard()` вызывает strict `/api/triage/recheck` v1;
- reconciliation сравнивает stable `reasonId`;
- remaining/new reasons обновляют item на месте;
- item удаляется только после fully authoritative zero-reason response;
- post-removal focus выбирает next, previous или queue heading.

Safe Actions и Open in Anki остаются существующими paths. Bulk/manual resolution отсутствуют.

## Guided Inspection Profiles workspace

`InspectionProfilesSettingsPage` объединяет:

```text
BasicProfileEditor
ProfileValidationResult
AdvancedProfileDisclosure
useInspectionProfilesWorkspace
```

`inspectionProfileBasicView.ts` — pure friendly projection над strict v1.

Hook владеет origin/baseline/user-edit state, latest-wins reads, validation cancellation, serialized mutations и revision conflicts.

## Security boundary

- frontend не имеет collection access;
- strict parsers v4/v1/v2 отклоняют unknown и incoherent payloads;
- exact card IDs используются для inspect/recheck/Open in Anki;
- display text не становится native query;
- sanitizer, validated media URLs и Shadow DOM isolation сохраняются;
- client-side resolution inference отсутствует;
- C1.6 не добавляет second detector/action stack.

## Focused tests

```text
pages/CardsPage.test.tsx
hooks/useCardsTriageWorkspace.test.tsx
components/cards/CardsInbox.test.tsx
components/cards/CardsDetailDrawer.test.tsx
lib/triageApi.test.ts
lib/triagePagination.test.ts
lib/triageOrdering.test.ts
hooks/useMediaQuery.test.tsx
components/AnkiCardShadowPreview.test.tsx
pages/LocalizationSmoke.test.tsx
```

C1.6 frontend suite:

```text
324 tests PASS
TypeScript typecheck PASS
production build PASS
bundle guard PASS — entry 429,516 bytes
```

## Текущий статус Core

```text
C1.5R.0–R.7 — Complete; owner accepted
C1.6 — Complete; owner accepted; merged into core
C1.6B — Conditional; not started
Core C1 — Complete
C2 — Next; not started
```