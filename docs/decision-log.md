# Decision log

Снимок документации: 2026-07-06.

Формат легковесный ADR. Статус всех решений ниже: Accepted.

## ADR-001: Dashboard как локальный React app через token-protected HTTP server

### Статус

Accepted

### Контекст

Dashboard должен быть богаче, чем Qt dialog, но работать локально рядом с Anki.

### Решение

Собирать React/Vite app в `anki_study_report/web_dashboard/` и отдавать его
через `dashboard_server.py` на `127.0.0.1` с token-protected API.

### Последствия

Появляется frontend build/package pipeline и token lifecycle. Runtime проверки
нужны для server startup и installed assets.

### Где смотреть

`anki_study_report/dashboard_server.py`, `web-dashboard/`.

## ADR-002: Payload builder как contract boundary

### Статус

Accepted

### Контекст

Frontend и backend должны иметь стабильную JSON форму.

### Решение

Держать сборку dashboard payload в `dashboard_payload.py`, а frontend contract в
`web-dashboard/src/types/report.ts`.

### Последствия

Любое изменение payload требует синхронного обновления tests/types/docs.

### Где смотреть

`tests/test_dashboard_payload.py`, `docs/dashboard-api.md`.

## ADR-003: Frontend не ходит напрямую в Anki collection

### Статус

Accepted

### Контекст

Anki collection и profile должны оставаться на Python side.

### Решение

Frontend получает `/api/report` и вызывает allowlisted API actions.

### Последствия

Frontend проще тестировать, но backend обязан публиковать полный payload.

### Где смотреть

`web-dashboard/src/app/App.tsx`, `dashboard_server.py`.

## ADR-004: Cache не меняет публичный dashboard contract

### Статус

Accepted

### Контекст

Cache нужен для скорости и истории, но не должен создавать второй API.

### Решение

`report_from_cache.py` адаптирует cache data в уже существующую report shape.

### Последствия

Cache changes требуют payload tests и fallback behavior checks.

### Где смотреть

`anki_study_report/stats_cache.py`, `anki_study_report/report_from_cache.py`.

## ADR-005: Cards preview isolation by mode

### Статус

Accepted

### Контекст

Anki note CSS может конфликтовать с dashboard CSS.

### Решение

Для `table` и `tiles` preview использовать `AnkiCardShadowPreview` и Shadow
DOM как front-only hosts. Для `ankiPreview` использовать тот же isolated
preview component в `mode="preview"` / `side="answer"` и показывать answer-only
HTML из `renderedPreview.backHtml` без отдельного front duplication.

### Последствия

Smoke/tests должны быть mode-aware. Preview CSS не должен протекать в document.
Preview не должен использовать iframe, исполнять JS templates или требовать
ослабления sanitizer.

### Где смотреть

`web-dashboard/src/components/AnkiCardShadowPreview.tsx`,
`web-dashboard/src/pages/CardsPage.tsx`.

## ADR-006: `.ankiaddon` как flat zip

### Статус

Accepted

### Контекст

Anki ожидает содержимое add-on без лишней верхней папки.

### Решение

`scripts/package_addon.py` пишет файлы из `anki_study_report/` в archive root.

### Последствия

Validator запрещает `anki_study_report/` prefix, dev deps и runtime files.

### Где смотреть

`scripts/package_addon.py`, `docs/packaging-release.md`.

## ADR-007: Generated/runtime artifacts вне git

### Статус

Accepted

### Контекст

Build outputs, logs, screenshots, cache и tokens не должны смешиваться с source.

### Решение

Игнорировать generated/runtime paths и валидировать archive against forbidden
entries.

### Последствия

Для проверки артефакта его нужно пересобирать, а не доверять старому файлу.

### Где смотреть

`.gitignore`, `scripts/package_addon.py`.

## ADR-008: Docker E2E через реальный Anki Desktop

### Статус

Accepted

### Контекст

Unit tests не ловят import hooks, profile bootstrap, native rendering и media
loading в реальном Anki.

### Решение

Поддерживать Docker E2E с Anki Desktop 26.05, isolated profile и browser/API
smoke.

### Последствия

E2E тяжелый, но обязателен для startup/rendering/media/package-layout changes.

### Где смотреть

`docker/anki-e2e/`, `docs/docker-e2e.md`.

## ADR-009: `__init__.py` как adapter/orchestration layer

### Статус

Accepted

### Контекст

Anki entrypoint неизбежно зависит от `aqt`, UI и hooks.

### Решение

Оставлять Anki wiring в `__init__.py`, а чистую логику выносить в отдельные
модули.

### Последствия

Pure modules можно импортировать и тестировать без установленного Anki.

### Где смотреть

`tests/conftest.py`, `docs/architecture.md`.
