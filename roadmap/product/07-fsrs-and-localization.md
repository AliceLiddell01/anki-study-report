# Stage 7 — FSRS Analytics and Localization Closure

**Status:** Complete

## Первоначальный план

Stage 7 вырос из серии аналитических и visual passes. Завершающий пункт старого roadmap — **Stage 7.7.1 Localization Cleanup** — предполагал небольшой maintenance: frontend literals, locale formatting, tests и E2E summary без массовой backend narrative migration.

## Фактически выполнено

### FSRS analytics

- Read-only FSRS center внутри `#/stats/fsrs`.
- Memory, calibration, steps и simulator views.
- Native Anki 26.05 data/config/simulator остаются source of truth.
- Никаких scheduler/config/history writes и Apply action.
- Compatible groups, retention overrides и sample limitations задокументированы.
- Visual delivery и final UX pass закрыли layout, chunking, bundle и real-Anki evidence.

### Localization

- Typed RU/EN product resources и русский fallback.
- Locale-aware formatting для дат/чисел.
- Убраны frontend-owned literals и добавлены parity/tests/E2E states.
- Stage 7.7.1 остался maintenance-этапом и не переносил произвольные backend narratives.
- Поздние structured privacy/notification texts локализованы в собственных этапах, а не задним числом через Stage 7.7.1.

## Canonical docs

- `docs/fsrs-analytics.md`
- `docs/fsrs-metric-definitions.md`
- `docs/localization.md`
- `docs/statistics-visual-design.md`

## Historical evidence/research

- `reports/product/stage-7-5-fsrs-visual-delivery-report.md`
- `reports/product/stage-7-6-fsrs-final-pass-report.md`
- `reports/research/fsrs-helper-reference-inventory.md`
