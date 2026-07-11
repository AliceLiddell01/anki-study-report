# Передача контекста новому чату/нейронке

Снимок документации: 2026-07-11.

Этот файл написан как короткий briefing для нового чата, агента или человека,
который впервые видит checkout. Если времени мало, начать нужно отсюда, потом
читать `README.md` и профильную страницу из `docs/`.

## Что это за проект

Это Anki add-on `Anki Study Report`. Он работает внутри Anki 26.05+, собирает
статистику обучения, строит Markdown/HTML report и публикует локальный React
dashboard через token-protected HTTP server.

Проект смешанный:

- Python add-on runtime: `anki_study_report/`
- React dashboard: `web-dashboard/`
- Python tests: `tests/`
- Frontend tests: `web-dashboard/src/**/*.test.ts(x)`
- Packaging scripts: `scripts/package_addon.py`, `build_ankiaddon.ps1`
- Real Anki Desktop E2E: `docker/anki-e2e/`

## Что прочитать первым

1. `README.md` - быстрый вход и команды.
2. `docs/project-overview.md` - карта проекта и source-of-truth.
3. `docs/architecture.md` - границы модулей.
4. Если задача про dashboard contract - `docs/dashboard-api.md`.
5. Если задача про сборку - `docs/packaging-release.md`.
6. Если задача про реальный Anki/Desktop/rendering - `docs/docker-e2e.md`.
7. Если задача про диагностику - `docs/troubleshooting.md`.
8. Если нужно выбрать проверки - `docs/test-matrix.md`.
9. Если агенту нужны правила поведения - `docs/codex-agent-rules.md`.
10. Если задача про GitHub Actions/Fast CI - `docs/ci-cd.md`.

Дополнительные справочники:

```text
docs/security-and-safety.md      server/media/actions/rendering safety
docs/release-checklist.md        публикация .ankiaddon
docs/fixtures-and-test-data.md   fixtures, mock data, synthetic E2E data
docs/frontend-map.md             routes/pages/helpers/tests frontend
docs/navigation-ia.md            current primary nav, profile menu, settings hierarchy
docs/settings-hub.md             Stage 2 settings routes, persistence, Today/settings boundary
docs/profile-mvp.md              Stage 3 all-collection Profile, per-profile persistence/API
docs/activity-calendar-v2.md     Stage 4 scoped calendar, day details and derived feed
docs/decks-v2.md                 Stage 5 scoped hierarchy, direct/subtree health and Browser actions
docs/config-reference.md         config/env vars/runtime paths
docs/decision-log.md             архитектурные решения и причины
docs/legacy-cleanup-inventory.md legacy/compat/fallback cleanup map
docs/legacy-cleanup-handoff.md   финальное состояние cleanup-линии и старт следующего этапа
docs/card-alias-audit.md         card payload alias evidence/removal readiness
```

## Главные инварианты

Не ломать dashboard payload contract. Backend builder находится в:

```text
anki_study_report/dashboard_payload.py
```

Frontend contract находится в:

```text
web-dashboard/src/types/report.ts
```

Если payload меняется, обновить оба слоя и tests.

Не тащить runtime outputs в git:

```text
e2e-artifacts/
web-dashboard/dist/
web-dashboard/screenshots/
anki_study_report/web_dashboard/
anki_study_report/user_files/
*.ankiaddon
```

Не импортировать Anki entrypoint в чистых тестах, если это требует `aqt`.
Использовать существующий test harness в `tests/conftest.py`.

Если production payload корректен, а тест устарел, править точное ожидание
теста, а не менять рабочий payload ради старого assertion.

## Как подходить к изменениям

Для узких исправлений:

1. Сначала прочитать текущий код и тест, который задает контракт.
2. Проверить фактическую форму данных.
3. Менять минимальный слой.
4. Запустить релевантную проверку.
5. Не форматировать и не откатывать несвязанные файлы.

Для legacy cleanup сначала открыть `docs/legacy-cleanup-inventory.md` и
определить, является ли место compatibility bridge, fallback, transitional
adapter, generated output или настоящим кандидатом на удаление.
Для удаления card payload aliases дополнительно читать
`docs/card-alias-audit.md`.

Для dashboard/frontend:

```powershell
cd web-dashboard
pnpm run test:frontend
pnpm run build:addon
```

Для Python:

```powershell
node scripts/run_python.mjs -m pytest
```

Для полной локальной проверки:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Эта же команда используется cloud-primary workflow
`.github/workflows/ci-fast.yml`. `cd web-dashboard; pnpm run test:all` остаётся
frontend-oriented aggregate, но не отдельным CI pipeline. Local fallback
ручной, и его PASS не заменяет GitHub CI PASS.

Для release artifact:

```powershell
.\build_ankiaddon.ps1
```

Для real Anki Desktop behavior:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

Для финального Cards/APKG/Perf100 release smoke:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker -RequireApkgFixture -Perf100
```

## Текущая архитектурная договоренность

`anki_study_report/__init__.py` - adapter/orchestration layer: Anki UI, hooks,
dialogs, dashboard lifecycle, cache wiring.

Чистая логика должна жить в отдельных модулях:

```text
dashboard_payload.py
report_from_cache.py
stats_cache.py
metrics.py
note_intelligence.py
browser_actions.py
config_service.py
profile_service.py
```

Так ее можно импортировать и тестировать без реального Anki.

## Текущая Navigation / IA

Primary navigation сейчас строго ограничена четырьмя пунктами:

```text
Сегодня → Активность → Колоды → Карточки
```

`#/home` сохраняется и отображается как «Сегодня». Профиль, Настройки,
Инструменты (`#/actions`) и «Поддержать проект» доступны через avatar menu
справа. Support ведёт на `https://boosty.to/ankistudyreport` как статическая
no-referrer ссылка в новой вкладке; `#/support` не существует. Settings Hub
использует `#/settings`, `#/settings/data`, `#/settings/server`,
`#/settings/sources`, `#/settings/logs`; старые `#/integrations` и `#/logs`
redirect-ятся в canonical diagnostics pages. Profile больше не редактирует
dashboard scope. Home использует отдельный current-day `StudyReport.today`, а
historical top-level report сохраняется для других pages. Полный contract:
`docs/settings-hub.md`.

Profile MVP использует отдельный `StudyReport.profile`, всегда построенный из
all-collection cache snapshot до dashboard filters. Editable
`customStudyStartedOn` и `deckOverviewSort` живут в per-profile runtime
`profile.json` и меняются через token-protected `/api/profile`. Полный contract:
`docs/profile-mvp.md`.

`#/calendar` остаётся route, но nav/heading называется «Активность». Canonical
`StudyReport.activityHub` содержит максимум год scoped daily/deck-day rows и
derived feed; Profile остаётся all-collection. Полный contract:
`docs/activity-calendar-v2.md`.

`#/decks` использует additive normalized `StudyReport.deckHub`: current deck
catalog, scoped direct rows, bottom-up subtree metrics, отдельные health /
confidence / descendant issues и typed Browser action по deck ID. Filtered
decks исключены; legacy `decks` сохранён. Полный contract: `docs/decks-v2.md`.

Не возвращать `#/stats`, `#/fsrs`, `#/browse` и не добавлять Search,
Notifications или другие placeholders до соответствующего продуктового этапа.
Stage 1 Navigation / IA завершён. Полный контракт и причины:
`docs/navigation-ia.md`.

## Docker E2E: что важно не перепутать

Installed add-on path внутри контейнера:

```text
/e2e/anki-data/addons21/anki_study_report_e2e
```

Base profile DB:

```text
/e2e/anki-data/prefs21.db
```

E2E artifacts:

```text
e2e-artifacts/runtime/dashboard-ready.json
e2e-artifacts/runtime/addon-e2e-events.jsonl
```

Если Docker E2E падает, сначала смотреть layout/profile/readiness artifacts,
затем `diagnostics/`, `reports/` и `html/`, а не менять production код наугад.
Полный redacted индекс текущего run — `e2e-artifacts/artifact-manifest.json`;
page/navigation/Cards matrices находятся под `screenshots/`.

## Cards preview: текущая release truth

- `table` и `tiles` используют `AnkiCardShadowPreview` / Shadow DOM host
  `data-testid="anki-card-shadow-preview"` и показывают front-only preview.
- `ankiPreview` тоже использует `AnkiCardShadowPreview`, но как answer-only
  host: `data-testid="anki-preview-answer"` плюс
  `data-testid="anki-card-shadow-preview"`,
  `data-shadow-preview-mode="preview"`, `data-preview-side="answer"`.
  Source HTML - `renderedPreview.backHtml`; отдельный front не дублируется.
- Если `backHtml` отсутствует, UI должен показывать диагностический fallback,
  а не молча подставлять отдельный штатный front preview.
- Preview не использует iframe, JS templates не исполняются, sanitizer нельзя
  ослаблять ради визуального совпадения, note CSS остается внутри Shadow DOM
  preview host.
- Целевой surface - локальный desktop/laptop dashboard, не mobile-first ширины.

Tracked APKG fixture:

```text
docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg
```

Fixture содержит 10 notes, 10 cards, 4 note types и 13 media files. Strict APKG
smoke:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture
```

Perf100 smoke использует эту же APKG fixture, клонирует импортированные
cards/notes внутри Docker collection, не создает новую APKG и не включает UI
virtualization. Timings являются diagnostic output, а не release thresholds:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture -Perf100
```

## Перед финальным ответом по задачам

Полезный минимум:

```powershell
git status --short --branch
git diff --check
```

Если были кодовые изменения, добавить релевантные test/build команды из
`docs/test-matrix.md`. Если проверку нельзя запустить, явно написать почему.
