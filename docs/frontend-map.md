# Карта frontend dashboard

Снимок документации: 2026-07-10.

Source of truth:

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/app/App.tsx
web-dashboard/src/layout/TopNav.tsx
web-dashboard/src/layout/SettingsLayout.tsx
web-dashboard/src/pages/
web-dashboard/src/lib/
web-dashboard/src/types/report.ts
web-dashboard/src/types/settings.ts
```

## Загрузка данных

`App.tsx` берет token из `window.location.search` и загружает:

```text
/api/report?token=<token>
```

В dev mode при non-403 ошибке используется `web-dashboard/src/data/mockReport.ts`.
Это удобно для UI-разработки, но не является проверкой реального API.

## Routes/pages

Primary navigation содержит только `Сегодня`, `Активность`, `Колоды` и
`Карточки` в этом порядке. Profile/Settings/Tools и внешний Boosty support link
открываются через avatar dropdown. Support — безопасная статическая ссылка, а
не SPA route. Технические settings pages связаны отдельной навигацией и не
являются primary-вкладками. Полный IA contract: `docs/navigation-ia.md`.

| Route | Component | Данные/API | Тесты | Риски |
| --- | --- | --- | --- | --- |
| `#/home` | `HomePage` («Сегодня») | `StudyReport.today` + historical forecast/fsrs | `HomePage.test.tsx`, `router.test.tsx` | Today slice должен оставаться current-day; top-level report сохраняется для других pages |
| `#/profile` | `ProfilePage` | `StudyReport.profile`, POST `/api/profile` | `ProfilePage.test.tsx`, `profileApi.test.ts`, `TopNav.test.tsx` | All-collection lifetime view; preferences per Anki profile, не dashboard scope |
| `#/decks` | `DecksPage` | `report.deckHub`, legacy `report.decks` fallback, typed Browser action | `DecksPage.test.tsx`, `deckTree.test.ts` | Не смешивать direct/subtree, не flatten hierarchy при filter/sort |
| `#/cards` | `CardsPage` | `attentionCards`, `attentionCardsStatus`, `noteTypeCatalog`, actions API, media URLs | `CardsPage.test.tsx`, `cardAttention.test.ts` | Самая рискованная зона: sanitizer, Shadow DOM, media, modes |
| `#/calendar` | `CalendarPage` («Активность») | `StudyReport.activityHub`, `activityHub` helpers | `ActivityPage.test.tsx`, `calendarStats.test.ts` | Scope/date availability, keyboard и derived weekly/feed contracts |
| `#/actions` | `ActionsPage` («Инструменты») | POST `/api/actions/<action>` | `TopNav.test.tsx`, `actionsApi.test.ts`, dashboard action tests backend | Доступен через avatar menu; только allowlisted actions |
| `#/settings` | `ReportSettingsPage` | GET/POST `/api/dashboard/settings` | `SettingsHub.test.tsx`, `settingsApi.test.ts` | Dashboard scope и report defaults разделены; Home period не редактируется |
| `#/settings/data` | `SettingsPage` («Данные») | settings API + cache status/actions | `SettingsHub.test.tsx`, backend cache tests | Form save и cache operations являются разными actions |
| `#/settings/server` | `ServerSettingsPage` | settings API + server status/actions | `SettingsHub.test.tsx`, server tests | restart/stop меняют token/lifecycle |
| `#/settings/sources` | `IntegrationsPage` | GET `/api/integrations/status` | `router.test.tsx`, typecheck | Read-only diagnostics; старый `#/integrations` redirect-ится сюда |
| `#/settings/logs` | `LogsPage` | logs endpoints/download | `router.test.tsx`, typecheck | Token redaction; старый `#/logs` redirect-ится сюда |

Stage 15 удалил `#/stats`, `#/fsrs` и `#/browse`: это были страницы с обещаниями
будущих функций без собственной live data или workflow. Они больше не
показываются в primary navigation и не входят в `RoutePath`; старые и
неизвестные hashes безопасно разрешаются в `#/home`. Реальные статистика и FSRS
остались на `HomePage`/`CalendarPage`, а действия Anki Browser — на
`ActionsPage` и `CardsPage`.

## Важные helpers/normalizers

```text
web-dashboard/src/lib/actionsApi.ts       token extraction and action response normalization
web-dashboard/src/lib/cardAttention.ts    card-level payload normalization
web-dashboard/src/lib/calendarStats.ts    calendar/heatmap model
web-dashboard/src/lib/activityHub.ts      bounded Activity period/metric/feed selectors
web-dashboard/src/lib/deckHealth.ts       deck status model
web-dashboard/src/lib/deckTree.ts         Decks v2 search/filter/sibling sort/visible rows
web-dashboard/src/lib/dateUtils.ts        date formatting
web-dashboard/src/lib/formatters.ts       safe formatting and finite numbers
web-dashboard/src/lib/profileApi.ts       narrow profile preference save API
web-dashboard/src/lib/theme.ts            theme localStorage
```

## Cards preview modes

`CardsPage.tsx` поддерживает:

```text
table
tiles
ankiPreview
```

Storage key:

```text
anki-study-report.cards.displayMode
```

`table` и `tiles` используют `AnkiCardShadowPreview` как front-only preview:

```text
web-dashboard/src/components/AnkiCardShadowPreview.tsx
data-testid="anki-card-shadow-preview"
```

`ankiPreview` тоже использует `AnkiCardShadowPreview`, но в режиме
`mode="preview"` / `side="answer"`. Он показывает единственную answer-only
секцию из `renderedPreview.backHtml` и не дублирует отдельный front:

```text
data-testid="anki-preview-answer"
data-testid="anki-card-shadow-preview"
data-shadow-preview-mode="preview"
data-preview-side="answer"
```

Если `backHtml` отсутствует, UI показывает diagnostic fallback внутри answer
section; это не штатное отдельное front preview. Preview не исполняет JS
templates и не использует iframe; sanitizer остается backend barrier, а note
CSS должен оставаться внутри Shadow DOM preview host. Целевой layout для этого
dashboard - desktop/laptop, не mobile widths ниже рабочего desktop surface.

При smoke failure сначала проверить active mode, потом DOM selector. Для
`table`/`tiles` искать Shadow DOM host с `data-shadow-preview-mode="table"` или
`tile`; для `ankiPreview` искать `data-testid="anki-preview-answer"` и
answer-host `data-shadow-preview-mode="preview"` / `data-preview-side="answer"`.

## Payload keys по страницам

| Payload key | Основные потребители |
| --- | --- |
| `metadata` | Home, Cards, Settings |
| `profile` | Profile identity, lifetime KPI, activity, deck overview/preferences |
| `summary` | Home |
| `kpis` | Home |
| `answerDistribution` | Home |
| `activity` | Home and legacy calendar compatibility |
| `activityHub` | Activity calendar, selected-day details, derived daily/weekly feed |
| `comparison` | Home |
| `decks` | Home, Decks, Cards filters/actions |
| `deckHub` | Decks v2 scoped hierarchy and detail; additive, normalized |
| `attentionCards` | Cards; canonical card-level payload key |
| `attentionCardsStatus` | Cards, Settings |
| `noteTypeCatalog` | Cards diagnostics |
| `forecast` | Home only; Activity не показывает placeholder forecast metric |
| `fsrs` | Home |
| `recommendations` | Home, Actions context |
| `cache` | Settings, ServerSettings |

## Важные тесты

```text
web-dashboard/src/lib/actionsApi.test.ts
web-dashboard/src/lib/calendarStats.test.ts
web-dashboard/src/lib/cardAttention.test.ts
web-dashboard/src/lib/dateUtils.test.ts
web-dashboard/src/lib/formatters.test.ts
web-dashboard/src/pages/CardsPage.test.tsx
web-dashboard/src/app/router.test.tsx
web-dashboard/src/layout/TopNav.test.tsx
```

## Visual/runtime risks

- Dev `mockReport` может скрыть real API failure.
- Media URLs без token в raw payload должны получить token при рендере.
- External `http:`, `file:` и token-bearing media URLs нормализуются frontend
  side, но backend sanitizer остается главным барьером.
- Note CSS должен оставаться внутри preview, а не протекать в документ.
- Cards page требует browser/live smoke после изменений rendering/media.
