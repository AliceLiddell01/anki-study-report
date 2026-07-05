# Anki Study Report

Документация этого репозитория описывает текущую версию проекта на 2026-07-05.
Ее цель - быть входной точкой для человека или нейронки, которой нужно быстро
понять, что здесь находится, как это запускать, какие контракты нельзя ломать и
почему часть решений устроена именно так.

Anki Study Report - это add-on для Anki 26.05+, который собирает статистику
обучения, строит Markdown/HTML-отчет и публикует локальный веб-dashboard с
детализацией по прогрессу, колодам, карточкам, FSRS, календарю, логам и
обслуживающим действиям.

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

## Самые важные команды

Полная локальная frontend/Python/package проверка без Docker:

```powershell
cd web-dashboard
pnpm run test:all
```

Релизная сборка add-on с проверками:

```powershell
.\build_ankiaddon.ps1
```

Полный прогон с Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

Только Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly
```

Быстрая упаковка и проверка архива:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
node scripts/run_python.mjs scripts/package_addon.py --check-only
```

## Документация

- [Обзор проекта](docs/project-overview.md)
- [Архитектура](docs/architecture.md)
- [Разработка и проверки](docs/development.md)
- [Dashboard API и payload-контракт](docs/dashboard-api.md)
- [Матрица проверок](docs/test-matrix.md)
- [Диагностика типовых проблем](docs/troubleshooting.md)
- [Frontend map](docs/frontend-map.md)
- [Security and safety model](docs/security-and-safety.md)
- [Config reference](docs/config-reference.md)
- [Docker E2E](docs/docker-e2e.md)
- [Упаковка и релиз](docs/packaging-release.md)
- [Release checklist](docs/release-checklist.md)
- [Fixtures and test data](docs/fixtures-and-test-data.md)
- [Decision log](docs/decision-log.md)
- [Codex/AI agent rules](docs/codex-agent-rules.md)
- [Передача контекста новому чату/нейронке](docs/ai-handoff.md)

Если нужно быстро сориентировать новый чат, обычно достаточно дать ему этот
`README.md` и папку `docs/`.

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
