# Навигация и информационная архитектура

**Статус решения:** принято; завершено до Stage 9.5 включительно  
**Базовая IA завершена:** 2026-07-10

Statistics, Search и workflow уведомлений добавлены последующими этапами без возвращения placeholder-маршрутов.

## IA уведомлений

Bell находится в App Shell, но не добавляет пункт основной навигации. Он открывает компактную панель и ведёт в `#/notifications`.

Полный Notification Center является пользовательской поверхностью истории. `#/settings/notifications` находится в системной группе Settings между Privacy и Server.

Контекстные действия ведут в существующие маршруты Statistics, Decks и Search. ID сущностей не записываются в hash.

FSRS находится внутри Statistics по маршруту `#/stats/fsrs` с вложенными страницами:

```text
memory
calibration
steps
simulator
```

Отдельный `#/fsrs` остаётся недопустимым.

Оболочка Settings расширена в Stage 2. Актуальный контракт описан в [`settings-hub.md`](settings-hub.md). Решения Stage 1 по основной навигации и menu аватара остаются без изменений.

## Границы Stage 1

Stage 1 меняет только иерархию существующих разделов frontend и App Shell:

- сокращает основную навигацию до ключевых учебных разделов;
- отделяет Profile и глобальные инструменты в menu аватара;
- объединяет существующие технические страницы общей навигацией Settings;
- сохраняет все работающие маршруты;
- сохраняет fallback неизвестного hash на `#/home`.

Stage 1 не меняет:

- payload dashboard;
- API Python;
- модель токена;
- рендер Cards;
- sanitizer;
- allowlist действий;
- содержимое продуктовых страниц глубже, чем требуется для их названия и места в IA.

## Основная навигация

Единственный источник истины для видимых основных пунктов — `primaryNavItems` в `web-dashboard/src/app/router.tsx`.

| Порядок | Название | Маршрут | Роль |
| --- | --- | --- | --- |
| 1 | Сегодня | `#/home` | оперативный центр текущего учебного дня |
| 2 | Активность | `#/calendar` | Calendar v2, выбранный день и производная история |
| 3 | Статистика | `#/stats` | аналитика периодов, качества, нагрузки, прогресса и колод |
| 4 | Колоды | `#/decks` | иерархия в текущем scope, состояние, причины и области внимания |
| 5 | Поиск | `#/search` | нативный запрос Cards/Notes, inspect и явные безопасные действия |
| 6 | Карточки | `#/cards` | ограниченная очередь проблем и постоянный Inspector активной карточки |

Профиль, Инструменты и технические страницы не являются аналитическими tabs и не входят в основную навигацию.

Stage 5 не меняет IA: `#/decks` остаётся тем же основным маршрутом, но его содержимое становится master-detail Decks v2. См. `docs/decks-v2.md`.

Stage 5.5 также не меняет маршруты. Постоянное управление темой находится в utility dock App Shell вне основной навигации, menu аватара и боковой панели Settings.

Selector RU/EN находится в том же dock и также не является пунктом навигации. См. [`localization.md`](localization.md).

## Роль Today/Home

Маршрут `#/home` сохраняет техническое имя для совместимости, но в UI называется «Сегодня».

Его задача — показать:

- состояние текущего учебного дня;
- оставшуюся нагрузку;
- важные риски;
- следующий рекомендуемый шаг.

Он не должен дублировать Profile, Activity, Statistics, Decks или Cards.

Глубокая переработка `HomePage` не входит в Stage 1.

## Dropdown аватара

Справа в topbar расположен явный trigger «Профиль» с нейтральным fallback-аватаром и chevron.

Menu разделено на два блока:

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
- не вызывает backend-действие;
- не получает токен dashboard;
- не меняет маршрут SPA.

Маршрут `#/support` не существует. Отдельная страница поддержки возможна только после отдельного продуктового решения при появлении нескольких providers.

Поведение menu с клавиатурой:

- открытие по click или `ArrowDown`;
- перемещение через `ArrowUp` и `ArrowDown`;
- `Home` и `End`;
- закрытие по `Escape`, click вне menu, выбору маршрута или внешней смене маршрута;
- после `Escape` фокус возвращается на trigger.

`#/profile` является самостоятельной локальной поверхностью всей collection: идентичность, KPI за всё время, активность и обзор колод. Он не дублирует основные маршруты Calendar, Decks и Cards и не меняет scope dashboard. См. `docs/profile-mvp.md`.

## Навигация Settings

`SettingsLayout` задаёт постоянную desktop-панель Settings Hub:

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

`#/integrations` и `#/logs` сохраняются как redirects совместимости.

Источники данных остаются диагностикой только для чтения, а не платформой внешних integrations.

## Текущие маршруты

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

## Скрытые, но сохранённые маршруты

Эти маршруты скрыты из основной навигации, но доступны через menu Profile или оболочку Settings:

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

## Будущие маршруты и правило эволюции

Statistics v1 и Search v1 добавлены только как полноценные основные маршруты.

Notifications реализованы как bell App Shell и служебный маршрут, а не основная вкладка.

Будущая IA меняется только вместе с реальными пользовательскими workflows:

- «Активность» сохраняет маршрут `#/calendar`; отдельный `#/activity` не добавляется;
- Statistics появился только вместе с полноценным продуктом и содержит пять разделов;
- FSRS живёт внутри Statistics, а не отдельной основной вкладкой;
- пользовательский поиск называется «Поиск»; старый Browse не является alias или placeholder;
- Notifications не переносятся в основную навигацию без отдельного доказанного решения;
- дополнения появляются только после проектирования соответствующей системы.

## Маршруты, которые нельзя возвращать как placeholders

```text
#/fsrs
#/browse
```

Эти и любые неизвестные hashes безопасно разрешаются в `#/home`. Aliases совместимости для них не создаются.

## Почему пользовательская и техническая навигация разделены

Основная навигация отвечает на вопрос: «Куда перейти для учёбы и анализа?»

Profile, глобальные действия, управление cache и server и диагностика решают другую задачу и создавали визуальный шум рядом с учебными разделами.

Menu аватара сохраняет заметный вход в личные и глобальные функции, а оболочка Settings не позволяет техническим страницам превратиться в изолированные маршруты.

Источники истины и тесты:

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/layout/TopNav.tsx
web-dashboard/src/layout/SettingsLayout.tsx
web-dashboard/src/app/router.test.tsx
web-dashboard/src/layout/TopNav.test.tsx
```

What’s New не является пунктом основной навигации. Он открывается действием «Что нового» в служебной группе menu Profile и из `#/settings/privacy`.

Privacy находится в группе Data оболочки Settings между Data и системными маршрутами.

## Маршрут пошаговой настройки Inspection Profiles

`#/settings/inspection-profiles` остаётся поверхностью настроек и качества данных, а не основной учебной навигацией.

Обычный путь:

```text
точный тип заметки
→ созданная настройка Basic
→ ограниченная проверка
→ явное подтверждение
```

Строгое редактирование и инструменты обслуживания остаются вторичными disclosure.
