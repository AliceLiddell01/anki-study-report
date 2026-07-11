# Decision log

Снимок документации: 2026-07-11.

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

Audit 2026-07-11 остановил публикацию из-за недокументированного происхождения
media в tracked APKG fixture. Репозиторий остаётся private до owner review,
замены fixture на synthetic либо подтверждения прав.

### Где смотреть

`docs/public-repository-readiness.md`, `docs/fixtures-and-test-data.md`,
`docs/security-and-safety.md`, `docs/ci-cd.md`.
