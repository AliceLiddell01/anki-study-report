# Справочник настроек и переменных окружения

**Снимок документации:** 2026-07-23

Source of truth:

```text
anki_study_report/manifest.json
anki_study_report/config.json
anki_study_report/config_service.py
anki_study_report/dashboard_server.py
anki_study_report/__init__.py
docker/anki-e2e/
```

Важно различать shipped `config.json`, code defaults из `config_service.py`,
per-profile runtime state и dev-only переменные E2E. Эти слои не должны
подменять друг друга.

## Notification preferences

Notification settings не находятся в global `config.json`: это отдельный
per-profile schema v1 в `notifications.sqlite3`. Public defaults — unread badge
и in-app toasts включены, minimum severity `critical`, все пять категорий
включены. `sound` и `osNotifications` фиксированы в `none`. Detector thresholds
не являются пользовательской конфигурацией.

## `manifest.json`

| Setting | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `package` | `anki_study_report` | Anki add-on identity | Нет | Смена ломает путь add-on/config/data |
| `name` | `Anki Study Report` | UI/Anki metadata | Да | Только косметика, но влияет на распознавание |
| `mod` | `1783987200` | Anki metadata | Нет | Нужен осознанный bump при релизе |
| `min_point_version` | `260500` | Anki compatibility | Да | Снижение требует реальной проверки старых Anki |
| `max_point_version` | `0` | Anki compatibility | Да | Ограничение может блокировать новые версии |

## Shipped `config.json`

| Setting | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `default_period` | `today` | report dialog period default | Да | Меняет ожидания первого отчёта |
| `report_scope` | `all` | scope выбора колод | Да | Может сузить или расширить отчёт |
| `selected_deck_ids` | `[]` | selected scope | Да | Некорректные IDs дают пустой или неожиданный отчёт |
| `include_child_decks` | `true` | deck filter expansion | Да | Меняет состав колод |
| `track_reviewer_sessions` | `false` | `session_tracker.py` | Да | Включает локальный session tracking |
| `session_idle_timeout_seconds` | `600` | session tracker | Да | Слишком мало или много искажает study time |
| `session_gap_cap_seconds` | `120` | session tracker | Да | Искажает cap между действиями |
| `use_study_time_stats` | `false` | `study_time_integration.py` | Да | Зависит от доступности внешней статистики |
| `use_stats_cache_for_report` | `false` | report/cache integration | Да | Меняет источник частей отчёта |
| `selected_profile` | `manual` | report dialog profiles | Да | Неверный profile меняет настройки отчёта |
| `report_detail_level` | `normal` | report rendering | Да | Меняет детализацию Markdown/HTML |
| `answer_mode` | `auto` | metrics/report payload | Да | Меняет Pass/Fail и standard semantics |
| `enabled_metrics.*` | см. config | metrics selection | Да | Отключение скрывает блоки отчёта |
| `last_report_ts` | `null` | since-last-report period | Internal state | Не редактировать вручную без причины |
| `web_dashboard.auto_start` | `false` | dashboard lifecycle | Да | Auto-start может создавать лишний local server |
| `web_dashboard.port` | `8766` | server/config | Да | Порт `8765` нормализуется обратно к default |
| `web_dashboard.idle_timeout_seconds` | `1800` | idle monitor | Да | `0` фактически отключает idle stop |
| `dashboard_display.period` | `all_time` | deprecated migration data | Нет | Home всегда current-day; ключ не публикуется в Settings |
| `dashboard_display.custom_start_date` | `""` | deprecated migration data | Нет | Не публикуется в Settings Hub |
| `dashboard_display.custom_end_date` | `""` | deprecated migration data | Нет | Не публикуется в Settings Hub |
| `dashboard_display.selected_deck_ids` | `[]` | dashboard deck filter | Да | Пустой список означает все колоды |
| `dashboard_display.selected_deck_names` | `[]` | dashboard labels | Да | Label-only, но должен соответствовать IDs |
| `dashboard_display.include_child_decks` | `true` | dashboard deck filter | Да | Меняет состав дочерних колод |

## Code defaults из `config_service.py`

`DEFAULT_CONFIG` дополнительно включает default-enabled metric keys, которых
может не быть в shipped `config.json`:

```text
average_answer_seconds
answer_distribution
forecast
```

Если add-on читает неполный config, `_enabled_metrics_from_config(...)`
подставляет defaults из кода.

## Dashboard server settings

| Setting / env var | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `DEFAULT_HOST` | `127.0.0.1` | `dashboard_server.py` | Нет | Не открывать наружу без security review |
| `DEFAULT_PORT` | `8766` | server/config | Да | Порт может быть занят; server допускает fallback на random port |
| `DEFAULT_IDLE_TIMEOUT_SECONDS` | `1800` | idle monitor | Да | Слишком малый timeout закрывает dashboard во время работы |
| token | generated `secrets.token_urlsafe(32)` | API auth | Нет | Не хранить в docs, logs или screenshots |

## Cache/runtime data

| Setting / path | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| Runtime data dir | `<profile>/addon_data/<addon_id>/` | `__init__.py` | Нет | Не хранить в repo |
| Fallback data dir | `anki_study_report/user_files/` | no-profile fallback | Нет | Runtime fallback, ignored by Git |
| Cache file | `study_report_cache.sqlite3` | `stats_cache.py` | Нет | Удаление сбросит cache |
| Cache schema | `CACHE_SCHEMA_VERSION = 3` | `stats_cache.py` | Нет | Старый cache требует rebuild |
| Report cache TTL | `5` seconds | `__init__.py` `_REPORT_CACHE` | Нет | Слишком большой TTL даст stale report |
| Logs dir | `<runtime>/logs` | `extension_logging.py` | Да, через Logs page | Логи могут содержать diagnostics |
| Profile preferences | `<runtime>/profile.json` | `profile_service.py` | Да, через Profile | Per-profile, atomic; не включать в package/git |

## Integrations/session/study time

| Setting | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `track_reviewer_sessions` | `false` | `session_tracker.py` | Да | Включает собственный journal интервалов |
| `session_idle_timeout_seconds` | `600` | session tracker | Да | Влияет на разрыв сессий |
| `session_gap_cap_seconds` | `120` | session tracker | Да | Влияет на capped gaps |
| `use_study_time_stats` | `false` | study time integration | Да | Включает внешний источник времени, если доступен |

## Docker/E2E env vars

Docker E2E не принимает произвольный APKG или media directory. Единственный
source collection content — три committed packages и их manifest:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
docker/anki-e2e/fixtures/real-decks/manifest.json
```

| Setting / env var | Default | Где используется | Риски изменения |
| --- | --- | --- | --- |
| `ANKI_VERSION` | `26.05` | Docker build | Меняет реальную Anki runtime version |
| `ANKI_SHA256` | empty | Docker build | Нужен для reproducible download check |
| `ANKI_REQUIRE_SHA256` | `0` | Docker build | `1` без hash ломает build |
| `ANKI_PYTHON_PACKAGE` | `anki==26.5` | Docker image | Должен соответствовать Anki Desktop |
| `ANKI_BASE` | `/e2e/anki-data` | E2E scripts | Нельзя указывать unsafe path |
| `ANKI_PROFILE` | `E2E` | E2E profile | Меняет profile folder/name |
| `ANKI_PROFILE_DIR` | `${ANKI_BASE}/${ANKI_PROFILE}` | E2E scripts | Должен совпадать с profile |
| `KEEP_E2E_DATA` | `0` | `create-profile.sh` | `1` сохраняет disposable data для debug |
| `ANKI_STUDY_REPORT_E2E` | `1` in E2E | add-on bootstrap | Включает E2E shortcuts |
| `ANKI_STUDY_REPORT_E2E_ARTIFACTS` | `/e2e/artifacts` | artifact root | Token-bearing artifacts не коммитить |
| `ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR` | empty/fallback | artifact root override | Category paths вычисляются относительно root |
| `ANKI_STUDY_REPORT_E2E_RUNTIME_DIR` | `<root>/runtime` | readiness/events/PIDs | Вычисляется runner-ом |
| `ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR` | `<root>/diagnostics` | startup/failure logs | Вычисляется runner-ом |
| `ANKI_STUDY_REPORT_E2E_REPORTS_DIR` | `<root>/reports` | machine-readable reports | Вычисляется runner-ом |
| `ANKI_STUDY_REPORT_E2E_HTML_DIR` | `<root>/html` | redacted DOM dumps | Вычисляется runner-ом |
| `ANKI_STUDY_REPORT_E2E_SCREENSHOTS_DIR` | `<root>/screenshots` | visual proof | Вычисляется runner-ом |
| `ANKI_STUDY_REPORT_E2E_PACKAGE_DIR` | `<root>/package` | exact add-on archive | Вычисляется runner-ом |
| `ANKI_STUDY_REPORT_E2E_READY_FILE` | `<root>/runtime/dashboard-ready.json` | readiness | Waiter и add-on используют один path |
| `ANKI_STUDY_REPORT_E2E_PORT` | `8766` | E2E dashboard | Только loopback внутри disposable environment |
| `ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT` | loopback fake | telemetry E2E | Читается только вместе с E2E mode |
| `ANKI_STUDY_REPORT_E2E_DEBUG_QT` | `0` | `start-anki.sh` | Включает verbose Qt diagnostics |
| `E2E_MODE` | `standard` | canonical workload | Поддерживаются `standard`, `perf100`; legacy cloud input `strict-apkg` нормализуется в `standard` |
| `ANKI_E2E_SCOPE` | `full` | targeted product assertions | Не отключает обязательный real-deck import |
| `ANKI_E2E_PERF100` | empty | scenario applicator | `1` выбирает 100 distinct existing cards без cloning |
| `ANKI_E2E_SCREENSHOT_WORKERS` | `3` | browser capture | Допустимы `1..4`; менять только в performance-задаче |
| `ANKI_E2E_RESOURCE_TELEMETRY` | `1` | cgroup sampler | `0` допустим только для явно ограниченного run |
| `ANKI_E2E_VERIFY_RESTART` | `auto` | restart gate | `full` автоматически требует restart |
| `ANKI_E2E_PREBUILT_ADDON_PATH` | empty | exact package consumer | Обязателен для Fast CI/release artifact source |
| `ANKI_E2E_PACKAGE_SOURCE` | `source-build` | package provenance | `source-build`, `fast-ci-artifact` или `release-artifact` |
| `ANKI_E2E_FAST_CI_RUN_ID` | empty | handoff evidence | Должен соответствовать exact successful Fast CI run |
| `ANKI_E2E_FAST_CI_TESTED_SHA` | empty | handoff evidence | Должен совпадать с проверяемым commit SHA |
| `ANKI_E2E_FAST_CI_PACKAGE_SHA256` | empty | handoff evidence | Должен совпадать с exact package artifact |

`RequireApkgFixture` остаётся только ограниченным compatibility input старого
cloud workflow. Он не включает отдельный режим, не задаёт path и не допускает
fallback: три committed package обязательны всегда.

## Что можно менять пользователю

- Report period, scope и decks.
- Dashboard deck filter; период dashboard больше не является настройкой.
- Dashboard port, auto-start и idle timeout.
- Session/study-time/cache options, если понятны последствия.
- Profile custom study start date и deck overview sort.

## Public Settings Hub API

`GET/POST /api/dashboard/settings` публикует только sections `dashboard`,
`report`, `data`, `server`. Полная shape и save model: `docs/settings-hub.md`.

Validation ranges:

```text
sessionIdleTimeoutSeconds  60..86400
sessionGapCapSeconds       1..3600 и не больше session idle timeout
server.port                0 или 1024..65535, кроме 8765
server.idleTimeoutSeconds  0..86400
```

Partial update сохраняет unknown/internal top-level и nested config keys.

`GET/POST /api/profile` — отдельный allowlist и не часть add-on config:
`customStudyStartedOn` (`null` или non-future ISO date) и `deckOverviewSort`
(`name`, `reviews`, `active_days`).

## Internal/dev-only

- E2E env vars.
- Runtime paths.
- Cache schema.
- Manifest package identity.
- Dashboard token.
- Generated frontend assets.

## Product notice runtime state

`product_notices.json` и `privacy.json` находятся рядом с `profile.json` в
`<profile>/addon_data/<addon_id>/`. Это не add-on config и не синхронизируется
через Anki Sync. `release/changelog.json` — tracked canonical input;
`anki_study_report/changelog.json` — generated packaged read-only asset.

`telemetry.sqlite3` находится в том же per-profile runtime directory. Это не
user config и не Anki Sync data. Public package содержит только read-only
`telemetry_contract.json`. Production endpoint закреплён в Python runtime;
React получает только bounded public status без URL или credentials.
