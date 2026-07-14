# Матрица проверок

Снимок документации: 2026-07-13.

Минимальная проверка - нижняя граница для маленького изменения. Желательная
проверка нужна перед merge/release или если изменение затрагивает несколько
слоев.

| Что изменилось | Минимальная проверка | Желательная проверка | Docker/live Anki нужен? | Почему |
| --- | --- | --- | --- | --- |
| docs-only | `git diff --check` | Проверить ссылки/пути вручную | Нет | Код и артефакты не менялись |
| Python pure logic | `node scripts/run_python.mjs -m pytest` | py_compile конкретных add-on files | Обычно нет | Большая часть pure modules тестируется без Anki |
| Anki hooks/startup | Targeted pytest если есть | Live Anki smoke или Docker E2E | Да | `aqt`, hooks и profile lifecycle не видны unit tests |
| Dashboard payload contract | `node scripts/run_python.mjs -m pytest tests/test_dashboard_payload.py` | `cd web-dashboard; pnpm run test:frontend` | Нет, если нет runtime/rendering | Backend shape должен совпасть с TS/types/normalizers |
| Frontend UI/types | `cd web-dashboard; pnpm run test:frontend` | `pnpm run build:addon` | Нет для чистой UI логики | TypeScript и Vitest ловят type/normalization regressions |
| Cards page/rendering/media | `pnpm run test:frontend` + `node scripts/run_python.mjs -m pytest tests/test_note_intelligence.py` | Docker E2E browser smoke | Да для final | Shadow DOM, native render и media loading зависят от runtime |
| Dashboard server/token/actions | `node scripts/run_python.mjs -m pytest tests/test_dashboard_server.py tests/test_dashboard_actions.py` | Frontend actions tests + local server smoke | Иногда | Нужно проверить token, allowlist и JSON errors |
| Cache/report_from_cache/stats_cache | `node scripts/run_python.mjs -m pytest tests/test_stats_cache.py` | smoke scripts из `scripts/smoke_report_cache_*.py` + full pytest | Нет обычно | Cache не должен менять public dashboard contract |
| Packaging/build scripts | `node scripts/run_python.mjs scripts/package_addon.py --check` | `.\build_ankiaddon.ps1` | Нет | Validator ловит forbidden files, linked assets, css markers |
| Docker E2E/runtime behavior | Targeted local checks перед запуском | `.\scripts\run_full_check.ps1 -CleanDocker` | Да | Проверяет реальный Anki Desktop/import/readiness/browser |
| E2E artifact paths/screenshots | `node scripts/run_python.mjs -m pytest tests/test_docker_smoke_helpers.py` | `.\scripts\run_full_check.ps1 -CleanDocker -RequireApkgFixture` | Да | Проверяет readers/writers, manifest и synthetic/APKG screenshot hierarchy |
| Release artifact | `.\build_ankiaddon.ps1` | Fresh install in local Anki + optional Docker E2E | Да для runtime changes | Archive может быть валиден, но installed/runtime behavior важен |
| `.github/workflows/ci-fast.yml` или Fast CI scripts | `git diff --check` | `.\scripts\run_full_check.ps1 -SkipDocker` | Нет | Cloud CI и local fallback вызывают одну canonical project command |
| `.github/workflows/ci-e2e.yml`, Docker wrapper или public artifact exporter | exporter pytest + `git diff --check` | strict APKG + Perf100 локально и manual exact-SHA cloud runs | Да | Проверяет cross-platform orchestration, real Anki и отсутствие token в public artifact |
| E2E scopes/parallel queue/telemetry/BuildKit layers | `pytest tests/test_e2e_performance.py tests/test_docker_smoke_helpers.py tests/test_ci_e2e_artifacts.py` + syntax/YAML checks | exact-SHA `stats` workers 3/4, затем first+warm `full standard` | Да для cloud benchmark | Проверяет deterministic tasks, bounded cleanup, p50/p90/p95, resource aggregation, cache structure и artifact v2 |
| `config.json` / Settings Hub API | `node scripts/run_python.mjs -m pytest tests/test_config_service.py tests/test_dashboard_server.py` | Frontend settings tests + package check | Нет обычно | Defaults, allowlist, partial update и token contract должны совпадать |
| Profile payload/persistence/UI | `pytest tests/test_profile_service.py tests/test_dashboard_server.py` + `pnpm run test:frontend` | `pnpm run build:addon` + `run_full_check.ps1 -CleanDocker` | Да для final Stage 3 | Проверяет all-collection scope, per-profile atomic storage, dialog/save/reload и light/dark surface |
| Activity/calendar/feed | `pytest tests/test_activity_feed.py` + `pnpm run test:frontend` | `run_full_check.ps1 -CleanDocker` | Да для final Stage 4 | Scope, date bounds, availability, keyboard, derived events/weeks и real screenshots |
| Decks hierarchy/health/actions | `pytest tests/test_deck_hierarchy.py tests/test_dashboard_payload.py tests/test_stats_cache.py tests/test_browser_actions.py tests/test_dashboard_actions.py` + `pnpm run test:frontend` | `run_full_check.ps1 -CleanDocker` | Да для final Stage 5 | Direct/subtree aggregation, filtered exclusion, keyboard disclosure, Browser modes и installed UI |
| App Shell theme / Activity+Decks polish | Targeted AppLayout/Activity/Decks Vitest + `node --check docker/anki-e2e/smoke-browser.mjs` | exact-SHA Fast CI + manual cloud E2E `standard` | Да для final Stage 5.5 | Persistence, route-wide dock, light/dark states и 125% scale proof требуют browser runtime |
| Dashboard localization / global shell | `pnpm run test:frontend` + `node --check docker/anki-e2e/smoke-browser.mjs` | exact-SHA Fast CI, one `standard/stats`, one final `standard/full` | Да для final localization delivery | Locale parity, RU fallback, storage, plural/formatting и representative renders покрываются unit tests; reload/hash/theme independence и four-state screenshots требуют browser runtime |
| Statistics / FSRS (six sections, ten routes) | `pytest tests/test_statistics_service.py tests/test_fsrs_service.py tests/test_dashboard_server.py` + `pnpm run test:frontend` | exact-SHA Fast CI, one `standard/stats`, one final `standard/full` | Да для final Stage 7 | Native configuration/memory/simulator, strict API and screenshots require both layers |
| Lazy routes / split dashboard assets | `pnpm run build:addon` + `pytest tests/test_package_build.py tests/test_dashboard_server.py` | package `--check-only`, exact-SHA `standard/stats`, затем final `standard/full` | Да для packaged nested-route proof | Manifest graph должен включать dynamic JS/async CSS, а runtime не может принимать неполный split build |
| Browser search/query actions | `node scripts/run_python.mjs -m pytest tests/test_browser_actions.py tests/test_dashboard_actions.py` | Cards/Actions frontend tests | Иногда | Search query sanitizer защищает Anki Browser actions |
| Search Query Foundation (read-only Cards/Notes) | `pytest tests/test_search_service.py tests/test_search_runtime.py tests/test_dashboard_server.py` + `pnpm exec vitest run src/lib/searchApi.test.ts` + typecheck | exact-SHA Fast CI и targeted `standard/global`; final `standard/full` только при эскалации planner/matrix | Да для runtime API | QueryOp serialization, native parser, query/inspect token contract и отсутствие mutation требуют real Anki proof |

## Команды-шпаргалка

```powershell
git diff --check
node scripts/run_python.mjs -m pytest
cd web-dashboard
pnpm run test:frontend
pnpm run build:addon
pnpm run test:all
```

```powershell
.\build_ankiaddon.ps1
.\scripts\run_full_check.ps1 -SkipDocker
.\scripts\run_full_check.ps1 -CleanDocker
.\scripts\run_full_check.ps1 -DockerOnly
.\scripts\run_full_check.ps1 -CleanDocker -RequireApkgFixture -Perf100
```

## Когда не запускать Docker E2E

### Statistics visual/chart changes

Targeted frontend contour:

```powershell
cd web-dashboard
pnpm exec vitest run src/pages/StatisticsPage.test.tsx src/components/statistics/statisticsPresentation.test.ts
pnpm run build
```

Проверяются hierarchy, controls, insight/KPI, mixed-unit separation,
zero-origin bars, missing/sparse states, percentage-point delta, semantic
palette, Russian labels, part-to-whole views, deterministic deck selection и
accessible tables. Финальный proof для layout/chart changes — exact-SHA cloud
Fast CI и Full Docker / Anki E2E `standard` с ручным просмотром Statistics
screenshots; успешный cloud full gate локально не дублируется.

Для FSRS visual delivery focused contour дополнительно включает
`FsrsStatisticsPage.test.tsx`, `fsrsPresentation.test.ts` и
`RouteDeliveryBoundary.test.tsx`. Bundle guard является частью `pnpm run build`
и не допускает JS chunks больше 500,000 bytes.

Не запускать Docker E2E для docs-only изменений и маленьких pure helper правок,
если они не касаются startup/rendering/media/server/package layout. Docker E2E
дорогой и нужен там, где unit tests не видят реальный Anki Desktop.

Для Cards preview финальный Docker browser smoke должен покрывать screenshots
`table`, `tiles` и `ankiPreview` в light/dark темах; `table`/`tiles` остаются
front-only через Shadow DOM, а `ankiPreview` проверяет единственный answer-only
preview host из `renderedPreview.backHtml` через `AnkiCardShadowPreview`
(`data-shadow-preview-mode="preview"`, `data-preview-side="answer"`). Perf100
использует tracked APKG fixture, клонирует импортированные cards/notes в Docker
collection до 100 cards, не создает новую APKG и не вводит virtualization;
timings сохраняются только как diagnostics.

Обычный strict APKG browser smoke также фиксирует 40 page screenshots, 2 avatar
menu screenshots, 6 synthetic Cards screenshots и 6 APKG Cards screenshots.
`e2e-artifacts/artifact-manifest.json` должен ссылаться только на существующие
relative paths; canonical add-on log — `diagnostics/anki_study_report.log`.
