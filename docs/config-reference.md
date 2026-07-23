# Справочник настроек и переменных окружения

**Снимок документации:** 2026-07-23.

Source of truth:

```text
anki_study_report/manifest.json
anki_study_report/config.json
anki_study_report/config_service.py
anki_study_report/dashboard_server.py
anki_study_report/__init__.py
docker/anki-e2e/
.github/workflows/ci-e2e.yml
```

Важно различать shipped config, code defaults, per-profile runtime state и dev-only E2E variables.

## Notification preferences

Notification settings хранятся отдельно от global `config.json` в per-profile `notifications.sqlite3` schema v1.

Defaults:

```text
notificationCenterEnabled = true
showUnreadBadge = true
showInAppToasts = true
minimumToastSeverity = critical
sound = none
osNotifications = none
all five categories = enabled
```

Detector thresholds не являются пользовательской конфигурацией.

## Add-on manifest

| Setting | Current | Риск |
| --- | --- | --- |
| `package` | `anki_study_report` | смена ломает identity/path |
| `name` | `Anki Study Report` | user-facing metadata |
| `mod` | package metadata | осознанный bump при release |
| `min_point_version` | `260500` | Anki 26.05 minimum |
| `max_point_version` | `0` | no upper bound |

## Shipped config

Основные user-facing keys:

```text
default_period
report_scope
selected_deck_ids
include_child_decks
track_reviewer_sessions
session_idle_timeout_seconds
session_gap_cap_seconds
use_study_time_stats
use_stats_cache_for_report
selected_profile
report_detail_level
answer_mode
enabled_metrics.*
web_dashboard.auto_start
web_dashboard.port
web_dashboard.idle_timeout_seconds
dashboard_display.selected_deck_ids
dashboard_display.selected_deck_names
dashboard_display.include_child_decks
```

Deprecated dashboard period keys могут сохраняться как migration data, но не публикуются как current Settings controls.

## Dashboard server

```text
host: 127.0.0.1
port default: 8766
idle timeout default: 1800 seconds
token: secrets.token_urlsafe(32)
```

Сервер нельзя открывать наружу без отдельного security review. Token не хранится в docs/logs/screenshots.

## Runtime data

```text
<profile>/addon_data/<addon_id>/
```

Там находятся cache, profile metadata, notifications, telemetry и logs. Эти данные не входят в package/git и не синхронизируются как add-on config.

## Public Settings/Profile API

`GET/POST /api/dashboard/settings` публикует только allowlisted sections:

```text
dashboard
report
data
server
```

Validation ranges:

```text
sessionIdleTimeoutSeconds  60..86400
sessionGapCapSeconds       1..3600 и <= session idle timeout
server.port                0 или 1024..65535, кроме 8765
server.idleTimeoutSeconds  0..86400
```

`GET/POST /api/profile` отдельно принимает `customStudyStartedOn` и `deckOverviewSort`.

## Docker/E2E collection inputs

Произвольный APKG/media input отсутствует. Collection source:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
docker/anki-e2e/fixtures/real-decks/manifest.json
```

## Docker/E2E runtime variables

| Variable | Default / source | Значение |
| --- | --- | --- |
| `ANKI_VERSION` | `26.05` | Anki Desktop version |
| `ANKI_SHA256` | workflow/build input | official archive digest |
| `ANKI_REQUIRE_SHA256` | cloud `1` | fail without exact hash |
| `ANKI_PYTHON_PACKAGE` | `anki==26.5` | Python package parity |
| `ANKI_BASE` | `/e2e/anki-data` | disposable base |
| `ANKI_PROFILE` | `E2E` | disposable profile name |
| `ANKI_PROFILE_DIR` | `${ANKI_BASE}/${ANKI_PROFILE}` | profile path |
| `KEEP_E2E_DATA` | `0` | preserve disposable data only for debug |
| `ANKI_STUDY_REPORT_E2E` | `1` | enable E2E shortcuts |
| `ANKI_STUDY_REPORT_E2E_ARTIFACTS` | `/e2e/artifacts` | artifact root |
| `ANKI_STUDY_REPORT_E2E_READY_FILE` | runtime path | readiness shared by waiter/add-on |
| `ANKI_STUDY_REPORT_E2E_PORT` | `8766` | loopback dashboard port |
| `ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT` | loopback fake | telemetry test endpoint |
| `E2E_MODE` | `standard` | `standard` or `perf100` |
| `ANKI_E2E_SCOPE` | `full` | product assertion scope |
| `ANKI_E2E_SCREENSHOT_WORKERS` | `3` | bounded 1..4 |
| `ANKI_E2E_RESOURCE_TELEMETRY` | `1` | resource sampler |
| `ANKI_E2E_VERIFY_RESTART` | `auto` | `full` requires restart |
| `ANKI_E2E_PREBUILT_ADDON_PATH` | empty/local source | exact package mount |
| `ANKI_E2E_PACKAGE_SOURCE` | `source-build` local | `source-build`, `fast-ci-artifact`, `release-artifact` |
| `ANKI_E2E_FAST_CI_RUN_ID` | empty | source successful Fast CI run |
| `ANKI_E2E_FAST_CI_TESTED_SHA` | empty | package tested commit, не current harness SHA |
| `ANKI_E2E_FAST_CI_PACKAGE_SHA256` | empty | exact package SHA-256 |
| `E2E_WORKFLOW_SOURCE_SHA` | current workflow SHA | current harness/workflow identity |
| `E2E_CHECKOUT_SHA` | current validated harness SHA | checkout used to run E2E |

Package tested SHA и E2E checkout SHA могут различаться только при validated `harness-only` reuse. Полный контракт: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md).

## E2E artifact directories

```text
<root>/runtime
<root>/diagnostics
<root>/reports
<root>/html
<root>/screenshots
<root>/package
```

Raw readiness/token, profile/collection и private paths не публикуются.

## Compatibility inputs

Legacy `strict-apkg`/`RequireApkgFixture` не включают отдельный source и нормализуются в обязательный standard real-deck contract. Три committed packages импортируются всегда.

## Internal/dev-only

- E2E env vars и handoff evidence;
- runtime paths;
- cache schemas;
- package identities;
- dashboard token;
- generated frontend assets;
- notification/telemetry SQLite.

Эти значения не являются пользовательскими Settings controls.
