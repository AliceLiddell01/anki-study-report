# Notification Preferences and Toasts

Снимок контракта: 2026-07-17. `#/settings/notifications` управляет только
локальным badge и краткими in-app сообщениями. Detectors и durable Center
продолжают работать независимо от этих presentation preferences.

## Defaults и persistence

Per-profile schema v1 сохраняет:

- `showUnreadBadge: true`;
- `showInAppToasts: true`;
- `minimumToastSeverity: critical`;
- пять включённых категорий: workload, retention, deck health, card problems,
  product updates;
- `sound: none`, `osNotifications: none`.

Partial update проходит строгую allowlist validation. Unknown future preference
fields сохраняются при round trip, но не становятся активными controls без
нового контракта.

## Delivery policy

Одновременно виден максимум один toast; очередь содержит максимум три items,
остаток сворачивается в summary. Один notification доставляется как toast один
раз (`toast_delivered_at`), а history всегда остаётся в Center. Warning закрывается
через 8 секунд и ставит таймер на паузу при hover/focus; critical остаётся до
явного закрытия. Toast не переводит focus и не открывает маршрут сам.

Non-critical сообщения используют polite status, critical — sparse alert.
Звуки, OS notifications, snooze, dismiss forever, email/push и remote delivery
не реализованы.

## Проверки

Frontend tests покрывают defaults, save/reload, category controls, single
viewport, bounded queue, summary и live regions. Real-Anki
`standard/notifications` проверяет critical persistence, warning timeout,
отсутствие focus stealing, no-repeat после reload и сохранение preferences
после рестарта профиля.
