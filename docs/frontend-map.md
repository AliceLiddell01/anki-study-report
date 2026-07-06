# Карта frontend dashboard

Снимок документации: 2026-07-06.

Source of truth:

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/app/App.tsx
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

| Route | Component | Данные/API | Тесты | Риски |
| --- | --- | --- | --- | --- |
| `#/home` | `HomePage` | `StudyReport`: summary, kpis, comparison, activity, decks, forecast, fsrs | indirect через frontend suite | Главная страница чувствительна к пустым блокам payload |
| `#/profile` | `ProfilePage` | GET/POST `/api/dashboard/settings`, optional refreshed report | frontend build/typecheck | Неверная normalizing settings форма меняет dashboard scope |
| `#/decks` | `DecksPage` | `report.decks`, `deckHealth` helpers | `deckHealth` indirectly | Статус/сортировка колод зависят от числовой нормализации |
| `#/cards` | `CardsPage` | `attentionCards`, `attentionCardsStatus`, `noteTypeCatalog`, actions API, media URLs | `CardsPage.test.tsx`, `cardAttention.test.ts` | Самая рискованная зона: sanitizer, Shadow DOM, media, modes |
| `#/stats` | `StatsPage` | Сейчас placeholder/simple page | typecheck | Не считать аналитикой, пока не подключены данные |
| `#/calendar` | `CalendarPage` | `activity.days`, calendar helpers | `calendarStats.test.ts` | Даты/period filters легко ломают heatmap |
| `#/fsrs` | `FsrsPage` | Сейчас simple/placeholder page | typecheck | Не описывать как полный FSRS UI без проверки |
| `#/browse` | `BrowsePage` | Сейчас simple/placeholder page | typecheck | Не путать с Anki Browser actions |
| `#/actions` | `ActionsPage` | POST `/api/actions/<action>` | `actionsApi.test.ts`, dashboard action tests backend | Только allowlisted actions |
| `#/integrations` | `IntegrationsPage` | GET `/api/integrations/status` | typecheck | Endpoint token-protected |
| `#/logs` | `LogsPage` | GET `/api/logs/recent`, POST `/api/logs/clear`, download URL | typecheck | Логи могут содержать diagnostics, token должен редактироваться |
| `#/settings/server` | `ServerSettingsPage` | GET `/api/server/status`, POST `/api/server/<action>` | `actionsApi.test.ts` | Restart/stop меняют server token/lifecycle |
| `#/settings` | `SettingsPage` | GET `/api/cache/status`, POST `/api/cache/refresh`, `/api/cache/rebuild` | typecheck | Cache busy/stale states |

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

`table` и `tiles` используют `AnkiCardShadowPreview`:

```text
web-dashboard/src/components/AnkiCardShadowPreview.tsx
data-testid="anki-card-shadow-preview"
```

`ankiPreview` не использует `AnkiCardShadowPreview` и не дублирует front. Этот
режим показывает единственную answer-only секцию из `renderedPreview.backHtml`:

```text
data-testid="anki-preview-answer"
.asr-front-preview-html
```

Если `backHtml` отсутствует, UI показывает diagnostic fallback. Preview не
исполняет JS templates и не использует iframe; sanitizer остается backend
barrier. Целевой layout для этого dashboard - desktop/laptop, не mobile widths
ниже рабочего desktop surface.

При smoke failure сначала проверить active mode, потом DOM selector. Для
`table`/`tiles` искать Shadow DOM host; для `ankiPreview` искать answer-only
HTML в обычном DOM.

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
| `attentionCards` / legacy aliases | Cards |
| `attentionCardsStatus` | Cards, Settings |
| `noteTypeCatalog` | Cards diagnostics |
| `forecast` | Home, Calendar forecast metric |
| `fsrs` | Home, Fsrs page placeholder/future |
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
```

## Visual/runtime risks

- Dev `mockReport` может скрыть real API failure.
- Media URLs без token в raw payload должны получить token при рендере.
- External `http:`, `file:` и token-bearing media URLs нормализуются frontend
  side, но backend sanitizer остается главным барьером.
- Note CSS должен оставаться внутри preview, а не протекать в документ.
- Cards page требует browser/live smoke после изменений rendering/media.
