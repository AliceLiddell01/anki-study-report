# Архитектура

## Локальные signals и notifications

`signal_detection.py` вычисляет четыре bounded detector family из cache
snapshot, Deck Hub и одного grouped `revlog` query. `notification_store.py`
владеет отдельной per-profile SQLite schema, reconciliation и preferences.
`__init__.py` привязывает stores заново при открытии профиля и публикует строгие
handlers в `dashboard_server.py`. React читает их через `notificationsApi.ts`;
App Shell монтирует bell/toasts, route pages остаются lazy boundaries. Этот
поток не соединён с `TelemetryClient`.

Stage 7 adds `fsrs_service.py` as an isolated read-only Anki adapter and pure
aggregate layer. `statistics_service.py` publishes only lightweight capability;
`dashboard_server.py` exposes a strict token-protected FSRS operation union.

Снимок документации: 2026-07-15.

## Общий поток данных

```mermaid
flowchart TD
    A["Anki collection"] --> B["metrics.py"]
    A --> C["stats_cache.py"]
    C --> D["report_from_cache.py"]
    C --> S["statistics_service.py"]
    B --> E["dashboard_payload.py"]
    D --> E
    E --> F["dashboard_server.py"]
    F --> G["web-dashboard React app"]
    S --> F
    A --> Q["search_service.py / QueryOp"]
    Q --> F
    A --> T["triage_service.py / QueryOp"]
    N["NotificationStore active card Signals"] --> T
    T --> F
    F --> M["entity_actions.py / CollectionOp"]
    B --> H["report_builder.py"]
    H --> I["Markdown/HTML report dialog"]
```

Главный принцип: Anki-зависимый код и UI orchestration остаются в
`__init__.py`, а преобразования данных по возможности вынесены в чистые модули,
которые можно импортировать и тестировать без установленного Anki.

## Python add-on

`anki_study_report/__init__.py` - entrypoint Anki add-on. Он:

- импортирует `aqt`, регистрирует меню и hooks;
- создает диалоги `StudyReportDialog`, `IntegrationDiagnosticsDialog`,
  `WebDashboardSettingsDialog`, `LauncherDialog`;
- управляет dashboard server lifecycle;
- соединяет cache, сбор метрик, публикацию dashboard report и UI actions;
- содержит E2E bootstrap, который активен только при `ANKI_STUDY_REPORT_E2E=1`.

Важно: этот файл намеренно остается adapter/orchestration layer. Когда
появляется новая чистая логика трансформации данных, ее лучше выносить в
отдельный модуль и покрывать тестами без Anki.

## Метрики и отчеты

`metrics.py` собирает основные данные из Anki collection:

- total reviews, new cards, answer distribution;
- deck breakdown;
- due tomorrow;
- FSRS-related данные;
- attention cards и note type diagnostics;
- pass/fail метрики.

`heatmap_metrics.py` отвечает за календарную активность и streaks.

`forecast_metrics.py` строит легкий прогноз нагрузки.

`report_builder.py` рендерит Markdown/HTML отчет для Anki dialog.

`study_time_integration.py` и `session_tracker.py` дают альтернативные источники
реального времени обучения, если соответствующие настройки включены.

## Cache layer

`stats_cache.py` управляет SQLite cache в runtime data директории профиля Anki:

```text
<profile>/addon_data/<addon_id>/study_report_cache.sqlite3
```

Если профиль недоступен, fallback - `anki_study_report/user_files/`.

`report_from_cache.py` адаптирует cache snapshot в части отчета. Он нужен,
чтобы dashboard мог быстро показывать долгие периоды и историю без полного
пересчета legacy-метрик каждый раз.

Кэш не должен менять публичный dashboard contract. Если cache и legacy дают
разную форму данных, адаптер обязан привести ее к тому же payload.

`profile_service.py` получает исходный all-collection snapshot до применения
dashboard period/deck filters. Он строит compact Profile slice и обслуживает
атомарный `<runtime>/profile.json`; frontend не сканирует collection и не
пересчитывает raw revlog.

`activity_service.py` получает тот же snapshot, но применяет текущий historical
dashboard deck scope. Он публикует bounded one-year `activityHub`, day-deck
details и derived daily/weekly events; старый `activity` contract остаётся для
Home/backward compatibility.

`deck_hub.py` объединяет current Anki deck catalog с теми же scoped direct
deck rows. Он исключает filtered decks, сохраняет structural ancestors,
агрегирует subtree bottom-up и публикует normalized `deckHub`. Cache schema v3
использует current home deck (`odid`) для карт во filtered deck.

## Dashboard payload

`dashboard_payload.py` - чистый слой трансформации метрик в JSON. Его ключевые
entrypoints:

- `build_dashboard_report_payload(metrics, metadata, cache_summary=None)`
- `build_default_dashboard_metadata(snapshot, today_key, display_settings=None, now=None)`
- `metrics_from_cache_snapshot(snapshot, today_key, display_settings=None)`

Payload должен соответствовать `web-dashboard/src/types/report.ts`.

Текущие top-level ключи:

```text
metadata
summary
kpis
answerDistribution
activity
comparison
decks
attentionCards
attentionCardsStatus
noteTypeCatalog
forecast
fsrs
recommendations
cache
today (optional Home-only slice)
profile (all-collection lifetime slice)
activityHub (scoped bounded Activity slice)
deckHub (scoped normalized Decks v2 hierarchy)
statisticsHub (bounded initial 90d Statistics result)
```

## Dashboard server

`dashboard_server.py` поднимает локальный HTTP server на `127.0.0.1`. Он:

- отдает static frontend из `anki_study_report/web_dashboard`;
- защищает report/API token-ом;
- публикует последний report payload в памяти;
- обслуживает media-preview безопасным allowlist/sanitizer путем;
- прокидывает dashboard actions обратно в Anki через callbacks.
- обслуживает narrow token-protected `GET/POST /api/profile`.
- обслуживает narrow token-protected `POST /api/statistics/query`.
- обслуживает read-only `POST /api/search/query` и `/api/search/inspect`;
  collection work выполняется сериализованным `QueryOp` через
  `search_runtime.py`, а validation/projection изолированы в
  `search_service.py`.
- обслуживает additive read-only `POST /api/triage/query`: `triage_runtime.py`
  сериализует collection read через `QueryOp`, а `triage_service.py`
  нормализует существующий attention collector, active card Signals и exact
  Search card rows и confirmed-profile content checks в bounded deterministic
  projection без triage persistence, collection mutations или full preview;
- обслуживает `POST /api/inspection-profiles/query|validate|update`:
  `inspection_profile_runtime.py` сериализует model/card reads через `QueryOp`,
  `inspection_profile_service.py` владеет structures/fingerprint/lifecycle/
  allowlisted evaluation, а `inspection_profile_store.py` — только strict
  validation, revision, atomic profile-local persistence and recovery;
- обслуживает отдельные card/note mutation endpoints; strict validation и
  preflight находятся в `entity_actions.py`, а official Anki wrapper bridge —
  в `entity_action_runtime.py`;

Frontend не должен иметь прямой доступ к Anki collection. Все действия идут
через API server и контролируются Python side.

`metrics.py` сохраняет legacy attention behavior и отдельно предоставляет
один bounded internal candidate DTO для triage. `NotificationStore` владеет
Signals, `search_service.project_card_row()` — compact identity, а
`InspectionProfileStore` — per-profile configuration. Triage объединяет их,
сохраняет learning reasons независимо от profile lifecycle и принимает только
confirmed/current content failures. Contracts:
`docs/cards-v2-triage-read-api.md`, `docs/inspection-profiles-v1.md`.

Security details: `docs/security-and-safety.md`.

## Frontend dashboard

`web-dashboard` - Vite + React + TypeScript приложение.

`web-dashboard/src/app/App.tsx` читает token из query string и грузит:

```text
/api/report?token=<token>
```

В development mode, если API недоступен и ошибка не `403`, приложение может
подставить `mockReport`. В production это не должно маскировать проблему
реального dashboard server.

Hash router находится в `web-dashboard/src/app/router.tsx`. Текущие страницы:

```text
#/home
#/profile
#/decks
#/cards
#/search
#/calendar
#/stats
#/stats/quality
#/stats/load
#/stats/progress
#/stats/decks
#/actions
#/settings
#/settings/data
#/settings/server
#/settings/sources
#/settings/logs
```

Старые placeholder routes `#/fsrs` и `#/browse` удалены в Stage 15. `#/stats`
вернулся только вместе с полноценным five-section Statistics v1; unknown hash
fallback ведёт на `#/home`.

Видимая primary navigation отделена от полного registry routes. Она содержит
`Сегодня`, `Активность`, `Статистика`, `Колоды` и `Карточки`. `TopNav.tsx` размещает
Profile/Settings/Tools в avatar dropdown, а `SettingsLayout.tsx` связывает
report/data/server/sources/logs постоянным Settings Hub sidebar. Старые
`#/integrations` и `#/logs` redirect-ятся в canonical diagnostics routes.
Технические страницы не показываются как основные аналитические вкладки.

`AppLayout` также владеет persistent `GlobalUtilityDock` вне route content.
Theme preference остаётся browser-local (`light|dark|system`) и применяется
inline до React render; dock фиксирует explicit light/dark без backend API.
Там же находится независимый selector языка `ru|en`. `i18next` и
`react-i18next` загружают bundled resources до первого render, русский служит
default/fallback, а `anki-study-report-language` хранит browser-local выбор.
Смена языка не меняет payload/API и синхронно обновляет product UI,
`html lang` и `document.title`. Полный contract: `docs/localization.md`.

Подробная карта frontend routes/pages/helpers: `docs/frontend-map.md`.
Продуктовое решение по навигации: `docs/navigation-ia.md`.
Search foundation и mutation architecture: `docs/search-query-foundation.md`,
`docs/search-v1-and-safe-actions.md`.

## Runtime data

Runtime data хранится отдельно от исходников, когда Anki profile доступен:

```text
<profile>/addon_data/<addon_id>/
```

Там размещаются cache, `profile.json` и logs. Старый `anki_study_report/user_files/`
используется как fallback и мигрируется при возможности.

В git не должны попадать:

```text
anki_study_report/user_files/*.sqlite3
anki_study_report/user_files/logs/*.log*
e2e-artifacts/
web-dashboard/dist/
anki_study_report/web_dashboard/
*.ankiaddon
```

## Product notices и privacy state

`product_notices.py` владеет двумя атомарными per-profile JSON stores и строгой
валидацией consent. `dashboard_server.py` публикует token-protected local API,
а `ProductNoticeCoordinator` последовательно показывает consent и What’s New.
`release/changelog.json` является каноническим source; Markdown и bundled
RU/EN assets генерируются. Этот слой работает офлайн и не является telemetry
sender. Отдельный Python client валидирует semantic events, хранит bounded
per-profile SQLite queue и выполняет consent-gated background delivery; React
не знает remote endpoint/credentials. Контракты:
`docs/product-notices-and-consent.md` и `docs/telemetry-client.md`.
## Declarative compact formatter runtime

C1.5R.2 introduces an independent per-profile configuration path:

```text
<profile>/addon_data/<addon-id>/card_display_formatters.json
```

Architecture flow:

```text
DashboardServerManager handlers
→ CardDisplayFormatterStore read once per Search/Triage request
→ immutable CardDisplayFormatterResolver
→ Search exact-card projector
→ Triage reuses Search-owned card rows
→ canonical R1 fallback on every formatter/store failure
```

The store is separate from `inspection_profiles.json`, global add-on config,
collection data, note types and templates. It uses strict schema v1,
deterministic atomic JSON writes, optimistic revision conflicts, corruption
quarantine and future-schema preserve/fail-closed behavior.

The formatter parser emits bounded ordered text/line/image/audio tokens only. It
executes no user program, reads no media file, loads no remote resource and does
not alter Inspector/expanded preview. Search v2 and Triage v3 payloads remain
unchanged.
