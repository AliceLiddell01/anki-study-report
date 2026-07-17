# Stage 2 — Settings Hub

**Status:** Complete

## Первоначальный план

Собрать реальные настройки и технические страницы в desktop-first Settings Hub, перенести управление dashboard scope из Profile и не добавлять placeholder settings будущих функций.

## Фактически выполнено

- Canonical settings shell и grouped sidebar.
- Report/Data/Server typed settings model с allowlisted partial update.
- Read-only Sources и redacted Logs diagnostics.
- Явные operational actions отделены от form save.
- Per-profile Privacy и Notification Preferences добавлены только после появления реальных backend contracts.
- Unsaved state, validation, error handling и keyboard/accessibility contract.

## Текущие routes

```text
#/settings
#/settings/data
#/settings/privacy
#/settings/notifications
#/settings/server
#/settings/sources
#/settings/logs
```

## Изменение плана

Notification и Privacy settings не были частью исходного Stage 2. Они добавлены позднее как extension существующей IA, а не как заранее созданные пустые controls.

## Canonical docs

- `docs/settings-hub.md`
- `docs/config-reference.md`
- `docs/privacy-telemetry.md`
- `docs/notification-preferences-and-toasts.md`
