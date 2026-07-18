# Матрица проверок

## Stage 6B GHCR cloud cutover

Focused layer: workflow/release/consumer-lock/package-handoff/artifact-observability
pytest, YAML/JSON/PowerShell/Bash/static scans and explicit no-match checks for
cloud BuildKit/GHA tokens. Required cloud order is exact-SHA Fast CI → one
`standard/settings` GHCR run → one `standard/full` GHCR run → isolated
release-artifact rehearsal. Manual E2E requires the Fast CI run ID; release uses
the exact release artifact. Local Docker source-build remains a fallback and is
not evidence of cloud PASS.

## Stage 9.3–9.5 signals/notifications

Focused layer: notification store/detectors/integration/dashboard server
pytest, Notification Bell/Center/Settings/Toasts/API Vitest, bundle build and
`node --check docker/anki-e2e/smoke-browser.mjs`. Targeted real-Anki scope —
`standard/notifications` с restart: lifecycle, bell/panel, all/unread/active,
resolved pagination, settings, warning/critical toast, RU/EN, light/dark,
read-resolution independence и persistence. Из-за App Shell, local API и
profile lifecycle требуется один финальный `standard/full`.

Снимок документации: 2026-07-16.

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
| Consent-gated telemetry client | `pytest tests/test_telemetry_contract.py tests/test_telemetry_store.py tests/test_telemetry_client.py tests/test_dashboard_server.py` + telemetry/privacy Vitest | `settings` real-Anki с loopback fake и restart | Да при изменении queue/network/deletion | Проверяет purpose isolation, strict payload, bounded queue/batch, retry, persistence и confirmed deletion без production traffic |
| Cache/report_from_cache/stats_cache | `node scripts/run_python.mjs -m pytest tests/test_stats_cache.py` | smoke scripts из `scripts/smoke_report_cache_*.py` + full pytest | Нет обычно | Cache не должен менять public dashboard contract |
| Packaging/build scripts | `node scripts/run_python.mjs scripts/package_addon.py --check` | `.\build_ankiaddon.ps1` | Нет | Validator ловит forbidden files, linked assets, css markers |
| Docker E2E/runtime behavior | Targeted local checks перед запуском | `.\scripts\run_full_check.ps1 -CleanDocker` | Да | Проверяет реальный Anki Desktop/import/readiness/browser |
| E2E artifact paths/screenshots | `node scripts/run_python.mjs -m pytest tests/test_docker_smoke_helpers.py` | `.\scripts\run_full_check.ps1 -CleanDocker -RequireApkgFixture` | Да | Проверяет readers/writers, manifest и synthetic/APKG screenshot hierarchy |
| Release artifact | `.\build_ankiaddon.ps1` | Fresh install in local Anki + optional Docker E2E | Да для runtime changes | Archive может быть валиден, но installed/runtime behavior важен |
| `.github/workflows/ci-fast.yml`, `run_full_check.ps1` или Fast CI timing scripts | `pytest tests/test_ci_fast_timing.py tests/test_ci_fast_workflow.py tests/test_full_check_timing.py tests/test_ci_package_metadata.py` + `git diff --check` | `.\scripts\run_full_check.ps1 -SkipDocker`; затем ровно один manual Fast CI dispatch на exact branch для runtime baseline | Нет | Проверяет schema/failure behavior, отдельные canonical phases, неизменные runner/cache/checkout/package contracts и diagnostics timing inventory; Jobs API анализ выполняется после run |
| `.github/workflows/ci-e2e.yml`, Docker wrapper, Fast-package handoff или public artifact exporter | handoff/workflow/exporter pytest + `git diff --check` + GHCR-only no-match scan | exact-SHA Fast CI, targeted `standard/settings`, затем risk-required `standard/full`; release-path change также требует isolated release-artifact rehearsal | Да для runtime handoff | Проверяет GHCR exact digest, отсутствие cloud BuildKit/GHA fallback, same-repo run/artifact identity, exact checkout, inner/transport hashes, prebuilt install, redaction и отсутствие token в container/public artifact |
| E2E scopes/parallel queue/telemetry/historical BuildKit evidence | `pytest tests/test_e2e_performance.py tests/test_docker_smoke_helpers.py tests/test_ci_e2e_artifacts.py` + syntax/YAML checks | только explicit performance work: exact-SHA `stats` workers 3/4 и обоснованные repeats | Да только для отдельного cloud benchmark | Проверяет deterministic tasks, bounded cleanup, p50/p90/p95, resource aggregation, historical schema parsing и artifact v2; обычный product gate не пишет BuildKit cache |
| `config.json` / Settings Hub API | `node scripts/run_python.mjs -m pytest tests/test_config_service.py tests/test_dashboard_server.py` | Frontend settings tests + package check | Нет обычно | Defaults, allowlist, partial update и token contract должны совпадать |
| Profile payload/persistence/UI | `pytest tests/test_profile_service.py tests/test_dashboard_server.py` + `pnpm run test:frontend` | `pnpm run build:addon` + `run_full_check.ps1 -CleanDocker` | Да для final Stage 3 | Проверяет all-collection scope, per-profile atomic storage, dialog/save/reload и light/dark surface |
| Activity/calendar/feed | `pytest tests/test_activity_feed.py` + `pnpm run test:frontend` | `run_full_check.ps1 -CleanDocker` | Да для final Stage 4 | Scope, date bounds, availability, keyboard, derived events/weeks и real screenshots |
| Decks hierarchy/health/actions | `pytest tests/test_deck_hierarchy.py tests/test_dashboard_payload.py tests/test_stats_cache.py tests/test_browser_actions.py tests/test_dashboard_actions.py` + `pnpm run test:frontend` | `run_full_check.ps1 -CleanDocker` | Да для final Stage 5 | Direct/subtree aggregation, filtered exclusion, keyboard disclosure, Browser modes и installed UI |
| App Shell theme / Activity+Decks polish | Targeted AppLayout/Activity/Decks Vitest + `node --check docker/anki-e2e/smoke-browser.mjs` | exact-SHA Fast CI + manual cloud E2E `standard` | Да для final Stage 5.5 | Persistence, route-wide dock, light/dark states и 125% scale proof требуют browser runtime |
| Dashboard localization / global shell | `pnpm run test:frontend` + `node --check docker/anki-e2e/smoke-browser.mjs` | exact-SHA Fast CI, one `standard/stats`, one final `standard/full` | Да для final localization delivery | Locale parity, RU fallback, storage, plural/formatting и representative renders покрываются unit tests; reload/hash/theme independence и four-state screenshots требуют browser runtime |
| Statistics / FSRS (six sections, ten routes) | `pytest tests/test_statistics_service.py tests/test_fsrs_service.py tests/test_dashboard_server.py` + `pnpm run test:frontend` | exact-SHA Fast CI, one `standard/stats`, one final `standard/full` | Да для final Stage 7 | Native configuration/memory/simulator, strict API and screenshots require both layers |
| Lazy routes / split dashboard assets | `pnpm run build:addon` + `pytest tests/test_package_build.py tests/test_dashboard_server.py` | package `--check-only`, exact-SHA `standard/stats`, затем final `standard/full` | Да для packaged nested-route proof | Manifest graph должен включать dynamic JS/async CSS, а runtime не может принимать неполный split build |
| Browser search/query actions | `node scripts/run_python.mjs -m pytest tests/test_browser_actions.py tests/test_dashboard_actions.py` | Cards/Actions frontend tests | Иногда | Search query sanitizer защищает Anki Browser actions |
| Search v1 + Safe Actions | `pytest tests/test_search_service.py tests/test_search_runtime.py tests/test_entity_actions.py tests/test_entity_action_runtime.py tests/test_dashboard_server.py tests/test_dashboard_actions.py` + Search/API Vitest + typecheck/build | exact-SHA Fast CI, targeted `standard/global`; final `standard/full` из-за shared server/E2E/package diff | Да | QueryOp latest-wins reads, strict action endpoints, one native undoable batch, filtered-deck restrictions, Browser bridge и deterministic restore |
| Inspection Profiles / triage v2 + Settings UI | profile store/service/runtime/triage/dashboard pytest + JSON Schema parity + workspace/router/i18n/import/profile/triage Vitest + typecheck/build/bundle | exact-SHA Fast CI, targeted `standard/cards` with `verify_restart=true` | Да | Live structures/fingerprint/persistence, Japanese/Programming isolation, validate-v2 sample, lifecycle editor, dirty/preview/needs-review screenshots and restart survival require real Anki |

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

Fast CI instrumentation использует optional `-TimingOutput`; без него canonical
локальный contour не создаёт timing files. Stage 5A разрешает один manual Fast CI
run после local PASS. Он является observational baseline, не before/after pair и
не основанием для объявления ускорения.

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

Для Cards workspace финальный Docker browser smoke должен покрывать canonical
queue/Inspector в light/dark, expanded preview, 1024 px и APKG fixture. Он
проверяет один active-item Shadow DOM host, cached expanded modal, keyboard row
activation, отсутствие legacy modes/checkbox/risk score и exact-ID open. Perf100
использует tracked APKG fixture, клонирует импортированные cards/notes в Docker
collection до 100 cards, не создает новую APKG и не вводит virtualization;
timings сохраняются только как diagnostics.

Обычный strict APKG browser smoke также фиксирует page/avatar screenshots и
пять canonical Cards workspace screenshots.
`e2e-artifacts/artifact-manifest.json` должен ссылаться только на существующие
relative paths; canonical add-on log — `diagnostics/anki_study_report.log`.

## Release delivery

Release/version/package/publisher/workflow изменения требуют focused tests
`test_release_automation.py`, `test_ankiweb_publisher.py`,
`test_release_workflow.py`, `test_package_build.py` и Node test
`tests/publish_ankiweb.test.mjs`, затем canonical `run_full_check.ps1
-SkipDocker`. Финальный production gate всегда `standard/full` на exact
release artifact SHA. `strict-apkg` и `perf100` не добавляются, если их
Cards/APKG/performance contracts не менялись.

PR release workflow проверяет release contract без secrets/mutations; heavy
build остаётся manual-dispatch-only и получает `skipped` на PR. Live AnkiWeb
`--dry-run` допустим только с env credentials и проверяет форму без выбора файла
и Save. Publish proof требует совпадения build/E2E/GitHub/AnkiWeb SHA-256.

## Product notices и consent

Нужны `test_product_notices.py`, `test_changelog.py`, dashboard/package/release
tests, coordinator/API Vitest и RU/EN parity. Planner выбирает targeted
`standard/settings`; shared App Shell, dashboard server, E2E или package/release
diff дополнительно требует final `standard/full`. Real-Anki smoke проверяет
consent-first order, no preselection, decline persistence, What’s New
no-repeat/manual reopen и Privacy route.

Stage 9.0.1 добавляет persisted enrollment retry/manual check, active-profile
timer, language-menu tooltip и service abuse hardening. Локально нужны focused
Python/Vitest, telemetry service `pnpm check`, затем только
`.\scripts\run_full_check.ps1 -SkipDocker`. После exact-SHA Fast CI выполняется
один `standard/settings` с exact package handoff; shared dashboard server и E2E
smoke в actual diff требуют один final `standard/full`. Локальный Docker,
повтор targeted run, strict APKG, Perf100 и release не запускаются.
