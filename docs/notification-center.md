# Notification Center

Снимок контракта: 2026-07-17. Notification Center — локальная история
учебных сигналов и product-update items. Он не является inbox аккаунта и не
синхронизируется между профилями или устройствами.

## Поверхности

- `NotificationBell` в App Shell показывает bounded unread badge (`99+`).
- Compact panel — non-modal dialog, максимум 8 новых элементов, Escape
  закрывает его и возвращает focus на bell.
- `#/notifications` показывает tabs `all`, `unread`, `active`, category filter,
  pagination, `Mark all read` и durable resolved history.
- Release item использует тот же `ProductNoticeStore`/What’s New source; второй
  changelog store не создаётся.

Read не разрешает signal, а resolution не помечает item прочитанным. Список и
summary обновляются после действий через локальное событие, но source of truth
остаётся SQLite профиля.

## Контекстные переходы

Workload открывает `#/stats/load`, retention — `#/stats/quality`, deck health —
`#/decks`, repeated Again — `#/search`, product update — существующее What’s
New. Для deck/card используется bounded session handoff: ID не попадает в hash,
localStorage или remote telemetry. Search принимает handoff как локальный
баннер и не выполняет произвольный query автоматически.

## API и безопасность

Все endpoints требуют текущий dashboard token и bind только к loopback server.
Response проходит точную TypeScript validation. Page limit не превышает 50;
unknown tabs/categories/fields отклоняются. В browser artifacts отсутствуют
token, Authorization, runtime DB и полные entity-ID lists.

## Accessibility и локализация

Bell имеет `aria-expanded`/`aria-controls`; panel управляет focus; tabs,
pagination и filters используют native semantics. Notification copy и actions
имеют RU/EN parity, light/dark проверены real-browser screenshots.

Канонические файлы: `NotificationBell.tsx`, `NotificationItemCard.tsx`,
`NotificationCenterPage.tsx`, `notificationsApi.ts` и namespace
`notifications` в locale-файлах.
