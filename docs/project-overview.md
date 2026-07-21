# Обзор проекта

**Снимок:** 2026-07-18

Anki Study Report — локальное расширение для Anki 26.05+, которое объясняет прогресс обучения, нагрузку и проблемы через Markdown/HTML report и React dashboard.

## Контуры runtime

1. Python add-on: `anki_study_report/`;
2. React/TypeScript dashboard: `web-dashboard/`;
3. tests/build/E2E: `tests/`, `scripts/`, `docker/anki-e2e/`;
4. отдельный приватный opt-in telemetry service: `anki-study-report-telemetry`.

Python отвечает за доступ к collection и server-side logic. Frontend получает bounded payloads и вызывает allowlisted API; он никогда не читает Anki collection напрямую.

Real-Anki Docker E2E проверяет integration risks, которые невозможно покрыть unit tests.

## Текущий продукт

Маршрут `#/settings/inspection-profiles` предоставляет локальную declarative конфигурацию качества для каждого note type с:

- явным confirmation;
- bounded safe preview;
- обработкой revision conflicts;
- strict import/export.

Inspection Profiles не изменяют объекты Anki. Cards queue/Inspector остаётся отдельной поверхностью Core C1.

Принятый product contour включает:

- локальный report/dashboard и cache-backed history;
- Profile, Activity и hierarchy колод;
- Statistics и read-only FSRS analytics;
- native Cards/Notes Search;
- allowlisted undoable Safe Actions;
- изолированный и санитизированный preview карточки;
- local per-profile Signals и Notification Center;
- opt-in bounded technical telemetry через отдельный service.

Текущая primary navigation:

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

## Roadmap

Завершённая продуктовая работа сохранена как Stage 0–9.5. Будущая работа разделена на независимые треки:

- [Core](../roadmap/core/README.md): `C1 Cards v2`, затем `C2 Core 1.0`; `C3` только для доказанных пробелов;
- [Gamification](../roadmap/gamification/README.md): параллельное research/product направление, ещё не готовое для production;
- [Telemetry operations](../roadmap/operations/README.md): отдельные защищённые внутренние tools;
- [Identity](../roadmap/identity/README.md): conditional continuity gate;
- [Extensions](../roadmap/extensions/README.md): conditional/deferred first-party ecosystem;
- [Platform](../roadmap/platform/README.md): независимые CI/CD/E2E/release работы.

Core не зависит от gamification, accounts, telemetry admin UI или extension packs.

## Границы source of truth

### Dashboard payload

- `anki_study_report/dashboard_payload.py`;
- `web-dashboard/src/types/report.ts`;
- payload/server/frontend tests;
- `docs/dashboard-api.md`.

### Packaging

- `scripts/package_addon.py`;
- `tests/test_package_build.py`;
- `docs/packaging-release.md`.

### Real-Anki E2E

- `docker/anki-e2e/README.md`;
- `scripts/run_anki_e2e_docker.ps1`;
- `scripts/run_full_check.ps1`;
- проверенные workflow artifacts.

### Signals и notifications

- `anki_study_report/signal_detection.py`;
- `anki_study_report/notification_store.py`;
- `docs/signals-foundation.md`;
- `docs/notification-center.md`.

### Telemetry

- local client contracts находятся в этом repository;
- ingestion, retention, deletion и deployment contracts находятся в отдельном приватном telemetry repository.

## Важные инварианты

- запрещены односторонние изменения payload/public contract;
- frontend не получает прямой доступ к collection;
- loopback/token boundary сохраняется;
- arbitrary SQL/RPC/action/plugin surface отсутствует;
- sanitizer, media validation и preview isolation нельзя ослаблять;
- generated/runtime artifacts не попадают в Git или package;
- local signal evidence не является telemetry;
- research candidates не считаются production features;
- release использует exact artifact, выполняется вручную и требует approval.

Актуальные подробности:

- [Архитектура](architecture.md);
- [Безопасность](security-and-safety.md);
- [Decision log](decision-log.md);
- [Roadmap](../roadmap/README.md);
- [AI handoff](ai-handoff.md).