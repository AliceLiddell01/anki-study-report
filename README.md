# Anki Study Report

## Signals и уведомления

Текущий dashboard содержит полностью локальные study signals: bell и compact
panel, durable `#/notifications`, per-profile настройки
`#/settings/notifications` и bounded in-app toasts. Детекторы не изменяют
коллекцию и не отправляют signal/evidence/entity data в telemetry. Контракты:
`docs/signals-foundation.md`, `docs/notification-center.md` и
`docs/notification-preferences-and-toasts.md`.

Документация этого репозитория описывает текущую версию проекта на 2026-07-17.
Ее цель - быть входной точкой для человека или нейронки, которой нужно быстро
понять, что здесь находится, как это запускать, какие контракты нельзя ломать и
почему часть решений устроена именно так.

Anki Study Report - это add-on для Anki 26.05+, который собирает статистику
обучения, строит Markdown/HTML-отчет и публикует локальный веб-dashboard с
детализацией по прогрессу, колодам, карточкам, FSRS, календарю, нативному
поиску Cards/Notes, логам и явным undoable действиям.
Web dashboard полностью поддерживает русский и английский интерфейс; язык
переключается глобально и сохраняется локально в браузере.

## Быстрый вход

Основной код add-on находится в `anki_study_report/`.

Frontend dashboard находится в `web-dashboard/`. Это Vite + React + TypeScript
приложение, которое после сборки копируется в
`anki_study_report/web_dashboard/` и затем упаковывается внутрь `.ankiaddon`.

Тесты находятся в `tests/` и `web-dashboard/src/**/*.test.ts(x)`.

Скрипты разработки, сборки, упаковки и E2E находятся в `scripts/` и
`docker/anki-e2e/`.

Главный релизный артефакт:

```text
anki_study_report.ankiaddon
```

Он является zip-архивом с плоским содержимым add-on, без верхней папки
`anki_study_report/`.

Текущая primary navigation dashboard:
`Сегодня → Активность → Статистика → Колоды → Поиск → Карточки`.
Профиль, Инструменты, Настройки и безопасная внешняя ссылка «Поддержать проект»
доступны через profile menu; Сервер, Источники данных и Логи собраны в settings
navigation. Полное решение и правила эволюции routes описаны в
`docs/navigation-ia.md`.

`#/profile` — локальная all-collection витрина текущего Anki-профиля с lifetime
KPI, активностью, обзором колод и per-profile настройками даты/сортировки.
`#/calendar` сохраняет canonical route, но отображается как «Активность» и
объединяет scoped calendar, day details и derived history feed.

## Roadmap и исторические отчёты

Текущая карта завершённых и будущих этапов вынесена из operational docs:

- [Главный roadmap](roadmap/README.md)
- [Продуктовые этапы](roadmap/product/README.md)
- [Платформенные CI/CD/E2E этапы](roadmap/platform/README.md)
- [Исторические отчёты и audits](reports/README.md)

```text
docs/       текущее устройство и обязательные контракты
roadmap/    этапы, зависимости, planned/completed scope
reports/    исторические handoff, audits и measurements
```

Текущий продуктовый контур завершён до Stage 9.5. Следующий рекомендуемый
продуктовый этап — Stage 10 Cards v2 / Problem Triage; отдельная CI-линия не
смешивается с ним. Платформенный GHCR cloud cutover завершён до CI Stage 6B;
следующие CI-оптимизации выполняются только по измеримым bottleneck/flake данным.

## Самые важные команды

Каноническая локальная frontend/Python/package проверка без Docker:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

GitHub Actions вызывает эту же команду как cloud-primary Fast CI. Более узкий
frontend-oriented aggregate остаётся доступен через
`cd web-dashboard; pnpm run test:all`.

Релизная сборка add-on с проверками:

```powershell
.\build_ankiaddon.ps1
```

Подготовка канонической версии и ручной gated release после merge:

```powershell
node scripts/run_python.mjs scripts/prepare_release.py --version 1.0.0 --check
gh workflow run release.yml --ref master -f version=1.0.0 -f channel=stable
```

Workflow публикует только после exact-artifact real-Anki gate и approval
Environment `ankiweb-production`; merge или push автоматически релиз не создают.

Полный прогон с Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

Только Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly
```

Финальный Cards/APKG/Perf100 smoke на реальном Anki Desktop:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker -RequireApkgFixture -Perf100
```

Быстрая упаковка и проверка архива:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
node scripts/run_python.mjs scripts/package_addon.py --check-only
```

## Документация

- [Индекс актуальной документации](docs/README.md)
- [Обзор проекта](docs/project-overview.md)
- [Архитектура](docs/architecture.md)
- [Разработка и проверки](docs/development.md)
- [Dashboard API и payload-контракт](docs/dashboard-api.md)
- [Frontend map](docs/frontend-map.md)
- [Navigation / Information Architecture](docs/navigation-ia.md)
- [Settings Hub](docs/settings-hub.md)
- [Profile MVP](docs/profile-mvp.md)
- [Activity / Calendar v2](docs/activity-calendar-v2.md)
- [Decks v2](docs/decks-v2.md)
- [Statistics v1](docs/statistics-v1.md)
- [FSRS analytics](docs/fsrs-analytics.md)
- [Search Query Foundation](docs/search-query-foundation.md)
- [Search v1 и Safe Actions](docs/search-v1-and-safe-actions.md)
- [Signals Foundation](docs/signals-foundation.md)
- [Notification Center](docs/notification-center.md)
- [Notification Preferences & Toasts](docs/notification-preferences-and-toasts.md)
- [UI Polish & Global Controls](docs/ui-polish-global-controls.md)
- [Локализация RU/EN](docs/localization.md)
- [Product notices и consent](docs/product-notices-and-consent.md)
- [Telemetry client](docs/telemetry-client.md)
- [Privacy и telemetry contract](docs/privacy-telemetry.md)
- [CI и gated release delivery](docs/ci-cd.md)
- [GHCR-only cloud E2E consumer](docs/ghcr-e2e-consumer.md)
- [Release automation](docs/release-automation.md)
- [Verification run policy](docs/verification-run-policy.md)
- [Матрица проверок](docs/test-matrix.md)
- [Security and safety model](docs/security-and-safety.md)
- [Config reference](docs/config-reference.md)
- [Docker E2E](docs/docker-e2e.md)
- [Производительность Docker E2E](docs/e2e-performance.md)
- [Упаковка и релиз](docs/packaging-release.md)
- [Release checklist](docs/release-checklist.md)
- [Fixtures and test data](docs/fixtures-and-test-data.md)
- [Decision log](docs/decision-log.md)
- [Codex/AI agent rules](docs/codex-agent-rules.md)
- [Передача контекста новому чату/нейронке](docs/ai-handoff.md)

Если нужно быстро сориентировать новый чат, дать ему `README.md`,
`roadmap/README.md`, `docs/ai-handoff.md` и профильный current-contract файл.
Исторические результаты брать из `reports/`, не из `docs/`.

## Участие и безопасность

- [Как внести вклад](CONTRIBUTING.md)
- [Кодекс поведения](CODE_OF_CONDUCT.md)
- [Политика сообщения об уязвимостях](SECURITY.md)
- [Лицензия GNU GPL v3.0 only](LICENSE)

Сообщения о предполагаемых уязвимостях нельзя публиковать в открытых Issues.
Используйте приватный канал, указанный в `SECURITY.md`.

## Контрактные правила

1. Не менять форму dashboard payload без синхронного обновления frontend-типов,
   тестов и документации.
2. Не добавлять runtime-артефакты в git: логи, screenshots, `e2e-artifacts/`,
   `web-dashboard/dist/`, `anki_study_report/web_dashboard/`, `.ankiaddon`.
3. Для узких исправлений сначала проверить текущий фактический контракт. Если
   production payload правильный, править устаревший тест, а не рабочий код.
4. После py_compile удалять `__pycache__`, чтобы сборка и package validation не
   смешивались с временными файлами.
5. Для изменений dashboard/runtime/рендеринга карточек по возможности
   подтверждать поведение на реальном локальном surface или Docker E2E.
6. Cards preview target - desktop/local dashboard: `table` и `tiles` остаются
   front-only через `AnkiCardShadowPreview` / Shadow DOM host, а `ankiPreview`
   использует тот же isolated preview host в answer-only режиме из
   `renderedPreview.backHtml` без iframe и без отдельного дублирования front.
7. Проект распространяется по `GPL-3.0-only`, если для конкретного файла или
   стороннего материала явно не указаны иные совместимые условия. Публичные
   history, Actions logs/artifacts и fixtures не должны содержать secrets, PII
   или материалы без разрешения на распространение.

## Облачные проверки

Fast CI автоматически проверяет push в `master`/`codex/**` и pull requests.
Отдельный workflow `Full Docker / Anki E2E` запускается вручную и проверяет
реальный Anki Desktop в Docker на GitHub-hosted Ubuntu. Cloud workflow использует
только exact digest-pinned GHCR environment: manual run требует exact successful
Fast CI package, а release gate — exact release artifact. Cloud BuildKit и
`type=gha` cache больше не используются; локальный Docker build fallback сохранён.
Доступные режимы: `standard`, `strict-apkg` и diagnostic `perf100`. Полный
контракт и команды — в `docs/ci-cd.md`, `docs/docker-e2e.md` и
`docs/ghcr-e2e-consumer.md`.
