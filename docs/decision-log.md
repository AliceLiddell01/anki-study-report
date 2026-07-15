# Decision log

## 2026-07-13 — FSRS analytics and verification gates

- FSRS lives only inside Statistics; `#/fsrs` remains invalid.
- Stage 7 is read-only: no scheduler, parameter, target, steps or history writes;
  native simulator has no Apply action.
- Native Anki 26.05 memory/config/simulator is source of truth. FSRS Helper
  26.06.12 is MIT reference, not dependency or vendored code.
- Compatible groups include preset, parameter fingerprint and scheduler
  settings; per-deck retention overrides remain distinct.
- Calibration/simulation require one group. Deck-selected Steps expands to the
  same preset. Current memory distributions are snapshots.
- Helper mutations are deferred to native Anki or future Scheduling Pack / DLC.
- Verification is Fast CI → targeted → one final full. Same-SHA success is not
  repeated; warm-cache/worker benchmarks are performance-work only.
- The deterministic planner is advisory and never auto-runs E2E.

Снимок документации: 2026-07-13.

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

## ADR-010: Учебная primary navigation отдельно от профиля и диагностики

### Статус

Accepted

### Контекст

Один topbar смешивал основные учебные разделы с Profile, actions, cache,
server, integrations и logs. Технические страницы были заметны, но размывали
продуктовую иерархию; простое удаление их из nav также ломало route registry.

### Решение

Оставить в primary navigation только `Сегодня`, `Активность` (canonical
`#/calendar` после ADR-013), `Колоды` и
`Карточки`. Вынести Profile, Settings и Tools в доступный avatar dropdown.
Сохранить технические routes и связать их минимальным `SettingsLayout`:
Данные, Система → Сервер, Диагностика → Источники данных/Логи. Держать полный
registry routes отдельно от списка primary navigation.

Utility block также содержит «Поддержать проект»: статическую HTTPS-ссылку на
Boosty `https://boosty.to/ankistudyreport`. Она открывается в новой вкладке с
`noopener noreferrer` и `no-referrer`, не использует backend action и не
создаёт `#/support`. Stage 1 Navigation / IA завершён.

### Последствия

App shell яснее отделяет учебные задачи от глобальных и технических функций,
но route tests должны отдельно проверять и видимую IA, и доступность скрытых
routes. Dropdown становится keyboard/focus contract, а внешний support link не
передаёт token-bearing dashboard URL как referrer. Новые Stats, FSRS, Search и
Notifications появляются только с реальными workflows, не placeholders.

### Где смотреть

`docs/navigation-ia.md`, `web-dashboard/src/app/router.tsx`,
`web-dashboard/src/layout/TopNav.tsx`,
`web-dashboard/src/layout/SettingsLayout.tsx`.

## ADR-012: Profile как per-Anki-profile all-collection lifetime view

### Статус

Accepted

### Контекст

После Settings Hub `#/profile` оставался transitional экраном и зависел от
dashboard metadata. Add-ons общие между Anki profiles, но collection и runtime
identity принадлежат конкретному profile. Profile metrics не должны меняться
вместе с dashboard deck scope.

### Решение

Строить typed `StudyReport.profile` из исходного all-collection stats-cache
snapshot до фильтров. Хранить только `customStudyStartedOn` и
`deckOverviewSort` в атомарном `<profile>/addon_data/<addon_id>/profile.json`.
Изменять их через отдельный token-protected allowlisted `/api/profile`.
Override даты является presentation metadata и не изменяет totals/activity.

### Последствия

Profile не требует нового collection scan и остаётся независимым от Today,
Calendar, Decks и Cards contracts. Shared add-on config/localStorage не может
быть authoritative profile storage. Future avatar/banner потребуют отдельных
validated local files и token-protected serving, но не входят в Stage 3.

### Где смотреть

`docs/profile-mvp.md`, `anki_study_report/profile_service.py`,
`anki_study_report/__init__.py`, `web-dashboard/src/pages/ProfilePage.tsx`.

## ADR-011: Typed Settings Hub и отдельная семантика Today

### Статус

Accepted

### Контекст

Dashboard scope редактировался в Profile, cache/server/logs жили на отдельных
технических routes, а `#/home` зависел от общего dashboard period и мог
показывать исторические данные под названием «Сегодня».

### Решение

Собрать canonical Settings Hub с постоянным sidebar и typed allowlisted
`/api/dashboard/settings`. Anki config остаётся source of truth, unknown/internal
keys сохраняются. `dashboard_display.period` deprecated. Для Home публикуется
отдельный `StudyReport.today`, а исторический top-level report остаётся у
Calendar/Decks/Cards. Profile становится read-only transitional page.

### Последствия

Frontend forms получают единый dirty/save/cancel contract; server/cache/log
actions остаются отдельными. Payload contract дополняется optional `today`
slice. Compatibility aliases `#/integrations` и `#/logs` redirect-ятся в
canonical settings routes.

### Где смотреть

`docs/settings-hub.md`, `anki_study_report/config_service.py`,
`anki_study_report/dashboard_payload.py`, `web-dashboard/src/lib/settingsApi.ts`,
`web-dashboard/src/layout/SettingsLayout.tsx`.

## ADR-013: Activity использует derived scoped aggregates и сохраняет `#/calendar`

### Статус

Accepted

### Контекст

Старый Calendar смешивал historical days с forecast и строил detail только из
общего `activity.days`. Нужна единая история ритма без второго route,
persistent event store или переключения на Profile all-collection semantics.

### Решение

Сохранить `#/calendar`, переименовать nav/heading в «Активность» и публиковать
additive typed `StudyReport.activityHub`. Backend строит максимум один год из
scoped stats-cache daily/deck-day aggregates; milestones/records учитывают
pre-window history. Daily/weekly feed является deterministic derived model.

### Последствия

Frontend получает один bounded source без raw revlog/N+1, а Profile и Today не
меняют scope. Availability становится explicit `active/inactive/unavailable`;
weekly comparison требует complete coverage и thresholds. Старые payload keys
сохраняются для Home/backward compatibility.

### Где смотреть

`docs/activity-calendar-v2.md`, `anki_study_report/activity_service.py`,
`web-dashboard/src/lib/activityHub.ts`,
`web-dashboard/src/pages/CalendarPage.tsx`.

## ADR-014: Decks v2 использует subtree metrics с отдельными direct metrics и descendant issues

### Статус

Accepted

### Контекст

Плоский `decks` не различал parent/child, direct/subtree и aggregate health от
локальной проблемы descendant. Filtered decks могли загрязнять current-deck
cache association.

### Решение

Добавить normalized scoped `deckHub` из current normal-deck catalog и
direct-only rows. Считать subtree bottom-up, health по subtree, confidence и
descendant issue count отдельно. Сохранить legacy `decks`. Использовать home
deck при `odid > 0`, исключить filtered decks и открывать Browser только typed
action по deck ID/mode с backend query builder.

### Последствия

Cache schema повышена до v2 и старый cache автоматически перестраивается.
Parent не наследует worst-child status, UI сортирует только siblings и хранит
expansion локально. Payload растёт линейно по числу колод без recursive copies.

### Где смотреть

`docs/decks-v2.md`, `anki_study_report/deck_hub.py`,
`web-dashboard/src/lib/deckTree.ts`, `web-dashboard/src/pages/DecksPage.tsx`.

## ADR-015: Cloud-primary Fast CI с ручным local fallback

### Статус

Accepted

### Контекст

Локальные pytest/Vitest/build/package проверки существовали, но старый
workflow повторял их отдельными YAML steps, не использовал Windows contract и
не оставлял компактный machine-readable результат. Полный Docker/Anki E2E пока
слишком тяжёл для первого приватного hosted-runner контура.

### Решение

Использовать один read-only GitHub-hosted Windows job как primary независимую
Fast CI проверку опубликованного commit. И cloud workflow, и ручной fallback
вызывают `.\scripts\run_full_check.ps1 -SkipDocker`; YAML отвечает только за
окружение, exact runtime versions, diagnostics summary и upload artifacts.
Docker/Anki E2E оставить отдельным будущим этапом.

### Последствия

Cloud и local результаты воспроизводимы через одну project test logic.
`LOCAL FALLBACK PASS != GitHub CI PASS`: локальный успех допустим как
диагностика или fallback при инфраструктурной недоступности, но не перекрывает
test/build/package failure GitHub Actions. CI artifacts являются ignored
runtime outputs и non-release builds.

### Где смотреть

`docs/ci-cd.md`, `.github/workflows/ci-fast.yml`,
`scripts/run_full_check.ps1`, `scripts/write_ci_fast_summary.ps1`.

## ADR-016: Public visibility проходит отдельный readiness gate без лицензии

### Статус

Accepted

### Контекст

Владелец выбрал будущую публичную видимость репозитория, но не выбирал
лицензию для свободного распространения. Git history, Actions outputs и tracked
fixtures после публикации становятся доступны внешним читателям.

### Решение

До смены visibility проверять все reachable refs/history, secrets/PII,
fixtures/media, существующие Actions runs и будущий CI artifact contract.
Unresolved secret, personal-data или media finding блокирует публикацию.
LICENSE, SPDX identifier и декларацию открытой лицензии не добавлять без
отдельного решения владельца.

### Последствия

Первичный audit 2026-07-11 остановил публикацию до owner review. Владелец затем
подтвердил, что лично создал и курировал cards/templates/deck structure и все 13
media, и разрешил публичное распространение конкретной fixture в repository,
tests и CI artifacts. Read-only inspection не нашёл противоречащих данных;
finding закрыт без synthetic replacement и history rewrite.

### Где смотреть

`docs/public-repository-readiness.md`, `docs/fixtures-and-test-data.md`,
`docs/security-and-safety.md`, `docs/ci-cd.md`.

## ADR-017: Owner-authored APKG сохраняется как regression fixture

### Статус

Accepted

### Контекст

Tracked APKG содержит реальные полезные rendering/media regression cases,
созданные и многократно переработанные владельцем с AI assistance. Generated
Docker collection и tracked APKG имеют разное происхождение.

### Решение

Сохранить APKG и её 13 owner-created media на основании прямого owner
provenance и разрешения на публичное использование в repository, tests, Docker
E2E и CI artifacts. Документация должна называть её owner-authored regression
fixture, а данные `seed-collection.py` — generated synthetic collection.

### Последствия

Synthetic replacement и history rewrite не нужны. Узкое разрешение для fixture
не является общей лицензией репозитория; LICENSE по-прежнему отсутствует.

### Где смотреть

`docker/anki-e2e/fixtures/README.md`, `docs/fixtures-and-test-data.md`,
`docs/public-repository-readiness.md`.

## ADR-018: Full Docker E2E остаётся manual cloud workflow с redacted artifacts

### Статус

Accepted

### Контекст

Fast CI не запускает real Anki Desktop. Существующая Docker E2E orchestration
уже едина для Windows/Docker Desktop и container runtime, но raw readiness
artifact содержит dashboard token, а hosted runner требует cross-platform
PowerShell и обязательной проверки Anki archive digest.

### Решение

Добавить manual-only `Full Docker / Anki E2E` на standard `ubuntu-24.04` с typed
режимами `standard`, `strict-apkg`, `perf100`. Workflow вызывает только
существующие `run_full_check.ps1 -DockerOnly` modes, требует официальный SHA-256
Anki 26.05 и публикует отдельный redacted `ci-e2e/` artifact schema v1. Для
первого proof разрешён временный exact-branch push trigger, удаляемый до merge.

### Последствия

Fast и Full E2E остаются независимыми; Full E2E не становится обязательным на
каждый push/PR. Raw token не публикуется, failure diagnostics сохраняются, но
исходный exit code не маскируется. Perf100 остаётся diagnostic smoke. Schedule,
path filters, CI consumer и release automation отложены.

### Где смотреть

`.github/workflows/ci-e2e.yml`, `scripts/prepare_ci_e2e_artifacts.py`,
`docs/ci-cd.md`, `docs/docker-e2e.md`.

## ADR-019: Global theme control живёт в persistent App Shell utility dock

### Статус

Accepted

### Контекст

Theme storage и ранняя initialization существовали, но после упрощения
navigation у пользователя не осталось постоянного control. Activity и Decks
также накопили presentation density issues, не требующие новых данных.

### Решение

Монтировать один `GlobalUtilityDock` в `AppLayout` вне route content и
переиспользовать существующий `anki-study-report-theme` contract. Future
language control являлся extension point и на этом этапе не рендерился; его
последующая реализация описана в ADR-024. Activity и Decks
polish меняет только presentation/state и сохраняет Stage 4/5 data semantics.

### Последствия

Theme toggle доступен на каждом route, переживает reload/navigation и не
требует backend. App Shell резервирует safe inset; modal/popover/toast остаются
выше dock. Visual E2E проверяет light/dark и 125% scale, а payload/API/cache
schemas не меняются.

### Где смотреть

`docs/ui-polish-global-controls.md`,
`web-dashboard/src/layout/GlobalUtilityDock.tsx`,
`web-dashboard/src/pages/CalendarPage.tsx`,
`web-dashboard/src/pages/DecksPage.tsx`.

## ADR-020: Statistics v1 использует bounded hub, typed query и честные historical boundaries

### Статус

Accepted

### Контекст

Периодическая аналитика требует пяти пользовательских sections, scope/period
comparisons, True Retention и current due/states, но frontend не должен
получать collection/raw revlog или создавать generic analytics RPC.

### Решение

Вернуть Statistics как first-class primary route с Overview, Quality, Load,
Progress и Deck Comparison. Публиковать additive bounded
`statisticsHub.initialResult` и narrow token-protected typed query endpoint.
Cache schema v3 хранит ratings, introduced, answer-time availability и
first-review-per-card/local-day young/mature retention aggregates; raw rows не
хранятся в public contract. Current state/due — отдельный bounded snapshot и не
выдаётся за historical reconstruction. Backend insights используют semantic
codes. Search Stats Extended и More Overview Stats остаются GPL references, не
runtime dependencies; FSRS/Advanced классифицированы, но отложены. Expensive
Time Machine/provider metrics требуют snapshots/lazy/provider architecture.

Cloud CI остаётся primary: успешные exact-SHA Fast CI/E2E не дублируются
локально. Commit subjects описывают фактический результат и не формулируются
как команды.

### Последствия

All-time агрегируется по месяцам, series/deck/due/payload bounded. Ordinary
success и True Retention имеют разные definitions. Parent/descendant rows не
double-count-ятся. Current state charts не обещают исторической динамики.
Schema v2 перестраивается как disposable cache.

### Где смотреть

`docs/statistics-v1.md`, `docs/statistics-metric-definitions.md`,
`docs/statistics-reference-inventory.md`,
`anki_study_report/statistics_service.py`,
`web-dashboard/src/pages/StatisticsPage.tsx`.

## ADR-021: Statistics использует purpose-driven visual и chart system

### Статус

Принято.

### Контекст

Stage 6 подтвердил metric/API/security architecture, но flat composition и
универсальные grouped bars смешивали count, seconds и percentages, а sparse
fixture выглядел как незаполненный scaffold.

### Решение

- Statistics использует отдельную четырёхуровневую visual hierarchy вместо
  flat page-level charts.
- Chart type выбирается по аналитической задаче; mixed units никогда не
  используют одну simple scale.
- Light/dark semantic palette централизована, previous-period comparison имеет
  dashed text cue, а missing/sparse values не интерполируются.
- Каждый chart имеет textual summary и structured table alternative.
- Developer terminology и формулы вынесены из primary UI.
- Deck comparison получает deterministic useful default selection.
- Stage 7 FSRS обязан переиспользовать этот panel/chart contract.

### Последствия

Backend metric formulas, query semantics, cache schema и payload size не
изменились. Recharts переиспользован как existing dependency. Frontend tests и
cloud standard E2E фиксируют semantics, accessibility, light/dark/state/125%
screenshots и default deck view.

### Где смотреть

- `docs/statistics-visual-design.md`
- `web-dashboard/src/pages/StatisticsPage.tsx`
- `web-dashboard/src/components/statistics/`
- `docker/anki-e2e/smoke-browser.mjs`

## ADR-022: E2E mode и scope независимы, а read-only capture использует bounded pool

### Статус

Принято.

### Контекст

Stage 6.5 full standard run `29208090406` на SHA `cd68c2c` дал canonical
baseline 183 s. Повтор старого checkout не нужен. Основное время тратилось на
повторную Docker/frontend работу и serial screenshot matrix, но final real-Anki
coverage, restart, Cards и security contracts уменьшать нельзя.

### Решение

- `mode` и `scope` являются независимыми понятиями; targeted real-Anki — только
  development contour, а `standard/full` — final gate.
- Read-only page captures выполняются одним Chromium и bounded BrowserContext
  pool; state mutation, Cards/APKG и lifecycle остаются serial.
- Default 3 workers выбирается измерением `stats` 3 vs 4, а не предположением.
- Buildx использует `docker` driver + containerd image store и `type=gha`,
  чтобы не экспортировать/импортировать весь image через отдельный builder;
  Anki install отделён от volatile smoke scripts,
  pnpm store строится из lockfile и runtime install выполняется offline.
- Build cache никогда не содержит profile, collection, token или artifacts.
- Phase/screenshot/resource telemetry и performance summary входят в artifact
  contract; цели сначала report-only, без flaky hard cutoff.
- Exact-SHA cloud gate не дублируется локально; один повтор full exact SHA
  разрешён для warm-cache validation.

### Последствия

Targeted feedback становится дешевле, full screenshot/restart parity
сохраняется. Worker errors, resource pressure, cache behavior и upload cost
измеримы. Missing metrics представлены `null` с причиной. Sharding отложен до
роста suite примерно до 5–10 минут.

Stage 6.6 measurement выбрал 3 workers: четвёртый context дал только 0.7%
capture-wall выигрыша при меньшей efficiency и большем p95 CPU. First/warm
full сохранили screenshot/restart/Cards parity, но warm canonical 190 s не
улучшил baseline 183 s из-за GHA image-transfer variance. Финальный exact-SHA
cache hit дал 162 s (−11.5%, 1.13×), сохранив 62 screenshots и нулевые browser
errors. Цель остаётся report-only; следующая оптимизация может работать с
transfer/image size, но не с coverage.

### Где смотреть

`docs/e2e-performance.md`, `.github/workflows/ci-e2e.yml`,
`docker/anki-e2e/e2e-contract.mjs`, `docker/anki-e2e/e2e-telemetry.py`,
`docker/anki-e2e/smoke-browser.mjs`.

## ADR-023: FSRS routes загружаются лениво и проверяются как полный asset graph

### Статус

Принято.

### Контекст

FSRS имел правильную backend semantics, но flat presentation и monolithic
878 kB entry мешали пользовательскому чтению и delivery safety. Проверка только
ссылок из `index.html` не видела lazy chunks и их CSS.

### Решение

- Пять FSRS routes используют purpose-driven read-only visual hierarchy без
  изменения backend formulas и typed query contract.
- Statistics и FSRS являются `React.lazy` boundaries с общим Suspense и
  visible chunk-error recovery.
- Deliberate vendor boundaries разделяют React, icons и chart graph; каждый JS
  chunk ограничен 500,000 bytes автоматическим guard.
- Vite manifest является graph source для packaging и runtime health; reachable
  static/dynamic dependencies обязательны, stale и unsafe assets запрещены.

### Последствия

Entry уменьшился до 235 kB, warning исчез, а total JS немного вырос из-за
chunk boundaries. Archive/runtime теперь отказываются принимать неполный lazy
build. Heavy FSRS calculations и simulator остаются manual/read-only.

### Где смотреть

`docs/stage-7-5-fsrs-visual-delivery-report.md`,
`web-dashboard/src/app/router.tsx`, `web-dashboard/vite.config.ts`,
`anki_study_report/dashboard_asset_graph.py`, `scripts/package_addon.py`.

## ADR-024: Dashboard localization использует bundled typed RU/EN resources

### Статус

Принято.

### Контекст

Dashboard имел русский product UI и пустой extension slot для языка. Частичная
подмена строк создала бы смешанный интерфейс, а runtime translation backend
нарушил бы локальную offline-модель add-on.

### Решение

- `i18next` и `react-i18next` инициализируются синхронно до первого React render.
- Русский является default/fallback; RU/EN resources целиком входят в bundle и
  имеют одинаковую типизированную структуру namespaces.
- `GlobalUtilityDock` владеет явным selector, preference хранится под
  `anki-study-report-language` и не зависит от theme.
- Product-owned UI-copy переводится, payload/user/technical data сохраняется
  дословно. Новый UI-copy допускается только через locale resources.
- Locale-aware formatters и i18next plural rules используются вместо ручной
  склейки единиц и окончаний.

### Последствия

Весь текущий product UI переключается без reload, `html lang` и title следуют
выбору, а parity/unit/browser tests защищают обе локали. Первая версия не
определяет язык браузера, не синхронизирует preference через Anki и поддерживает
только LTR `ru|en`.

### Где смотреть

`docs/localization.md`, `web-dashboard/src/i18n/`,
`web-dashboard/src/layout/GlobalUtilityDock.tsx`,
`docker/anki-e2e/smoke-browser.mjs`.

## ADR-025: Search foundation использует native grammar и bounded read models

### Статус

Принято.

### Контекст

Search v1 нужны Cards/Notes query и compact inspect, но прямой доступ frontend
к collection, универсальный RPC/SQL и rich preview расширили бы security scope.
`find_cards()`/`find_notes()`
возвращают весь список matching IDs, а не paged cursor.

### Решение

- Native Anki query остаётся source of truth; structured deck/note type/tag/
  state/flag filters собираются через supported search nodes.
- Read выполняется сериализованным `QueryOp` с finite timeout. HTTP server
  остаётся на `127.0.0.1`, token-protected и не логирует raw query.
- Результат ограничен 2000 deterministic IDs, page sizes `25|50|100`; objects
  загружаются только для страницы, IDs отдаются decimal strings.
- Card/Note row/details разделены и содержат bounded safe plain text без
  template rendering, media или mutation.
- TypeScript client/types являются foundation для отдельного `#/search`;
  page/table/inspector/selection не меняют read API contract.

### Последствия

Shipping UI строится на стабильном typed contract. Offset pages не
являются collection snapshot, а широкий native search всё ещё вычисляет все
matching IDs перед cap; эти ограничения задокументированы и проверяются на
real Anki в `standard/global` и final `standard/full`.

### Где смотреть

`docs/search-query-foundation.md`, `anki_study_report/search_service.py`,
`anki_study_report/search_runtime.py`, `web-dashboard/src/lib/searchApi.ts`,
`docker/anki-e2e/smoke-browser.mjs`.

## ADR-027: Safe Actions используют explicit desired state и native batch undo

### Статус

Принято.

### Контекст

Search selection требует ограниченных изменений Cards/Notes, но generic RPC,
toggle semantics, per-ID operations и partial stale batches сделали бы
поведение непредсказуемым. `set_card_deck()` в Anki 26.05 извлекает card из
filtered deck и очищает FSRS data, поэтому filtered source нельзя трактовать
как обычный move без явной product semantics.

### Решение

- Card и note endpoints разделены и принимают только hard-coded action union.
- Полный bounded request валидируется и все entities разрешаются до mutation.
- Изменяющая пачка запускает один official Anki operation wrapper и один native
  undo step; no-op возвращает отдельный code без ложного undo.
- Bury/unbury не расширяются до siblings/notes. Move проверяет normal
  destination server-side и отклоняет filtered destination и `odid > 0` source.
- Frontend локализует stable result codes, сериализует mutation и после успеха
  повторяет query/inspect с page correction и selection reconciliation.

### Последствия

Surface остаётся ограниченным suspend/flag/tags/bury/move workflow. Delete,
reschedule, fields, note type и arbitrary deck/tag operations отложены.
`standard/global` доказывает cycles и fixture restore, а public evidence не
содержит token, raw query, tag content или ID lists.

### Где смотреть

`docs/search-v1-and-safe-actions.md`, `anki_study_report/entity_actions.py`,
`anki_study_report/entity_action_runtime.py`,
`web-dashboard/src/hooks/useSearchWorkspace.ts`,
`docker/anki-e2e/smoke-browser.mjs`.

## ADR-026: Release delivery использует exact-artifact gates и AnkiWeb UI adapter

### Статус

Принято.

### Контекст

Package checks и real-Anki E2E существовали, но версия, GitHub Release и
обновление owner-only AnkiWeb form не были связаны единым проверяемым artifact.
Прямая API-интеграция AnkiWeb недоступна, а автоматическая публикация после
merge дала бы production secrets PR-коду или убрала явное решение владельца.

### Решение

- Версия, changelog, manifest release date и public metadata валидируются до build.
- Production запускается только manual dispatch с exact current `master` и
  защищается одной concurrency group.
- Один archive и SHA-256 проходят reusable standard/full Anki E2E, GitHub draft,
  AnkiWeb publish и public download verification.
- GitHub write jobs отделены от Playwright job; credentials доступны только
  через reviewed Environment `ankiweb-production`.
- UI adapter fail-closed проверяет owner page и единственную `Branch 1`, делает
  максимум один Save, не создаёт branch и не сохраняет auth/browser evidence.
- Published SemVer assets неизменяемы; rerun до публикации идемпотентен.

### Последствия

PR может доказать release build без secrets и mutations. Stable GitHub Release
финализируется только после AnkiWeb byte verification; prerelease AnkiWeb не
обновляет. DOM change или auth challenge требует адаптации/ручного решения и не
приводит к частичной скрытой публикации. Search UI остаётся вне этого решения.

### Где смотреть

`docs/release-automation.md`, `.github/workflows/release.yml`,
`scripts/release_common.py`, `scripts/manage_github_release.py`,
`scripts/publish_ankiweb.mjs`.

## ADR-028: Product notices разделяют release history и consent

### Статус

Принято.

### Контекст

История обновлений нужна на первом запуске и после skipped versions, но её
нельзя связывать с разрешением telemetry. Browser storage и package files не
переживают профильные обновления надёжно, а English Markdown не даёт RU/EN
parity для UI.

### Решение

- Два атомарных JSON store живут в profile `addon_data` и имеют собственные
  schema/migrations/quarantine.
- Consent и What’s New — отдельные accessible modal; coordinator всегда ставит
  требуемое решение раньше release history.
- Ничего не выбрано заранее; decline не ухудшает продукт, material notice
  change выключает effective purposes до re-consent.
- `release/changelog.json` — единый structured RU/EN source, остальные release
  и frontend outputs генерируются детерминированно.
- React общается только с loopback token API; foundation не отправляет события.

### Последствия

Обновления и ручной reopen не стирают историю или privacy choice. Package
содержит только read-only changelog, а runtime state остаётся per-profile.
Networking может добавляться отдельным reviewable изменением только поверх
этого fail-closed контракта.

### Где смотреть

`docs/product-notices-and-consent.md`, `docs/privacy-telemetry.md`,
`anki_study_report/product_notices.py`, `release/changelog.json`.

## ADR-029: Cloud telemetry принимается через staging-first EU gates

### Статус

Принято.

### Контекст

Telemetry service реализован, но production endpoint нельзя включать по одному
факту готовности кода. D1 jurisdiction задаётся при создании, R2 binding должен
явно выбирать EU, а секреты и реальные URL нельзя подменять placeholders или
предположениями.

### Решение

- Cloudflare inventory выполняется read-only до любых изменений.
- Staging и production получают разные EU D1/R2, Worker и секреты.
- Deploy остаётся manual-only; workflows используют pinned action SHA,
  Environment secrets, повторные migrations и synthetic lifecycle gates.
- Production принимается только после staging, deletion residue check и
  backup/temporary-restore drill.
- Add-on получает фактический Worker URL отдельным PR только после cloud
  acceptance и финализации RU/EN уведомления.

### Последствия

Кодовая готовность Stage 9.2 и эксплуатационная готовность Cloudflare — разные
статусы. До завершения приёмки telemetry остаётся fail-closed; этот проход не
создаёт release дополнения.

### Где смотреть

`docs/stage-9-telemetry-foundation-handoff.md`, `docs/privacy-telemetry.md`,
private repository `anki-study-report-telemetry`.
