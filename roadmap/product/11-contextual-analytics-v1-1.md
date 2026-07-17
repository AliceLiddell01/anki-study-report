# Stage 11 — Contextual Analytics v1.1

**Status:** Conditional after Cards v2 and Core 1.0 hardening

## Цель

Добавлять аналитику только там, где Cards v2, Signals или реальные пользовательские сценарии выявили доказанный вопрос, на который текущие Statistics/FSRS не отвечают.

## Принцип отбора

Новая метрика принимается только при наличии:

1. конкретного пользовательского решения;
2. точного определения и unit/sample rules;
3. data availability без небезопасного full-scan;
4. понятного contextual placement;
5. тестируемой интерпретации и RU/EN copy.

## Возможный scope

- contextual panels из Cards triage и Signals;
- missing comparison/baseline views, подтверждённые Stage 10;
- улучшения metric explanations и evidence links;
- backend narrative localization, только если structured backend-owned narrative действительно потребуется;
- performance/coverage improvements существующих queries.

## Out of scope

- ещё одна общая Statistics page;
- дублирование FSRS/Anki native analytics;
- arbitrary dashboards/charts;
- vanity metrics;
- изменение scheduler/config;
- remote analytics pack до Stage 12/13.

## Completion criteria

Каждое добавление имеет canonical metric definition, API parity, contextual UX, bounded query, tests и verification scope. Если доказанных gaps нет, Stage 11 может быть закрыт без feature expansion.
