# Передача контекста новому чату/нейронке

Снимок документации: 2026-07-15.

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
11. Если задача про E2E scopes/cache/telemetry - `docs/e2e-performance.md`.
12. Если задача про native Cards/Notes query или inspect -
    `docs/search-query-foundation.md`.
13. Если задача про `#/search`, selection или mutations —
    `docs/search-v1-and-safe-actions.md`.

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
docs/ui-polish-global-controls.md Stage 5.5 theme dock and Activity/Decks presentation polish
docs/search-query-foundation.md  native query/inspect foundation
docs/search-v1-and-safe-actions.md Search route, selection, Browser bridge и undoable mutations
docs/config-reference.md         config/env vars/runtime paths
docs/decision-log.md             архитектурные решения и причины
docs/legacy-cleanup-inventory.md legacy/compat/fallback cleanup map
docs/legacy-cleanup-handoff.md   финальное состояние cleanup-линии и старт следующего этапа
docs/card-alias-audit.md         card payload alias evidence/removal readiness
```

Search Query Foundation остаётся read-only API, но теперь имеет продуктовый
`#/search` surface. Его pagination contract использует `pageCount` для числа bounded result pages и `pageLimit`
для hard-cap предела запроса; пустой результат имеет `page=1`, `pageCount=0`.
`web-dashboard/src/lib/searchApi.ts` runtime-проверяет все обязательные поля
Cards/Notes rows и details, вложенные структуры и response metadata. E2E seed и
APKG import не вызывают deprecated `Collection.save()` в Anki 26.05; отдельный
deck-manager `col.decks.save(deck)` не является этим API и сохраняется.

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
entity_actions.py
entity_action_runtime.py
config_service.py
profile_service.py
activity_service.py
deck_hub.py
statistics_service.py
```

Так ее можно импортировать и тестировать без реального Anki.

## Текущая Navigation / IA

Statistics использует отдельный visual contract поверх неизменного Stage 6
typed API: четыре уровня page identity → query/coverage → insight/KPI →
analytical panels. Chart type выбирается по вопросу; несопоставимые units не
делят simple scale. Shared primitives/palette и полный screenshot contract
описаны в `docs/statistics-visual-design.md`.

Primary navigation сейчас содержит шесть продуктовых пунктов:

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
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

Stage 5.5 монтирует persistent `GlobalUtilityDock` в `AppLayout`: theme toggle
использует существующий `anki-study-report-theme`, а Activity/Decks меняют
только presentation/state. Dock также содержит независимый RU/EN selector с
browser-local `anki-study-report-language`. Все product-owned строки живут в
bundled typed resources; русский — default/fallback, пользовательские и
технические payload values не переводятся. Полный contract:
`docs/localization.md` и `docs/ui-polish-global-controls.md`.

`#/search` использует native Cards/Notes query, bounded inspector, явную
selection до 200 IDs, Browser bridge и allowlisted undoable actions. Read и
mutation разделены между QueryOp и official CollectionOp wrappers; полный
contract — `docs/search-v1-and-safe-actions.md`.

`#/stats` и четыре nested routes используют additive
`StudyReport.statisticsHub`, cache schema v3 и token-protected
`POST /api/statistics/query`. True Retention хранится как first-review
daily/deck-day aggregate; current states/due остаются bounded live snapshot.
Полный contract: `docs/statistics-v1.md`.

Stage 7 добавляет read-only FSRS center в Statistics: `#/stats/fsrs` и
`memory|calibration|steps|simulator`. Lightweight capability находится в
`statisticsHub.fsrs`, heavy операции — strict token-protected
`POST /api/statistics/fsrs/query`; source of truth — native Anki 26.05.
Проверки следуют `docs/verification-run-policy.md`: Fast CI → targeted scope →
один final full gate.

Не возвращать `#/fsrs`, `#/browse` и не добавлять Notifications или другие
placeholders до соответствующего продуктового этапа.
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

APKG является owner-authored, sanitized и owner-authorized regression fixture,
а не generated synthetic collection. Владелец создал/курировал карточки и все
13 media и разрешил публичное использование fixture в repository, tests, Docker
E2E и CI artifacts. Read-only inspection не нашёл противоречащих данных;
publication finding закрыт. Fixture-specific permission не задаёт лицензию для
остального репозитория.

## Cloud Full Docker E2E

Cloud E2E разделяет `mode` и `scope`. Targeted scopes поднимают настоящий Anki
и сохраняют security/core checks, но final gate — `standard/full`. Page capture
использует один Chromium и bounded pool из 3 BrowserContext по умолчанию.
Buildx `type=gha` сохраняет только build layers; profile/token/runtime outputs
не кэшируются. Artifact schema v2 содержит phase, screenshot, resource и
performance reports. Baseline — готовый run `29208090406`, 183 s; старую
реализацию повторно не запускать. Полный contract: `docs/e2e-performance.md`.

Fast CI и real-Anki E2E разделены. `.github/workflows/ci-e2e.yml` после
bootstrap запускается вручную с typed mode/scope/workers/telemetry/restart.
Основной release proof — `standard/full`; strict APKG и Perf100 нужны только
при изменении их paths. Workflow использует `ubuntu-24.04`, read-only
permissions, официальный digest Anki 26.05 и ту же локальную
`run_full_check.ps1 -DockerOnly` orchestration.

Public artifact — только `ci-e2e/`: raw readiness token исключён,
`dashboard-ready.redacted.json` безопасен, manifest paths и text exports
проверяются. `ci-e2e-summary.json` schema v2 содержит exact SHA, mode/scope,
cache/build/performance и runtime result без token/PII. LOCAL PASS не заменяет
exact-SHA GitHub PASS; performance goals и Perf100 timings пока не являются
release thresholds.

## Stage 7.5 delivery truth

Statistics и FSRS — route-level lazy chunks. Их загрузка проходит через
`RouteDeliveryBoundary`; не возвращать их в eager entry ради обхода package
ошибки. Production `web_dashboard/manifest.json` обязателен. Общий
`dashboard_asset_graph.py` проверяет static/dynamic imports, async CSS, path
safety и non-empty files и используется package validator/runtime health.

FSRS остаётся read-only: calibration и simulator manual, presentation verdicts
не меняют backend formulas, sparse samples не превращаются в уверенный вывод.
Canonical closure и bundle baseline/after находятся в
`docs/stage-7-5-fsrs-visual-delivery-report.md`.

## Перед финальным ответом по задачам

Полезный минимум:

```powershell
git status --short --branch
git diff --check
```

Если были кодовые изменения, добавить релевантные test/build команды из
`docs/test-matrix.md`. Если проверку нельзя запустить, явно написать почему.

## Release delivery truth

Каноническая версия находится в `anki_study_report/version.py`, release notes —
в versioned section `CHANGELOG.md`, публичная стабильная AnkiWeb часть — в
`release/ankiweb-description.md`. `release.yml` на PR только валидирует и
строит; production запускается вручную с current `master`.

Exact `.ankiaddon` проходит SHA handoff через standard/full real-Anki E2E,
draft GitHub Release, approved `ankiweb-production`, один Save существующей
AnkiWeb `Branch 1` и публичный download verification. Stable финализирует
GitHub Release после AnkiWeb; prerelease AnkiWeb не трогает. Credentials не
должны появляться в контексте/аргументах/файлах. Подробности и recovery:
`docs/release-automation.md`.
