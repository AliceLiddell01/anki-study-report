# Stage 8 — Search Query Foundation, Search v1 and Safe Actions

**Status:** Complete

## Старый план

```text
8.0 Search Query Foundation
8.1 Search v1
8.5 Safe Actions v1
8.6 Optional Safe Actions Expansion
```

## Фактический результат

### Stage 8.0 — Query foundation

- Native Anki Cards/Notes queries.
- Typed `CardId`, `NoteId`, `DeckId`, `NotetypeId` boundaries.
- Compact models, deterministic sorting, bounded pagination и inspect API.
- Serialized/non-blocking collection reads.
- Отдельная стабилизация 8.0.1 закрыла complete runtime validators, `pageCount`/`pageLimit` semantics и deprecated `Collection.save()` usage.

### Stage 8.1 — Search v1

- Canonical `#/search` с Cards/Notes modes.
- Native query input и bounded structured filters.
- Results table, selection, lazy compact inspector и sorting.
- Session-only raw query policy; query не попадает в URL/telemetry.
- Open selected cards/notes in native Anki Browser.
- RU/EN, light/dark и keyboard/accessibility coverage.

### Stage 8.5 — Safe Actions v1

- Explicit CardAction/NoteAction contracts.
- Suspend/unsuspend, set/clear flag, add/remove note tags.
- Batch caps, typed results и один native undo step.

### Stage 8.6 — Expansion

Пользовательская необходимость была подтверждена в том же implementation cycle, поэтому optional scope выполнен:

- bury/unbury;
- move cards to normal deck;
- filtered destination/source safety restrictions.

## Отличие от плана

8.1, 8.5 и 8.6 были реализованы как один связный продуктовый workflow поверх уже принятого 8.0, а не как три независимые UI-заглушки.

## Canonical docs

- `docs/search-query-foundation.md`
- `docs/search-v1-and-safe-actions.md`
- `docs/dashboard-api.md`
- `docs/security-and-safety.md`
