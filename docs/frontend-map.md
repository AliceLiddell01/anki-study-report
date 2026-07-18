# Карта frontend dashboard

## Documentation structure

Current contracts remain in `docs/`; stage sequencing is in `../roadmap/`;
historical reports/audits are indexed in `../reports/README.md`.

## Notification surfaces

`TopNav.tsx` монтирует `NotificationBell`; `AppLayout.tsx` — единственный
`NotificationToasts`. `NotificationCenterPage.tsx` и
`NotificationSettingsPage.tsx` загружаются как route-level chunks;
`SearchPage.tsx` тоже lazy, чтобы entry оставался ниже bundle budget.
`NotificationItemCard.tsx` владеет copy/actions, `notificationsApi.ts` — exact
response validation, `notificationHandoff.ts` — bounded session-only context.
Routes: `#/notifications` и `#/settings/notifications`.

`FsrsStatisticsPage.tsx` owns five nested FSRS views and `fsrsApi.ts` owns the
typed lazy API/cache identity. `StatisticsPage` and `FsrsStatisticsPage` are
real route-level dynamic imports; `RouteDeliveryBoundary` owns their loading
and chunk-failure UI. Canonical routes start with `#/stats/fsrs`.

Снимок документации: 2026-07-12.

Source of truth:

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/app/App.tsx
web-dashboard/src/layout/TopNav.tsx
web-dashboard/src/layout/SettingsLayout.tsx
web-dashboard/src/layout/GlobalUtilityDock.tsx
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

`AppLayout` монтирует один `GlobalUtilityDock` для всех routes. Theme toggle
переиспользует `lib/theme.ts` и storage key `anki-study-report-theme`.
Language selector рядом с ним использует `i18n/language.ts`, storage key
`anki-study-report-language` и переключает bundled RU/EN resources без reload.
Оба preference независимы; подробнее — `docs/localization.md`.

## Routes/pages

Primary navigation содержит `Сегодня`, `Активность`, `Статистика`, `Колоды`,
`Поиск` и `Карточки` в этом порядке. Profile/Settings/Tools и внешний Boosty support link
открываются через avatar dropdown. Support — безопасная статическая ссылка, а
не SPA route. Технические settings pages связаны отдельной навигацией и не
являются primary-вкладками. Полный IA contract: `docs/navigation-ia.md`.

| Route | Component | Данные/API | Тесты | Риски |
| --- | --- | --- | --- | --- |
| `#/home` | `HomePage` («Сегодня») | `StudyReport.today` + historical forecast/fsrs | `HomePage.test.tsx`, `router.test.tsx` | Today slice должен оставаться current-day; top-level report сохраняется для других pages |
| `#/profile` | `ProfilePage` | `StudyReport.profile`, POST `/api/profile` | `ProfilePage.test.tsx`, `profileApi.test.ts`, `TopNav.test.tsx` | All-collection lifetime view; preferences per Anki profile, не dashboard scope |
| `#/decks` | `DecksPage` | `report.deckHub`, legacy `report.decks` fallback, typed Browser action | `DecksPage.test.tsx`, `deckTree.test.ts` | Не смешивать direct/subtree, не flatten hierarchy при filter/sort |
| `#/search` | `SearchPage` | Search query/inspect, entity actions, `deckHub` picker | `SearchPage.test.tsx`, `searchApi.test.ts`, `entityActionsApi.test.ts` | Latest-wins reads, explicit selection cap, serialized mutations и refresh/reconciliation |
| `#/cards` | `CardsPage` | `attentionCards`, `attentionCardsStatus`, `noteTypeCatalog`, actions API, media URLs | `CardsPage.test.tsx`, `cardAttention.test.ts` | Самая рискованная зона: sanitizer, Shadow DOM, media, modes |
| `#/calendar` | `CalendarPage` («Активность») | `StudyReport.activityHub`, `activityHub` helpers | `ActivityPage.test.tsx`, `calendarStats.test.ts` | Scope/date availability, keyboard и derived weekly/feed contracts |
| `#/stats` + four nested routes | `StatisticsPage` | `statisticsHub.initialResult`, POST `/api/statistics/query`, native Stats action | `StatisticsPage.test.tsx`, `statisticsApi.test.ts` | Bounded query, stale response, current snapshot vs history |
| `#/actions` | `ActionsPage` («Инструменты») | POST `/api/actions/<action>` | `TopNav.test.tsx`, `actionsApi.test.ts`, dashboard action tests backend | Доступен через avatar menu; только allowlisted actions |
| `#/settings` | `ReportSettingsPage` | GET/POST `/api/dashboard/settings` | `SettingsHub.test.tsx`, `settingsApi.test.ts` | Dashboard scope и report defaults разделены; Home period не редактируется |
| `#/settings/data` | `SettingsPage` («Данные») | settings API + cache status/actions | `SettingsHub.test.tsx`, backend cache tests | Form save и cache operations являются разными actions |
| `#/settings/inspection-profiles` | lazy `InspectionProfilesSettingsPage` | strict Inspection Profiles query/validate v2/update API | `InspectionProfilesSettingsPage.test.tsx`, profile API/backend/E2E tests | Detached draft, no autosave, exact refs, revision conflict, strict import/export |
| `#/settings/server` | `ServerSettingsPage` | settings API + server status/actions | `SettingsHub.test.tsx`, server tests | restart/stop меняют token/lifecycle |
| `#/settings/sources` | `IntegrationsPage` | GET `/api/integrations/status` | `router.test.tsx`, typecheck | Read-only diagnostics; старый `#/integrations` redirect-ится сюда |
| `#/settings/logs` | `LogsPage` | logs endpoints/download | `router.test.tsx`, typecheck | Token redaction; старый `#/logs` redirect-ится сюда |

Stage 15 удалил placeholder `#/stats`, `#/fsrs` и `#/browse`. Stage 6 вернул
`#/stats` только как five-section live product; FSRS/Browse не возвращались.
Неизвестные hashes безопасно разрешаются в `#/home`.

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
web-dashboard/src/lib/statisticsApi.ts    typed query, abort and validation errors
web-dashboard/src/lib/searchApi.ts        strict Search query/inspect client
web-dashboard/src/lib/triageApi.ts        strict triage v2 parser/read client
web-dashboard/src/lib/inspectionProfilesApi.ts strict profile parser/client and one-profile import parser
web-dashboard/src/hooks/useInspectionProfilesWorkspace.ts latest-wins catalog, detached draft, validation and serialized mutations
web-dashboard/src/lib/entityActionsApi.ts strict card/note mutation client
web-dashboard/src/hooks/useSearchWorkspace.ts query, selection, inspect and mutation orchestration
web-dashboard/src/lib/fsrsPresentation.ts semantic FSRS verdicts and form bounds
web-dashboard/src/lib/theme.ts            theme localStorage
web-dashboard/src/i18n/index.ts           i18next initialization and bundled resources
web-dashboard/src/i18n/language.ts        language normalization/storage/document sync
web-dashboard/src/i18n/locales/           RU/EN namespace resources
```

`types/search.ts` различает Cards/Notes row/details и хранит IDs строками.
Search v1 использует отдельный `#/search`; Cards page и его preview contract не
переименованы в Cards v2. Полный contract: `docs/search-v1-and-safe-actions.md`.

`types/triage.ts` содержит v2 request/response, item/reason/evidence и
partial-source types. `triageApi.ts` отправляет token-consistent JSON POST и
fail-closed проверяет exact response/nested shapes, decimal IDs, enums, bounds,
counts и finite evidence. Эта foundation намеренно не подключена к CardsPage:
`#/cards` всё ещё читает legacy `attentionCards`; hook/state machine/визуальный
режим C1.3 не добавляет. `types/inspectionProfiles.ts` и
`inspectionProfilesApi.ts` строго проверяют lifecycle, structures,
discriminated check union, validate v1/v2 previews, revision-bearing updates и
single-profile import document. C1.4 добавляет lazy Settings route, workspace
hook и редактор, не меняя CardsPage. Полные contracts:
`docs/cards-v2-triage-read-api.md` and `docs/inspection-profiles-v1.md`.

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
| `statisticsHub` | Statistics layout, common controls and all five sections |
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
web-dashboard/src/pages/StatisticsPage.test.tsx
web-dashboard/src/components/statistics/statisticsPresentation.test.ts
web-dashboard/src/app/router.test.tsx
web-dashboard/src/layout/TopNav.test.tsx
web-dashboard/src/layout/GlobalUtilityDock.test.tsx
web-dashboard/src/i18n/language.test.ts
web-dashboard/src/i18n/resources.test.ts
web-dashboard/src/pages/LocalizationSmoke.test.tsx
web-dashboard/src/lib/formatters.localization.test.ts
```

## Visual/runtime risks

Statistics presentation layer:

- `pages/StatisticsPage.tsx` — route composition, query state, KPI/insight and
  route-specific panels;
- `components/statistics/StatisticsCharts.tsx` — line/bar/stacked primitives,
  tooltip, legend, summary and associated data table;
- `components/statistics/statisticsPresentation.ts` — semantic palette mapping,
  comparison display, sparse summaries and deterministic deck selection;
- `styles.css` — centralized light/dark `--stats-color-*` tokens and panel
  hierarchy.

Statistics не должна возвращаться к shared grouped scale для count/seconds,
percent/count или cards/percentage. Backend series не следует расширять ради
presentation без доказанного semantic blocker.

FSRS presentation использует shared shell, но сохраняет разные задачи routes:
overview conclusion, snapshot distributions, manual calibration, learning-step
sufficiency и read-only workload simulation. Calibration/simulator запросы
остаются manual. Chart output всегда имеет summary и table alternative.

Production build создаёт Vite manifest и восемь JS chunks. Bundle guard
проверяет, что Statistics и FSRS остаются dynamic entries, а каждый JS chunk
меньше 500,000 bytes. Текущая архитектура границ описана в
`reports/product/stage-7-5-fsrs-visual-delivery-report.md`.

- Dev `mockReport` может скрыть real API failure.
- Media URLs без token в raw payload должны получить token при рендере.
- External `http:`, `file:` и token-bearing media URLs нормализуются frontend
  side, но backend sanitizer остается главным барьером.
- Note CSS должен оставаться внутри preview, а не протекать в документ.
- Cards page требует browser/live smoke после изменений rendering/media.

## Product notices

`ProductNoticeCoordinator.tsx` монтируется рядом с `#dashboard-app-shell` и
владеет единственным активным modal. `AccessibleModal.tsx` реализует focus
trap/inert/return focus; `TelemetryConsentDialog.tsx` и `WhatsNewDialog.tsx`
остаются разными решениями. `PrivacySettingsPage.tsx` обслуживает
`#/settings/privacy`. Local API client находится в `lib/productNoticesApi.ts`,
а bundled fallback — в `data/changelog.generated.ts`.
