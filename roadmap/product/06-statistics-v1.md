# Stage 6 — Statistics v1

**Status:** Complete

## Первоначальный план

Создать самостоятельную аналитическую surface только после стабилизации Navigation, Profile, Activity и Decks; использовать typed backend queries, а не вычислять метрики во frontend.

## Фактически выполнено

- `#/stats` и nested Quality/Load/Progress/Decks routes.
- Additive `statisticsHub`, bounded `POST /api/statistics/query` и cache schema evolution.
- Canonical definitions для retention, workload, progress, answer states и deck comparison.
- Visual hierarchy и chart-selection rules документированы отдельно.
- FSRS не стал отдельной вкладкой и был добавлен в Stage 7 внутри Statistics.

## Canonical docs

- `docs/statistics-v1.md`
- `docs/statistics-metric-definitions.md`
- `docs/statistics-visual-design.md`
- `docs/dashboard-api.md`

## Historical research

- `reports/research/statistics-reference-inventory.md`
