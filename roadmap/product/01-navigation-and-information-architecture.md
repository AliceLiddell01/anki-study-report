# Stage 1 — Navigation / Information Architecture

**Status:** Complete

## Первоначальный план

Разделить пользовательские учебные разделы, профиль, настройки, диагностику и служебные инструменты; не смешивать этот этап с legacy cleanup или глубокой переработкой страниц.

## Фактический результат

- Primary navigation зафиксирована как `Сегодня → Активность → Статистика → Колоды → Поиск → Карточки`.
- Profile, Settings, Tools и Support вынесены в avatar menu.
- Технические routes объединены Settings shell; старые `#/integrations` и `#/logs` оставлены только как redirects к canonical destinations.
- FSRS находится внутри Statistics, а не отдельной primary-вкладкой.
- Notification bell добавлен позднее в App Shell, но не стал primary navigation item.
- `#/notifications` — utility/history route; `#/settings/notifications` — settings route.
- Unknown/removed hashes безопасно возвращаются на `#/home`; `#/fsrs` и `#/browse` не возвращены как placeholders.

## Изменение плана

Stage 1 изначально определял только базовую IA. Поздние реальные workflows (Statistics, Search, Notifications) расширили route registry, не меняя основного принципа: новый route появляется только вместе с работающим продуктовым контуром.

## Canonical docs

- `docs/navigation-ia.md`
- `docs/frontend-map.md`
- `docs/settings-hub.md`

## Зависимость следующих этапов

Cards v2 должен использовать существующий `#/cards` и contextual handoff из Search/Signals, а не создавать ещё одну конкурирующую primary route.
