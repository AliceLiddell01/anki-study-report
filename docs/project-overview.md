# Обзор проекта

**Снимок:** 2026-07-28

Anki Study Report — локальное расширение для Anki 26.05+, которое объясняет учебный прогресс, нагрузку и обнаруженные проблемы через отчёт Markdown/HTML и dashboard на React.

## Контуры runtime

1. Python add-on: `anki_study_report/`;
2. dashboard на React/TypeScript: `web-dashboard/`;
3. тесты, сборка и E2E: `tests/`, `scripts/`, `docker/anki-e2e/`;
4. отдельный приватный сервис телеметрии с явным согласием: `anki-study-report-telemetry`.

Python отвечает за доступ к collection и server-side-логику. Frontend получает ограниченные payload и вызывает API из allowlist; он никогда не читает collection Anki напрямую.

Real-Anki E2E в Docker проверяет интеграционные риски, которые невозможно покрыть unit-тестами.

## Текущий продукт

Маршрут `#/settings/inspection-profiles` предоставляет локальную декларативную настройку качества для каждого типа заметки:

- явное подтверждение;
- безопасный предпросмотр с ограниченным объёмом;
- обработка конфликтов revision;
- строгий import/export.

Inspection Profiles не изменяют объекты Anki. Очередь Cards и Inspector остаются отдельной поверхностью Core C1.

Принятый продуктовый контур включает:

- локальный отчёт и dashboard с историей из cache;
- Profile, Activity и иерархию колод;
- Statistics и read-only-аналитику FSRS;
- нативный поиск Cards/Notes;
- отменяемые Safe Actions из allowlist;
- изолированный и санитизированный предпросмотр карточки;
- локальные для профиля Signals и Notification Center;
- ограниченную техническую телеметрию с явным согласием через отдельный сервис.

Текущая основная навигация:

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

## Roadmap

Завершённая продуктовая работа сохранена как Stage 0–9.5. Будущая работа разделена на независимые треки:

- [Core](../roadmap/core/README.md): C1 завершён; C2 implementation/integration влиты, owner acceptance требует bounded remediation; затем обязательны C3–C6;
- [Геймификация](../roadmap/gamification/README.md): независимый research/product track; G4.3 завершён как `FROZEN_PRE_SCREENING`, G4.4 ещё не начат, production integration запрещена;
- [Эксплуатация телеметрии](../roadmap/operations/README.md): отдельные защищённые внутренние инструменты;
- [Идентификация](../roadmap/identity/README.md): условный gate непрерывности;
- [Расширения](../roadmap/extensions/README.md): условная или отложенная экосистема first-party;
- [Платформа](../roadmap/platform/README.md): независимая работа над CI/CD, E2E и выпуском.

Core не зависит от геймификации, аккаунтов, административного UI телеметрии или пакетов расширений.

## Границы источников истины

### Payload dashboard

- `anki_study_report/dashboard_payload.py`;
- `web-dashboard/src/types/report.ts`;
- тесты payload, server и frontend;
- `docs/dashboard-api.md`.

### Сборка пакета

- `scripts/package_addon.py`;
- `tests/test_package_build.py`;
- `docs/packaging-release.md`.

### Real-Anki E2E

- `docker/anki-e2e/README.md`;
- `scripts/run_anki_e2e_docker.ps1`;
- `scripts/run_full_check.ps1`;
- проверенные артефакты workflow.

### Signals и уведомления

- `anki_study_report/signal_detection.py`;
- `anki_study_report/notification_store.py`;
- `docs/signals-foundation.md`;
- `docs/notification-center.md`.

### Телеметрия

- контракты локального client находятся в этом репозитории;
- контракты ingestion, retention, deletion и deployment находятся в отдельном приватном репозитории телеметрии.

### Gamification research

- current contract index: `docs/gamification/README.md`;
- track status and stage dependencies: `roadmap/gamification/README.md`;
- current G4.3 closeout: `roadmap/gamification/g4-core-economy-candidate-protocol.md`;
- historical post-merge report: `reports/research/g4-3-candidate-economy-protocol-closeout-2026-07-28.md`.

Research contracts, fixtures and dry matrices remain outside the production add-on, dashboard API, Fast CI and release package until a separate owner decision.

## Важные инварианты

- односторонние изменения payload или публичного контракта запрещены;
- frontend не получает прямой доступ к collection;
- граница loopback и токена сохраняется;
- поверхности произвольного SQL, RPC, действий или plugins отсутствуют;
- sanitizer, проверку media и изоляцию предпросмотра нельзя ослаблять;
- сгенерированные и runtime-артефакты не попадают в Git или пакет;
- локальные подтверждения Signals не являются телеметрией;
- исследовательские кандидаты не считаются production-функциями;
- выпуск использует точный артефакт, выполняется вручную и требует одобрения.

Актуальные подробности:

- [Архитектура](architecture.md);
- [Безопасность](security-and-safety.md);
- [Журнал решений](decision-log.md);
- [Roadmap](../roadmap/README.md);
- [Передача контекста ИИ](ai-handoff.md).
