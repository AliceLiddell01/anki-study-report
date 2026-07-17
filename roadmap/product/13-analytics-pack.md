# Stage 13 — Analytics Pack

**Status:** Planned after Stage 12

## Цель

Создать first-party Analytics Pack как доказательство Extension Pack foundation и место для optional/expensive analytics, которые не должны увеличивать core payload/startup для всех пользователей.

## Принципы

- Pack использует только Stage 12 extension contracts.
- Core Statistics/FSRS остаются canonical для базовых метрик.
- Не дублировать существующие панели ради количества функций.
- Все вычисления локальные по умолчанию.
- Никаких scheduler mutations без отдельного продукта и explicit user action.
- Remote telemetry не получает учебные данные pack.

## Scope определяется перед реализацией

Возможные кандидаты должны пройти отдельный evidence review:

- более тяжёлые longitudinal comparisons;
- optional cohort/period analyses внутри одного профиля;
- extended scheduling diagnostics;
- импортируемые first-party analytical modules.

Кандидат без конкретного вопроса, metric definition и performance budget не входит в pack.

## Completion criteria

- Pack устанавливается отдельно и не меняет core package.
- Typed compatibility/capability contract проходит.
- Optional computations не ухудшают core startup.
- Все metrics документированы и тестируются.
- Removal pack не повреждает core/profile data.
