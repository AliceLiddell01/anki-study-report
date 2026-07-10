# Справочник настроек и переменных окружения

Снимок документации: 2026-07-05.

Source of truth:

```text
anki_study_report/manifest.json
anki_study_report/config.json
anki_study_report/config_service.py
anki_study_report/dashboard_server.py
anki_study_report/__init__.py
docker/anki-e2e/
```

Важно различать shipped `config.json` и code defaults в `config_service.py`.
Некоторые default keys есть в коде, но отсутствуют в текущем shipped config.

## `manifest.json`

| Setting | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `package` | `anki_study_report` | Anki add-on identity | Нет | Смена ломает путь add-on/config/data |
| `name` | `Anki Study Report` | UI/Anki metadata | Да | Только косметика, но влияет на распознавание |
| `mod` | `1782864000` | Anki metadata | Нет | Нужен осознанный bump при релизе |
| `min_point_version` | `260500` | Anki compatibility | Да | Снижение требует реальной проверки старых Anki |
| `max_point_version` | `0` | Anki compatibility | Да | Ограничение может блокировать новые версии |

## Shipped `config.json`

| Setting | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `default_period` | `today` | report dialog period default | Да | Меняет ожидания первого отчета |
| `report_scope` | `all` | scope выбора колод | Да | Может сузить/расширить отчет |
| `selected_deck_ids` | `[]` | selected scope | Да | Некорректные IDs дают пустой/неожиданный отчет |
| `include_child_decks` | `true` | deck filter expansion | Да | Меняет состав колод |
| `track_reviewer_sessions` | `false` | `session_tracker.py` | Да | Включает локальный session tracking |
| `session_idle_timeout_seconds` | `600` | session tracker | Да | Слишком мало/много искажает study time |
| `session_gap_cap_seconds` | `120` | session tracker | Да | Искажает cap между действиями |
| `use_study_time_stats` | `false` | `study_time_integration.py` | Да | Зависит от доступности внешней статистики |
| `use_stats_cache_for_report` | `false` | report/cache integration | Да | Меняет источник parts отчета |
| `selected_profile` | `manual` | report dialog profiles | Да | Неверный profile может менять настройки отчета |
| `report_detail_level` | `normal` | report rendering | Да | Меняет детализацию Markdown/HTML |
| `answer_mode` | `auto` | metrics/report payload | Да | Меняет Pass/Fail vs standard semantics |
| `enabled_metrics.*` | см. config | metrics selection | Да | Отключение скрывает блоки отчета |
| `last_report_ts` | `null` | since-last-report period | Internal state | Не редактировать руками без причины |
| `web_dashboard.auto_start` | `false` | dashboard lifecycle | Да | Auto-start может создавать лишний local server |
| `web_dashboard.port` | `8766` | dashboard server | Да | Порт `8765` нормализуется обратно к default |
| `web_dashboard.idle_timeout_seconds` | `1800` | idle monitor | Да | `0` фактически отключает idle stop |
| `dashboard_display.period` | `all_time` | deprecated migration data | Нет | Stage 2 игнорирует ключ; Home всегда current-day, остальные pages используют history |
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
| `DEFAULT_PORT` | `8766` | server/config | Да | Порт может быть занят; server fallback на random port |
| `DEFAULT_IDLE_TIMEOUT_SECONDS` | `1800` | idle monitor | Да | Слишком малый timeout закрывает dashboard во время работы |
| token | generated `secrets.token_urlsafe(32)` | API auth | Нет | Не хранить в docs/logs/screenshots |

## Cache/runtime data

| Setting / path | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| Runtime data dir | `<profile>/addon_data/<addon_id>/` | `__init__.py` | Нет | Не хранить в repo |
| Fallback data dir | `anki_study_report/user_files/` | no profile fallback | Нет | Runtime fallback, ignored by git |
| Cache file | `study_report_cache.sqlite3` | `stats_cache.py` | Нет | Удаление сбросит cache |
| Cache schema | `CACHE_SCHEMA_VERSION = 1` | `stats_cache.py` | Нет | Изменение требует migration/rebuild |
| Report cache TTL | `5` seconds | `__init__.py` `_REPORT_CACHE` | Нет | Слишком большой TTL даст stale runtime report |
| Logs dir | `<runtime>/logs` | `extension_logging.py` | Да, через Logs page | Логи могут содержать runtime diagnostics |

## Integrations/session/study time

| Setting | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `track_reviewer_sessions` | `false` | `session_tracker.py` | Да | Включает собственный journal интервалов |
| `session_idle_timeout_seconds` | `600` | `session_tracker.py` | Да | Влияет на разрыв сессий |
| `session_gap_cap_seconds` | `120` | `session_tracker.py` | Да | Влияет на capped gaps |
| `use_study_time_stats` | `false` | `study_time_integration.py` | Да | Включает внешний источник времени, если доступен |

## Docker/E2E env vars

| Setting / env var | Default | Где используется | User-facing? | Риски изменения |
| --- | --- | --- | --- | --- |
| `ANKI_VERSION` | `26.05` | Docker build | Dev-only | Меняет реальную Anki runtime version |
| `ANKI_SHA256` | empty | Docker build | Dev-only | Нужен для reproducible download check |
| `ANKI_REQUIRE_SHA256` | `0` | Docker build | Dev-only | `1` без hash ломает build |
| `ANKI_PYTHON_PACKAGE` | `anki==26.5` | Docker image | Dev-only | Должен соответствовать Anki Desktop |
| `ANKI_BASE` | `/e2e/anki-data` | E2E scripts | Dev-only | Нельзя указывать unsafe path |
| `ANKI_PROFILE` | `E2E` | E2E profile | Dev-only | Меняет profile folder/name |
| `ANKI_PROFILE_DIR` | `${ANKI_BASE}/${ANKI_PROFILE}` | E2E scripts | Dev-only | Должен совпадать с profile |
| `KEEP_E2E_DATA` | `0` | `create-profile.sh` | Dev-only | `1` сохраняет старые данные для debug |
| `ANKI_STUDY_REPORT_E2E` | `1` in E2E | add-on bootstrap | Dev-only | Включает E2E shortcuts |
| `ANKI_STUDY_REPORT_E2E_ARTIFACTS` | `/e2e/artifacts` | E2E artifacts | Dev-only | Token-bearing artifacts не коммитить |
| `ANKI_STUDY_REPORT_E2E_ARTIFACTS_DIR` | empty/fallback | E2E artifact root override | Dev-only | Все category paths вычисляются относительно выбранного root |
| `ANKI_STUDY_REPORT_E2E_RUNTIME_DIR` | `<root>/runtime` | readiness/events/PIDs | Dev-only | Вычисляется runner-ом из artifact root |
| `ANKI_STUDY_REPORT_E2E_DIAGNOSTICS_DIR` | `<root>/diagnostics` | startup/failure logs | Dev-only | Вычисляется runner-ом из artifact root |
| `ANKI_STUDY_REPORT_E2E_REPORTS_DIR` | `<root>/reports` | machine-readable summaries | Dev-only | Вычисляется runner-ом из artifact root |
| `ANKI_STUDY_REPORT_E2E_HTML_DIR` | `<root>/html` | redacted DOM dumps | Dev-only | Вычисляется runner-ом из artifact root |
| `ANKI_STUDY_REPORT_E2E_SCREENSHOTS_DIR` | `<root>/screenshots` | visual proof | Dev-only | Вычисляется runner-ом из artifact root |
| `ANKI_STUDY_REPORT_E2E_PACKAGE_DIR` | `<root>/package` | Docker-built add-on | Dev-only | Вычисляется runner-ом из artifact root |
| `ANKI_STUDY_REPORT_E2E_READY_FILE` | `/e2e/artifacts/runtime/dashboard-ready.json` | readiness | Dev-only | Waiter и add-on должны читать/писать тот же path |
| `ANKI_STUDY_REPORT_E2E_PORT` | `8766` | E2E dashboard start | Dev-only | Порт для E2E server |
| `ANKI_STUDY_REPORT_E2E_DEBUG_QT` | `0` | `start-anki.sh` | Dev-only | Включает verbose Qt diagnostics |
| `ANKI_E2E_APKG_FIXTURE` | empty | PowerShell wrapper | Dev-only | Использовать только sanitized fixture |
| `ANKI_E2E_APKG_FIXTURE_PATH` | empty | container import | Dev-only | Container path to staged APKG |
| `ANKI_E2E_REQUIRE_APKG_FIXTURE` | empty/`0` | APKG mode | Dev-only | `1` делает отсутствие APKG ошибкой |
| `ANKI_E2E_REAL_MEDIA_DIR` | empty | real media allowlist copy | Dev-only | Только read-only media source |
| `ANKI_E2E_REQUIRE_REAL_MEDIA` | empty | real media mode | Dev-only | `1` требует allowlisted media |

## Что можно менять пользователю

- Report period/scope/decks.
- Dashboard deck filter; период dashboard больше не является настройкой.
- Dashboard port/auto-start/idle timeout.
- Session/study-time/cache options, если понятны последствия.

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

## Internal/dev-only

- E2E env vars.
- Runtime paths.
- Cache schema.
- Manifest package identity.
- Dashboard token.
- Generated frontend assets.
