# Stage 5 — Decks v2

**Status:** Complete

## Первоначальный план

Сделать `#/decks` рабочим master-detail разделом со scoped hierarchy, direct/subtree metrics, health/confidence и безопасными переходами в Anki Browser.

## Фактически выполнено

- Normalized `deckHub` contract и deterministic hierarchy.
- Direct и subtree metrics разделены.
- Health, confidence и descendant issues не смешиваются в одно число.
- Filtered decks исключены из небезопасных операций.
- Safe Browser actions используют deck IDs, names остаются presentation data.
- Contextual notification navigation позже переиспользовала существующий route без ID в hash.

## Canonical docs

- `docs/decks-v2.md`
- `docs/dashboard-api.md`
- `docs/navigation-ia.md`
