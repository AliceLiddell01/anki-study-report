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
```

## Загрузка данных

`App.tsx` берет token из `window.location.search` и загружает:

```text
/api/report?token=<token>
```

В dev mode при non-403 ошибке используется `web-dashboard/src/data/mockReport.ts`.
Это удобно для UI-разработки, но не является проверкой реального API.

## Routes/pages

Primary navigation содержит только `Сегодня`, `Календарь`, `Колоды` и
`Карточки` в этом порядке. Profile/Settings/Tools и внешний Boosty support link
открываются через avatar dropdown. Support — безопасная статическая ссылка, а
не SPA route. Технические settings pages связаны отдельной навигацией и не
являются primary-вкладками. Полный IA contract: `docs/navigation-ia.md`.

| Route | Component | Данные/API | Тесты | Риски |
| --- | --- | --- | --- | --- |
| `#/home` | `HomePage` («Сегодня») | `StudyReport`: summary, kpis, comparison, activity, decks, forecast, fsrs | `router.test.tsx`, `TopNav.test.tsx`, indirect через frontend suite | Страница чувствительна к пустым блокам payload; глубокий redesign не входит в Navigation / IA |
| `#/profile` | `ProfilePage` | GET/POST `/api/dashboard/settings`, optional refreshed report | `TopNav.test.tsx`, frontend build/typecheck | Доступен через avatar menu; неверная normalizing settings форма меняет dashboard scope |
| `#/decks` | `DecksPage` | `report.decks`, `deckHealth` helpers | `deckHealth` indirectly | Статус/сортировка колод зависят от числовой нормализации |
| `#/cards` | `CardsPage` | `attentionCards`, `attentionCardsStatus`, `noteTypeCatalog`, actions API, media URLs | `CardsPage.test.tsx`, `cardAttention.test.ts` | Самая рискованная зона: sanitizer, Shadow DOM, media, modes |
| `#/calendar` | `CalendarPage` | `activity.days`, calendar helpers | `calendarStats.test.ts` | Даты/period filters легко ломают heatmap |
| `#/actions` | `ActionsPage` («Инструменты») | POST `/api/actions/<action>` | `TopNav.test.tsx`, `actionsApi.test.ts`, dashboard action tests backend | Доступен через avatar menu; только allowlisted actions |
| `#/integrations` | `IntegrationsPage` («Источники данных») | GET `/api/integrations/status` | `router.test.tsx`, typecheck | Settings → Диагностика; реальная read-only диагностика, endpoint token-protected |
| `#/logs` | `LogsPage` | GET `/api/logs/recent`, POST `/api/logs/clear`, download URL | `router.test.tsx`, typecheck | Settings → Диагностика; логи могут содержать diagnostics, token должен редактироваться |
| `#/settings/server` | `ServerSettingsPage` | GET `/api/server/status`, POST `/api/server/<action>` | `router.test.tsx`, `actionsApi.test.ts` | Settings → Система; restart/stop меняют server token/lifecycle |
| `#/settings` | `SettingsPage` | GET `/api/cache/status`, POST `/api/cache/refresh`, `/api/cache/rebuild` | `router.test.tsx`, `TopNav.test.tsx`, typecheck | Вход из avatar menu и раздел «Данные»; cache busy/stale states |

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
web-dashboard/src/lib/deckHealth.ts       deck status model
web-dashboard/src/lib/dateUtils.ts        date formatting
web-dashboard/src/lib/formatters.ts       safe formatting and finite numbers
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
| `metadata` | Home, Profile, Cards, Settings |
| `summary` | Home |
| `kpis` | Home |
| `answerDistribution` | Home |
| `activity` | Home, Calendar |
| `comparison` | Home |
| `decks` | Home, Decks, Cards filters/actions |
| `attentionCards` | Cards; canonical card-level payload key |
| `attentionCardsStatus` | Cards, Settings |
| `noteTypeCatalog` | Cards diagnostics |
| `forecast` | Home, Calendar forecast metric |
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
