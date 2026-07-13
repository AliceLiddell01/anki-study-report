# Navigation / Information Architecture

FSRS lives inside Statistics at `#/stats/fsrs` with nested `memory`,
`calibration`, `steps`, and `simulator`; standalone `#/fsrs` remains invalid.

Статус решения: **Accepted / Complete through Stage 6**. Базовая IA завершена
2026-07-10, Statistics v1 добавлена 2026-07-12.

Settings shell расширен в Stage 2. Актуальный settings contract описан в
`docs/settings-hub.md`; решения Stage 1 по primary navigation и avatar menu
остаются без изменений.

## Границы Stage 1

Этап меняет только иерархию существующих frontend-разделов и app shell:

- сокращает primary navigation до основных учебных разделов;
- отделяет профиль и глобальные утилиты в avatar menu;
- объединяет существующие технические страницы общей settings navigation;
- сохраняет все работающие routes и fallback неизвестного hash на `#/home`.

Stage 1 не меняет dashboard payload, Python API, token model, Cards rendering,
sanitizer, actions allowlist и содержимое продуктовых страниц глубже, чем нужно
для их названия и места в IA.

## Primary navigation

Единственный source of truth для видимых основных пунктов —
`primaryNavItems` в `web-dashboard/src/app/router.tsx`.

| Порядок | Название | Route | Роль |
| --- | --- | --- | --- |
| 1 | Сегодня | `#/home` | Оперативный центр текущего учебного дня |
| 2 | Активность | `#/calendar` | Calendar v2, выбранный день и derived history |
| 3 | Статистика | `#/stats` | Аналитика периодов, качества, нагрузки, прогресса и колод |
| 4 | Колоды | `#/decks` | Scoped hierarchy, состояние, причины и области внимания |
| 5 | Карточки | `#/cards` | Карточки, требующие внимания |

Профиль, Инструменты и технические страницы не являются аналитическими
вкладками и в primary navigation не входят.

Stage 5 не меняет IA: `#/decks` остаётся тем же primary route, но его content
теперь является master-detail Decks v2. См. `docs/decks-v2.md`.

Stage 5.5 также не меняет routes. Постоянный theme control живёт в App Shell
utility dock вне primary nav, avatar menu и Settings sidebar. Future language
utility документирован, но не рендерится.

## Роль Today/Home

Route `#/home` сохраняет техническое имя для совместимости, но в интерфейсе
называется «Сегодня». Его целевая роль — показать состояние текущего учебного
дня, оставшуюся нагрузку, важные риски и следующий рекомендуемый шаг. Он не
должен дублировать будущие Profile, Activity, Statistics, Decks или Cards.

Глубокий redesign `HomePage` не входит в Stage 1.

## Avatar dropdown

Справа в topbar расположен явный trigger «Профиль» с нейтральным avatar
fallback и chevron. Текущее меню разделено на два блока:

```text
Профиль       → #/profile
Настройки     → #/settings
────────────
Инструменты   → #/actions
Поддержать проект → https://boosty.to/ankistudyreport
```

«Поддержать проект» — статическая HTTPS-ссылка на Boosty. Она открывается в
новой вкладке с `noopener noreferrer` и `referrerPolicy="no-referrer"`, не
использует backend action, не получает dashboard token и не изменяет SPA route.
Route `#/support` не существует. Отдельная support page остаётся возможным
будущим продуктовым решением только при появлении нескольких providers.

Меню открывается по click или `ArrowDown`, поддерживает `ArrowUp`/`ArrowDown`,
`Home`/`End`, закрывается по `Escape`, click outside, выбору route и внешней
смене route. После `Escape` focus возвращается на trigger.

`#/profile` в Stage 3 является самостоятельной локальной all-collection
витриной: identity, lifetime KPI, activity и deck overview. Он не дублирует
primary Calendar/Decks/Cards routes и не редактирует dashboard scope. Детали:
`docs/profile-mvp.md`.

## Settings navigation

`SettingsLayout` задаёт постоянный desktop sidebar Settings Hub:

```text
Отчёт
  Отчёт              → #/settings
Данные
  Данные              → #/settings/data

Система
  Сервер              → #/settings/server

Диагностика
  Источники данных    → #/settings/sources
  Логи                → #/settings/logs
```

`#/integrations` и `#/logs` сохранены как compatibility redirects. Источники
данных остаются read-only диагностикой, а не платформой внешних интеграций.

## Текущие routes

Все эти routes остаются рабочими:

```text
#/home
#/profile
#/decks
#/cards
#/calendar
#/stats
#/stats/quality
#/stats/load
#/stats/progress
#/stats/decks
#/actions
#/settings
#/settings/data
#/settings/server
#/settings/sources
#/settings/logs
```

## Hidden-but-kept routes

Routes ниже скрыты из primary navigation, но доступны через профильное меню
или settings shell:

```text
#/profile
#/actions
#/settings
#/settings/data
#/settings/server
#/settings/sources
#/settings/logs
```

## Future routes и правило эволюции

Statistics v1 уже добавлена как полноценный primary route. Будущая IA может
добавить «Поиск» и «Уведомления»,
но только вместе с реальными пользовательскими workflows:

- «Активность» сохраняет route `#/calendar`; отдельный `#/activity` не добавляется;
- Статистика появилась только вместе с Statistics v1 и содержит пять sections;
- FSRS живёт внутри Statistics, а не отдельной primary-вкладкой;
- будущий пользовательский поиск называется «Поиск», старый Browse не служит
  его placeholder;
- Уведомления появляются только с реальным notification workflow;
- Дополнения появляются только после проектирования соответствующей системы.

## Routes, которые нельзя возвращать как placeholders

```text
#/fsrs
#/browse
```

Эти hashes и любые неизвестные hashes безопасно разрешаются в `#/home`.
Compatibility aliases для них не создаются.

## Почему пользовательская и техническая навигация разделены

Primary navigation отвечает на вопрос «куда перейти для учёбы и анализа».
Профиль, глобальные действия, cache/server controls и диагностика решают другую
задачу и создавали визуальный шум рядом с учебными разделами. Avatar menu
сохраняет заметный вход в личные и глобальные функции, а settings shell не даёт
техническим страницам стать orphan routes.

Source of truth и проверки:

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/layout/TopNav.tsx
web-dashboard/src/layout/SettingsLayout.tsx
web-dashboard/src/app/router.test.tsx
web-dashboard/src/layout/TopNav.test.tsx
```
