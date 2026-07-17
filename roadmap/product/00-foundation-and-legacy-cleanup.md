# Stage 0 — Foundation and Legacy Cleanup

**Status:** Complete

## Исходная задача

Сформировать безопасную локальную архитектуру add-on и удалить накопившиеся legacy aliases, placeholders, transitional adapters и дублирующие routes без возврата старого поведения ради удобства миграции.

## Фактически выполнено

- Python runtime внутри Anki, React/Vite dashboard и token-protected loopback HTTP server.
- Стабильная граница `dashboard_payload.py` ↔ frontend types/runtime validators.
- SQLite stats cache, report adapter, local media boundary и safe Browser/actions contracts.
- Shadow DOM preview isolation без iframe/произвольного JavaScript.
- Реальный Anki Desktop Docker E2E, package validators и flat `.ankiaddon` contract.
- Legacy cleanup завершён серией малых этапов: удалены устаревшие routes/placeholders и payload aliases, укреплены static fallback/status/cache boundaries.
- Финальная IA после cleanup стала отправной точкой для Stage 1, а не поводом вернуть legacy navigation.

## Что изменилось относительно ранних планов

Cleanup превратился из локальной уборки в архитектурный gate: любое удаление проверялось по production code/tests, а compatibility layer сохранялся только при доказанной необходимости.

## Canonical docs

- `docs/architecture.md`
- `docs/dashboard-api.md`
- `docs/security-and-safety.md`
- `docs/packaging-release.md`

## Historical evidence

- `reports/product/legacy-cleanup-handoff.md`
- `reports/audits/legacy-cleanup-inventory.md`
- `reports/audits/card-alias-audit.md`

## Осталось вне scope

Legacy не должен возвращаться как shortcut при реализации Cards v2, DLC или новых routes. Новые migrations должны быть явными и versioned, а не скрытыми aliases.
