# Navigation / Information Architecture

**Статус решения:** Accepted / Complete through Stage 9.5  
**Базовая IA завершена:** 2026-07-10

Statistics, Search и Notification workflow были добавлены последующими этапами без возвращения placeholder routes.

## IA уведомлений

Bell находится в App Shell, но не добавляет пункт primary navigation. Он открывает compact panel и ведёт в `#/notifications`.

Полный Notification Center является пользовательской history surface. `#/settings/notifications` находится в System group Settings shell между Privacy и Server.

Context actions ведут в существующие routes Statistics, Decks и Search. Entity IDs не записываются в hash.

FSRS находится внутри Statistics по route `#/stats/fsrs` с nested pages:

```text
memory
calibration
steps
simulator
```

Standalone `#/fsrs` остаётся invalid.

Settings shell расширен в Stage 2. Актуальный settings contract описан в [`settings-hub.md`](settings-hub.md). Решения Stage 1 по primary navigation и avatar menu остаются без изменений.

## Границы Stage 1

Stage 1 меняет только hierarchy существующих frontend sections и App Shell:

- сокращает primary navigation до основных учебных разделов;
- отделяет Profile и global utilities в avatar menu;
- объединяет существующие технические страницы общей settings navigation;
- сохраняет все работающие routes;
- сохраняет fallback неизвестного hash на `#/home`.

Stage 1 не меняет:

- dashboard payload;
- Python API;
- token model;
- Cards rendering;
- sanitizer;
- action allowlist;
- содержимое product pages глубже, чем требуется для их названия и места в IA.

## Primary navigation

Единственный source of truth для видимых основных пунктов — `primaryNavItems` в `web-dashboard/src/app/router.tsx`.

| Порядок | Название | Route | Роль |
| --- | --- | --- | --- |
| 1 | Сегодня | `#/home` | оперативный центр текущего учебного дня |
| 2 | Активность | `#/calendar` | Calendar v2, выбранный день и derived history |
| 3 | Статистика | `#/stats` | аналитика периодов, качества, нагрузки, прогресса и колод |
| 4 | Колоды | `#/decks` | scoped hierarchy, состояние, причины и области внимания |
| 5 | Поиск | `#/search` | native Cards/Notes query, inspect и явные безопасные actions |
| 6 | Карточки | `#/cards` | bounded queue проблем и persistent Inspector активной карточки |

Профиль, Инструменты и технические страницы не являются аналитическими tabs и не входят в primary navigation.

Stage 5 не меняет IA: `#/decks` остаётся тем же primary route, но его content становится master-detail Decks v2. См. `docs/decks-v2.md`.

Stage 5.5 также не меняет routes. Persistent theme control находится в App Shell utility dock вне primary nav, avatar menu и Settings sidebar.

Selector RU/EN находится в том же dock и также не является navigation item. См. [`localization.md`](localization.md).

## Роль Today/Home

Route `#/home` сохраняет техническое имя для compatibility, но в UI называется «Сегодня».

Его задача — показать:

- состояние текущего учебного дня;
- оставшуюся нагрузку;
- важные риски;
- следующий рекомендуемый шаг.

Он не должен дублировать Profile, Activity, Statistics, Decks или Cards.

Глубокий redesign `HomePage` не входит в Stage 1.

## Avatar dropdown

Справа в topbar расположен явный trigger «Профиль» с нейтральным avatar fallback и chevron.

Меню разделено на два блока:

```text
Профиль            → #/profile
Настройки           → #/settings
────────────────
Инструменты         → #/actions
Поддержать проект   → https://boosty.to/ankistudyreport
```

«Поддержать проект» — статическая HTTPS-ссылка на Boosty. Она:

- открывается в новой вкладке;
- использует `noopener noreferrer`;
- использует `referrerPolicy="no-referrer"`;
- не вызывает backend action;
- не получает dashboard token;
- не изменяет SPA route.

Route `#/support` не существует. Отдельная support page возможна только после отдельного product decision при появлении нескольких providers.

Keyboard behavior меню:

- открытие по click или `ArrowDown`;
- navigation через `ArrowUp`/`ArrowDown`;
- `Home`/`End`;
- закрытие по `Escape`, click outside, выбору route или внешней смене route;
- после `Escape` focus возвращается на trigger.

`#/profile` является самостоятельной локальной all-collection surface: identity, lifetime KPI, activity и deck overview. Он не дублирует primary routes Calendar/Decks/Cards и не изменяет dashboard scope. См. `docs/profile-mvp.md`.

## Settings navigation

`SettingsLayout` задаёт persistent desktop sidebar Settings Hub:

```text
Отчёт
  Отчёт               → #/settings

Данные
  Данные               → #/settings/data
  Проверка карточек    → #/settings/inspection-profiles
  Приватность          → #/settings/privacy

Система
  Уведомления          → #/settings/notifications
  Сервер               → #/settings/server

Диагностика
  Источники данных     → #/settings/sources
  Логи                 → #/settings/logs
```

`#/integrations` и `#/logs` сохраняются как compatibility redirects.

Источники данных остаются read-only diagnostics, а не платформой внешних integrations.

## Текущие routes

```text
#/home
#/profile
#/decks
#/search
#/cards
#/calendar
#/stats
#/stats/quality
#/stats/load
#/stats/progress
#/stats/decks
#/actions
#/notifications
#/settings
#/settings/data
#/settings/inspection-profiles
#/settings/privacy
#/settings/notifications
#/settings/server
#/settings/sources
#/settings/logs
#/stats/fsrs
#/stats/fsrs/memory
#/stats/fsrs/calibration
#/stats/fsrs/steps
#/stats/fsrs/simulator
```

## Скрытые, но сохранённые routes

Эти routes скрыты из primary navigation, но доступны через Profile menu или Settings shell:

```text
#/profile
#/actions
#/notifications
#/settings
#/settings/data
#/settings/inspection-profiles
#/settings/privacy
#/settings/notifications
#/settings/server
#/settings/sources
#/settings/logs
```

## Future routes и правило эволюции

Statistics v1 и Search v1 добавлены только как полноценные primary routes.

Notifications реализованы как App Shell bell и utility route, а не primary tab.

Будущая IA меняется только вместе с реальными пользовательскими workflows:

- «Активность» сохраняет route `#/calendar`; отдельный `#/activity` не добавляется;
- Statistics появился только вместе с полноценным product и содержит пять sections;
- FSRS живёт внутри Statistics, а не отдельной primary tab;
- пользовательский поиск называется «Поиск»; старый Browse не является alias или placeholder;
- Notifications не переносятся в primary navigation без отдельного доказанного решения;
- Additions появляются только после проектирования соответствующей системы.

## Routes, которые нельзя возвращать как placeholders

```text
#/fsrs
#/browse
```

Эти и любые unknown hashes безопасно разрешаются в `#/home`. Compatibility aliases для них не создаются.

## Почему пользовательская и техническая navigation разделены

Primary navigation отвечает на вопрос: «Куда перейти для учёбы и анализа?»

Profile, global actions, cache/server controls и diagnostics решают другую задачу и создавали visual noise рядом с учебными sections.

Avatar menu сохраняет заметный вход в личные и global functions, а Settings shell не позволяет техническим pages превратиться в orphan routes.

Source of truth и tests:

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/layout/TopNav.tsx
web-dashboard/src/layout/SettingsLayout.tsx
web-dashboard/src/app/router.test.tsx
web-dashboard/src/layout/TopNav.test.tsx
```

What’s New не является primary navigation item. Он открывается action «Что нового» в utility group Profile menu и из `#/settings/privacy`.

Privacy находится в Data group Settings shell между Data и System routes.

## Guided route Inspection Profiles

`#/settings/inspection-profiles` остаётся settings/data-quality surface, а не primary study navigation.

Normal path:

```text
точный note type
→ generated Basic setup
→ bounded check
→ explicit confirm
```

Strict editing и maintenance tools остаются secondary disclosures.