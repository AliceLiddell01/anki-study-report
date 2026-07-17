# Stage 4 — Activity / Calendar v2

**Status:** Complete

## Первоначальный план

Превратить календарь из статической визуализации в scoped temporal workflow: выбранный день, detail view и derived activity feed, не смешивая его с Profile lifetime data.

## Фактически выполнено

- Canonical route остаётся `#/calendar`, пользовательское название — «Активность».
- Scoped daily/deck-day history и bounded year window.
- Day details и deterministic derived feed.
- Profile сохраняет all-collection lifetime semantics.
- Presentation позже отполирована Stage 5.5 без изменения data contract.

## Canonical docs

- `docs/activity-calendar-v2.md`
- `docs/navigation-ia.md`
- `docs/ui-polish-global-controls.md`
