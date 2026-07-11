# Обзор проекта

Снимок документации: 2026-07-05.

`Anki Study Report` - локальный add-on для Anki, который помогает понять
качество обучения не только по общим числам, но и по причинам: где провалы,
какие колоды проседают, какие карточки требуют внимания, насколько тяжелая
нагрузка впереди и что может помочь прямо сейчас.

## Что делает add-on

- Собирает метрики из коллекции Anki: revlog, карточки, колоды, расписание,
  FSRS, календарную активность.
- Строит Markdown/HTML-отчет через диалог внутри Anki.
- Поднимает локальный HTTP dashboard на `127.0.0.1`, по умолчанию на порту
  `8766`.
- Публикует временный dashboard payload, который frontend читает через
  `/api/report?token=...`.
- Может использовать SQLite cache для быстрых dashboard-отчетов и истории.
- Показывает карточки, требующие внимания: leech, repeated again, slow answer,
  low pass rate, missing audio/image/meaning/example/part of speech.
- Умеет отдавать безопасные media-preview через `/api/media`.
- Имеет Docker E2E среду, где add-on запускается внутри реального Anki Desktop.

## Текущие runtime-границы

Проект состоит из трех крупных частей:

1. Python add-on (`anki_study_report/`)
2. React dashboard (`web-dashboard/`)
3. Проверки/сборка/E2E (`tests/`, `scripts/`, `docker/anki-e2e/`)

Python add-on является источником данных и серверной логики. Frontend не
подключается напрямую к Anki: он получает уже опубликованный JSON payload и
вызывает ограниченные API действия. Docker E2E нужен для проверки того, что все
это работает не только в тестовых заглушках, но и в реальном Anki Desktop.

## Важные файлы

```text
anki_study_report/__init__.py              Anki entrypoint, UI dialogs, orchestration
anki_study_report/metrics.py               сбор основных метрик из коллекции
anki_study_report/dashboard_payload.py     чистая сборка JSON payload для dashboard
anki_study_report/dashboard_server.py      локальный HTTP server и API endpoints
anki_study_report/stats_cache.py           SQLite cache менеджер
anki_study_report/report_from_cache.py     адаптация cache в report/dashboard parts
anki_study_report/report_builder.py        Markdown/HTML report builder
anki_study_report/note_intelligence.py     preview/sanitizer/card intelligence
anki_study_report/browser_actions.py       безопасные поисковые запросы для Anki Browser
anki_study_report/dashboard_actions.py     действия dashboard -> Anki
anki_study_report/config_service.py        config defaults/read/write normalization

web-dashboard/src/app/                     загрузка report и hash-router
web-dashboard/src/pages/                   страницы dashboard
web-dashboard/src/lib/                     frontend normalization/helpers
web-dashboard/src/types/report.ts          TypeScript контракт dashboard payload

scripts/package_addon.py                   сборка и валидация .ankiaddon
build_ankiaddon.ps1                        релизная сборка с проверками
scripts/run_full_check.ps1                 локальный полный прогон + Docker опционально
scripts/run_anki_e2e_docker.ps1            запуск Docker E2E
docker/anki-e2e/README.md                  подробности Docker E2E среды
```

## Что считается source of truth

Для dashboard payload source of truth - связка:

- `anki_study_report/dashboard_payload.py`
- `web-dashboard/src/types/report.ts`
- `tests/test_dashboard_payload.py`
- frontend tests вокруг нормализации карточек и actions API

Для упаковки source of truth - `scripts/package_addon.py` и
`tests/test_package_build.py`.

Для Docker E2E source of truth - `docker/anki-e2e/README.md`,
`scripts/run_anki_e2e_docker.ps1`, `scripts/run_full_check.ps1` и артефакты из
`e2e-artifacts/`.

Дополнительные навигационные документы:

- `docs/test-matrix.md` - какие проверки запускать.
- `docs/troubleshooting.md` - диагностика типовых проблем.
- `docs/security-and-safety.md` - token/server/media/rendering safety.
- `docs/decision-log.md` - почему приняты текущие архитектурные решения.
- `docs/settings-hub.md` - canonical settings routes, public model и save/runtime boundaries.
- `docs/profile-mvp.md` - per-Anki-profile identity, lifetime all-collection contract и persistence.
- `docs/activity-calendar-v2.md` - scoped temporal history, day details и deterministic derived feed.
- `docs/decks-v2.md` - scoped deck hierarchy, direct/subtree metrics, health/confidence и safe Browser actions.
- `docs/ui-polish-global-controls.md` - persistent theme utility и presentation-only Activity/Decks polish.

## Что не является source of truth

- Уже собранный `anki_study_report.ankiaddon`, если он не пересобран в текущем
  checkout.
- `web-dashboard/dist/` и `anki_study_report/web_dashboard/`, если не выполнен
  свежий `pnpm run build:addon` или `build_ankiaddon.ps1`.
- Логи, screenshots и `e2e-artifacts/`: они важны для диагностики, но не должны
  попадать в git или архив add-on.
