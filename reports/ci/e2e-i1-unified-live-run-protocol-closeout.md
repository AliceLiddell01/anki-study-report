# Итоговый отчёт: E2E-I1 — единый live-протокол выполнения Fast CI и real-Anki Docker E2E

## Статус

```text
Дата завершения: 2026-07-24
Статус реализации: COMPLETE ON FEATURE BRANCH
Статус обязательных проверок: PASS
Рабочая ветка: platform/e2e-observability-roadmap
Base branch: core
Base SHA: 8f8d841bc4b540f9e1cedf7c5787c1b3f5ee5edb
Финальный implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Pull request: НЕ СОЗДАН
Merge в core: НЕ ВЫПОЛНЕН
Auto-merge: НЕ ВКЛЮЧЁН
Release / tag / GitHub Release / AnkiWeb publication: НЕ ВЫПОЛНЕНЫ
Следующий этап E2E-I2: НЕ НАЧАТ
```

Этап `E2E-I1` реализовал единый schema-versioned lifecycle для Fast CI и real-Anki Docker E2E. Крупные фазы теперь немедленно отображаются в консоли и одновременно сохраняются как детерминированный `run-events.jsonl`. Контракт прошёл package-producing Fast CI и два независимых `standard/full` real-Anki E2E на одном exact package и одном exact commit.

Актуальный технический контракт: [`../../docs/run-event-protocol.md`](../../docs/run-event-protocol.md).

Roadmap всего контура `E2E-I1`–`E2E-I6`: [`../../roadmap/platform/e2e-observability-build-identity.md`](../../roadmap/platform/e2e-observability-build-identity.md).

## Цель этапа

До `E2E-I1` проект уже имел:

- Fast CI timing;
- Docker phase/resource telemetry;
- raw logs;
- API/browser/restart reports;
- screenshots;
- artifact manifest;
- exact Fast CI package handoff;
- real-deck Docker E2E.

Но execution evidence был фрагментирован между GitHub workflow YAML, PowerShell, Bash, Python и Node.js. Во время длительных операций пользователь видел либо общий step, либо длинный интервал без устойчивого lifecycle. После failure приходилось вручную восстанавливать, какая фаза реально началась, завершилась или осталась активной.

Цели `E2E-I1`:

1. Ввести один общий event contract для Fast CI и Docker E2E.
2. Сразу показывать крупные фазы в console output.
3. Сохранять те же события в machine-readable JSONL.
4. Использовать стабильные phase IDs, совпадающие с timing/orchestration.
5. Сохранить прежние raw diagnostics и telemetry.
6. Сделать Compose output детерминированным и неинтерактивным в CI.
7. Fail closed отклонять неизвестные, повреждённые или небезопасные события.
8. Встроить stream в Fast CI diagnostics, Docker manifest и public E2E artifact.

## Границы scope

В scope вошли:

- schema v1;
- registry producers и phases;
- run/phase/message lifecycle;
- console formatter;
- append-only JSONL writer;
- concurrent append protection;
- security validation;
- Fast CI integration;
- Docker E2E integration;
- artifact manifest/exporter integration;
- deterministic Compose output;
- success и controlled-failure tests;
- production telemetry race, обнаруженный финальным E2E и необходимый для завершения stage gate.

Вне scope остались:

- item-level progress маршрутов, тем и preview anchors;
- расширение browser scenarios;
- pixel/perceptual visual regression;
- стабильные failure codes и primary/secondary failure summaries;
- отдельный preflight/cancellation contract;
- non-release build identity;
- единый финальный run summary;
- performance blocking thresholds;
- автоматические retries;
- внешняя logging/observability platform;
- release или публикация;
- merge в `core`;
- PR в `core`.

## Принятая архитектура

```text
Fast CI / Docker orchestration
→ schema-validated event
→ немедленная console line
→ cross-platform append-only JSONL
→ финальная validation
→ diagnostics/public artifact
```

Единая реализация:

```text
docker/anki-e2e/run_event_protocol.py
```

Производители:

```text
fast-ci
docker-e2e
```

Event kinds:

```text
run
phase
message
```

Statuses:

```text
run:     start | pass | fail | cancel
phase:   start | pass | fail | skip | cancel
message: info
```

## Schema v1

Каждая JSONL-строка содержит строго упорядоченные поля:

```text
schemaVersion
timestampUtc
elapsedMs
producer
phaseId
eventKind
status
durationMs
current
total
message
failureCode
```

Пример:

```json
{"schemaVersion":1,"timestampUtc":"2026-07-23T19:43:58.751Z","elapsedMs":2,"producer":"fast-ci","phaseId":"run","eventKind":"run","status":"start","durationMs":null,"current":null,"total":null,"message":"pipeline=canonical","failureCode":null}
```

`failureCode` зарезервирован для `E2E-I3` и в текущем этапе всегда равен `null`.

Финализированный stream обязан:

- начинаться одним `run/start`;
- использовать одного producer;
- содержать только зарегистрированные phases/statuses;
- иметь неубывающий `elapsedMs`;
- завершаться одним `run/pass`, `run/fail` или `run/cancel`;
- использовать compact deterministic JSON;
- быть UTF-8 без BOM;
- завершать каждую запись `\n`.

## Консольный lifecycle

Fast CI:

```text
[00:12.040] [FAST] [frontend-vitest] START
[00:52.603] [FAST] [frontend-vitest] PASS duration=40563ms
```

Docker E2E:

```text
[00:10.112] [E2E] [browser-smoke-first] START
[00:42.316] [E2E] [browser-smoke-first] PASS duration=32204ms
```

ANSI не является частью контракта. Console message сначала проходит ту же security validation, что и JSONL.

## Registry phases

### Fast CI

Registry синхронизирован с `scripts/ci_fast_timing.py`. Import-time parity check запрещает рассинхронизацию timing и run-events registries.

Основные фактически выполненные фазы финального run:

```text
install-python-dependencies
install-frontend-dependencies
changelog-check
frontend-typecheck-tests
frontend-vitest
frontend-vite-build
frontend-bundle-check
frontend-addon-assets-copy
python-pytest
package-build-check
package-check-only
verification-planner
ci-summary
package-metadata-write
package-staged-validation
package-metadata-verify
```

### Docker E2E

```text
workspace-copy
exact-package-validation
frontend-dependency-install
frontend-build
addon-package
profile-bootstrap
collection-bootstrap
real-deck-import
scenario-preparation
addon-install
anki-start-first
dashboard-ready-first
api-smoke-first
browser-smoke-first
anki-restart
dashboard-ready-restart
api-smoke-restart
telemetry-restart
artifact-manifest
```

Cloud E2E с exact package выполняет `exact-package-validation`; local `source-build` использует frontend/package phases.

## Реализация по слоям

### Общий schema/JSONL runtime

Файл:

```text
docker/anki-e2e/run_event_protocol.py
```

Реализовано:

- schema validation;
- deterministic serialization;
- console formatting;
- initialization/finalization;
- append-only writer;
- state/lock sidecars;
- cross-platform file locking;
- stream validation;
- CLI `initialize`, `emit`, `finish-run`, `validate`.

### Fast CI

Файлы:

```text
.github/workflows/ci-fast.yml
scripts/ci_fast_timing.py
scripts/write_ci_fast_summary.ps1
```

Результат:

- существующий timing API сохранён;
- каждый timing phase start/finish создаёт соответствующее run event;
- Fast CI finalization закрывает незавершённые phases как failure;
- финальный run result повторно валидируется;
- `ci-fast/run-events.jsonl` входит в diagnostics artifact;
- transient `.lock`/`.state.json` не входят в public inventory;
- значения `github.*` передаются в PowerShell через `env`, а не вставляются в inline executable text.

### Docker E2E

Файлы:

```text
docker/anki-e2e/run-e2e.sh
scripts/run_anki_e2e_docker.ps1
```

Результат:

- `phase_start` немедленно публикует `phase/start`;
- `phase_end` публикует terminal status и duration;
- прежний `e2e-telemetry.py` сохраняется;
- active phase при shell failure закрывается как `phase/fail`;
- cleanup сохраняет canonical result;
- итоговый stream завершается и валидируется;
- CI Compose запускается без TTY animation и interactive menu.

### Artifact manifest и public exporter

Файлы:

```text
docker/anki-e2e/write-artifact-manifest.py
scripts/prepare_ci_e2e_artifacts.py
scripts/verify_fast_ci_e2e_handoff.py
```

Результат:

- success manifest требует `reports/run-events.jsonl`;
- stream индексируется как обычный report;
- public exporter валидирует source и copied stream;
- успешный E2E без stream отклоняется;
- package/harness reuse evidence продолжает проверяться независимо;
- legacy exporter API сохранён для существующих тестов и callers;
- повторный импорт wrapper-а стал idempotent и не накапливает monkeypatch wrappers.

## Security и privacy

Validator отклоняет:

- unknown schema/status/kind/phase;
- отрицательные duration/progress values;
- несогласованные `current`/`total`;
- control characters, multiline и NUL;
- token-bearing URLs;
- authorization/private-key material;
- GitHub/OpenAI-style secret forms;
- Windows/UNC/private Linux absolute paths;
- сообщения длиннее 512 UTF-8 bytes;
- event lines длиннее 2048 bytes;
- BOM, partial line, malformed JSON;
- non-deterministic field order/serialization;
- non-null `failureCode` до `E2E-I3`.

Дополнительные гарантии:

- dashboard token не попадает в stream;
- raw readiness не публикуется;
- public artifact exporter не доверяет исходному JSONL без validation;
- public copied stream валидируется повторно;
- transient writer sidecars не считаются evidence;
- GitHub context values не интерполируются напрямую в PowerShell script body.

## Concurrent append

Writer использует:

```text
Windows: msvcrt.locking
Linux:   fcntl.flock
```

После получения exclusive lock запись выполняется одним append и `fsync`. Focused test с 24 параллельными process writers подтвердил:

```text
corrupted lines: 0
lost messages: 0
duplicate final run events: 0
```

## Docker Compose в CI

В CI установлены:

```text
COMPOSE_ANSI=never
COMPOSE_PROGRESS=plain
COMPOSE_MENU=0
COMPOSE_STATUS_STDOUT=1
```

Compose invocation:

```text
docker compose --ansi never --progress plain run --no-TTY ...
```

Local interactive behavior сохраняется без явного `CI`/`GITHUB_ACTIONS`.

## Тестовое покрытие

Добавлены или обновлены:

```text
tests/test_run_event_protocol.py
tests/test_run_event_integration.py
tests/test_run_event_controlled_failure.py
tests/test_ci_fast_run_events.py
tests/test_ci_fast_workflow.py
tests/test_ci_e2e_workflow.py
tests/test_prepare_ci_e2e_artifacts_reimport.py
tests/test_telemetry_e2e_harness.py
tests/test_telemetry_threshold_delivery.py
```

Проверяются:

- schema и deterministic JSON;
- lifecycle success/failure;
- registry parity;
- security rejection;
- message/line bounds;
- concurrent append;
- Fast CI integration;
- Docker phase wiring;
- manifest requirement;
- public exporter double validation;
- Compose CI mode;
- transient sidecar exclusion;
- wrapper repeated-import compatibility;
- telemetry threshold delivery после consent transition.

Финальный Fast CI подтвердил:

```text
Vitest: 69 files, 342 tests — PASS
pytest: 902 passed, 2 skipped — PASS
package build/check — PASS
exact package metadata/check — PASS
```

## Обнаруженные проблемы и исправления

Этап намеренно проходил через реальные cloud gates. Несколько последовательных failures выявили не только ошибки новой observability integration, но и существующую production telemetry race.

| Run | Контур | Результат | Подтверждённая причина | Исправление |
| ---: | --- | --- | --- | --- |
| `30033549308` | Fast CI | FAIL | exporter wrapper перестал сохранять прежний API и unit compatibility | восстановлен public API wrapper-а без ослабления production validation |
| `30034579297` | Fast CI | FAIL | повторный импорт wrapper-а накапливал цепочку monkeypatch wrappers и терял mocked `utc_now` | idempotent import, временная подмена через `try/finally`, regression test |
| `30036551037` | E2E handoff | FAIL до Docker | Fast CI summary включал временные `run-events.jsonl.lock` и `.state.json`, которых уже не было в artifact | transient sidecars исключены из `artifactFiles`, strict validator сохранён |
| `30037712580` | real-Anki E2E | FAIL в browser smoke | consent transition запускал пустой sender; первые feature events частично отправлялись, остаток блокировался periodic throttle | пустой sender не запускается; threshold delivery использует `force=True`; добавлен exact regression test |
| `30039103625` | Fast CI | PASS | final package-producing proof | exact package и diagnostics опубликованы |
| `30039372012` | standard/full E2E | PASS | первый real-Anki proof после telemetry fix | подтверждены package, runtime, browser, restart, telemetry и artifact contracts |
| `30039708429` | standard/full E2E | PASS | независимый финальный full proof | подтверждена воспроизводимость завершённого stage contour |

## Production telemetry race

Финальный E2E до исправления показал:

```text
reliabilityDiagnostics delivered: 25
featureUsage delivered: 3 из 25 ожидаемых
остаток очереди: ниже threshold
periodic throttle: блокировал новый sender
```

Причина:

1. после изменения consent запускался sender даже при пустой очереди;
2. sender успевал забрать первые несколько новых events;
3. оставшееся количество становилось меньше `QUEUE_SEND_THRESHOLD = 25`;
4. обычный threshold send использовал `force=False` и блокировался 15-минутным periodic interval.

Исправление в `anki_study_report/telemetry_client.py`:

- consent change запускает forced sender только при непустой очереди;
- threshold send использует `request_send(force=True)`;
- existing active worker по-прежнему coalesces follow-up request;
- deletion semantics не изменены.

Regression test проверяет две полные партии по 25 events и отсутствие пустого sender при consent transition.

## Финальный Fast CI proof

```text
Run ID: 30039103625
Result: PASS
Branch: platform/e2e-observability-roadmap
Tested commit: a376a1e5556b26043d29fadcf01698972bd1b2ba
Run attempt: 1
Structured duration: 143453 ms
Run events: 34
Statuses: 17 START, 17 PASS
Final event: run/pass
```

Крупнейшие внутренние фазы:

| Фаза | Длительность |
| --- | ---: |
| `python-pytest` | 60 375 ms |
| `frontend-vitest` | 40 563 ms |
| `frontend-typecheck-tests` | 12 172 ms |
| `frontend-vite-build` | 9 703 ms |
| `install-python-dependencies` | 6 375 ms |

Diagnostics artifact:

```text
ID: 8576563207
Name: ci-fast-30039103625-1
Digest: sha256:b46f9ef654a46d19a5108f0dbd9007c797e0d4240517224f9cf35a213fc31933
```

Exact package artifact:

```text
ID: 8576563986
Name: ci-package-a376a1e5556b26043d29fadcf01698972bd1b2ba-30039103625-1
Artifact digest: sha256:7fb10ce94de2985efcf489de077ddc8de06ad3464673b337db3e73378ebd111e
Inner .ankiaddon SHA-256: 9ac537e77ed32fb1dd65f79d5e84084a1b4f0e301c0215d9d5b61b8bf2d99fbf
Package size: 750680 bytes
```

Artifact transport digest и SHA-256 внутреннего `.ankiaddon` являются разными identities и проверяются отдельно.

## Первый real-Anki proof

```text
Run ID: 30039372012
Job: Real Anki Desktop (standard / full)
Result: PASS
Mode: standard
Scope: full
Screenshot workers: 3
Resource telemetry: enabled
Restart: completed
Fast CI source run: 30039103625
Package tested SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
E2E checkout SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Package source: fast-ci-artifact
Package reuse: exact tree
Workflow duration: 138 s
Canonical E2E duration: 82667 ms
Run events: 34
Statuses: 17 START, 17 PASS
Final event: run/pass
Screenshots: 18
```

E2E artifact:

```text
ID: 8576643972
Name: ci-e2e-standard-30039372012-1
Size: 6805336 bytes
Digest: sha256:1912fb35952af1463fa6b833229f27c797d9f34a97f7bd48d3e8be3efaafb091
```

Ключевые фазы:

| Фаза | Длительность |
| --- | ---: |
| browser real-deck and dashboard capture | 32 204 ms |
| telemetry restart persistence and deletion | 28 059 ms |
| first readiness wait | 4 154 ms |
| restart readiness | 4 151 ms |
| Anki stop and restart | 3 866 ms |

GHCR environment:

```text
Image digest: sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
Platform: linux/amd64
Environment contract SHA-256: sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
Cache state: ghcr-digest
```

## Финальный независимый full proof

```text
Run ID: 30039708429
Job: Real Anki Desktop (standard / full)
Result: PASS
Mode: standard
Scope: full
Screenshot workers: 3
Resource telemetry: enabled
Restart: completed
Fast CI source run: 30039103625
Package tested SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
E2E checkout SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Package source: fast-ci-artifact
Package reuse: exact tree
Workflow duration: 195 s
Canonical E2E duration: 115693 ms
Run events: 34
Statuses: 17 START, 17 PASS
Final event: run/pass
Screenshots: 18
```

E2E artifact:

```text
ID: 8576802933
Name: ci-e2e-standard-30039708429-1
Size: 6823182 bytes
Digest: sha256:0931e91580f48f951797b71729cab4673a6b23e6b3f3bf0e422c84c701663368
```

Ключевые фазы:

| Фаза | Длительность |
| --- | ---: |
| telemetry restart persistence and deletion | 61 970 ms |
| browser real-deck and dashboard capture | 32 602 ms |
| restart readiness | 4 148 ms |
| first readiness wait | 4 153 ms |
| Anki stop and restart | 2 797 ms |

Разница длительности между двумя full runs относится преимущественно к telemetry restart и GHCR pull/validation. Timing остаётся informational; blocking performance threshold в `E2E-I1` не вводился.

## Browser evidence

Оба successful E2E artifacts содержат 18 screenshots:

```text
10 page screenshots:
  home light/dark
  cards light/dark
  decks light/dark
  profile light/dark
  settings light/dark

6 native real-deck previews:
  words light/dark
  grammar light/dark
  java light/dark

2 Cards state screenshots:
  real-deck-inbox light/dark
```

Browser reports подтвердили:

```text
ok: true
pageErrors: 0
failedRequests: 0
unexpectedExternalRequests: 0
```

## Telemetry evidence после исправления

В обоих финальных E2E runs:

```text
total events: 179
reliabilityDiagnostics: 25
featureUsage: 154
pending events after restart: 129
delivered after restart: 129
restartPersistence: true
confirmedDeletion: true
credentialDestroyed: true
lastDeliveryErrorCode: null
```

Это подтверждает, что исправление не просто устранило timeout, а сохранило:

- purpose isolation;
- threshold delivery;
- offline persistence;
- restart delivery;
- confirmed deletion;
- credential destruction.

## Artifact evidence

Успешные E2E artifacts содержат:

- validated `artifact-manifest.json` schema v2;
- exact `.ankiaddon`;
- `run-events.jsonl`;
- phase timings;
- performance summary;
- resource samples/summary;
- Fast CI handoff evidence;
- GHCR provenance;
- real-deck manifest/import/inventory/anchors/scenarios;
- API first/restart reports;
- browser report;
- telemetry fake/restart reports;
- runtime events;
- 18 screenshots;
- redacted readiness;
- Docker/Anki diagnostics.

Success manifest требует `reports/run-events.jsonl`. Public exporter валидирует source и public copy.

## Выполнение completion criteria

| Критерий `E2E-I1` | Результат | Evidence |
| --- | --- | --- |
| Общий schema-versioned event contract | PASS | `run_event_protocol.py`, schema v1 docs/tests |
| Immediate console output | PASS | `[FAST]` и `[E2E]` lifecycle в cloud runs |
| Structured JSONL evidence | PASS | Fast CI и два E2E artifacts |
| Stable phase IDs | PASS | registry parity и integration tests |
| Success stream | PASS | 34 events, `run/pass` во всех финальных runs |
| Controlled failure stream | PASS | focused controlled-failure test |
| Unknown/unsafe value rejection | PASS | schema/security tests |
| Cross-process append | PASS | 24 writers, zero corruption |
| Deterministic Compose output | PASS | CI env + `--ansi never --progress plain --no-TTY` |
| Existing timing/raw diagnostics preserved | PASS | timing/resource/raw files присутствуют |
| Manifest/public artifact integration | PASS | required report + double validation |
| Package/security/real-deck semantics unchanged | PASS | exact handoff и два full real-Anki E2E |
| Owner acceptance evidence | PASS | пользователь предоставил и подтвердил три successful runs |

## Изменённые production/orchestration файлы

```text
.github/workflows/ci-fast.yml
anki_study_report/telemetry_client.py
docker/anki-e2e/run-e2e.sh
docker/anki-e2e/run_event_protocol.py
docker/anki-e2e/write-artifact-manifest.py
scripts/ci_fast_timing.py
scripts/prepare_ci_e2e_artifacts.py
scripts/run_anki_e2e_docker.ps1
scripts/verify_fast_ci_e2e_handoff.py
scripts/write_ci_fast_summary.ps1
```

Продуктовый dashboard payload, frontend API types, collection access boundary и release publication не изменялись.

## Состояние репозитория после этапа

На момент implementation closeout ветка:

```text
platform/e2e-observability-roadmap
```

находилась впереди `core` и не отставала от merge base. PR в `core` не создавался по прямому указанию владельца. Merge, auto-merge, tag и release не выполнялись.

Документационные commits после successful gates являются docs-only и не требуют нового Fast CI/Docker run без отдельной причины согласно verification policy.

## Остаточные риски и ограничения

1. `browser-smoke-first` остаётся одной крупной фазой; item-level route/theme/preview progress относится к `E2E-I2`.
2. `failureCode` ещё не содержит stable taxonomy; это `E2E-I3`.
3. Run-event stream не является единственным итоговым summary; canonical aggregation относится к `E2E-I6`.
4. Timing/resource values остаются informational и не являются performance gate.
5. Windows/PowerShell local parity подтверждается unit/workflow contract и Fast CI, но отдельный ручной local owner run не зафиксирован как обязательный gate.
6. GitHub artifact retention ограничен workflow policy; данный отчёт сохраняет identities/digests, но не включает runtime ZIP в repository.
7. Production telemetry race исправлен в рамках stage closure, однако этот fix изменил package bytes и поэтому потребовал новый package-producing Fast CI — что было выполнено.

Ни один из этих пунктов не блокирует завершение `E2E-I1`.

## Решение о завершении

```text
E2E-I1: COMPLETE
```

Основания:

- implementation завершена;
- актуальный контракт документирован;
- focused success/failure/security/concurrency tests присутствуют;
- package-producing Fast CI прошёл;
- exact package identity подтверждена;
- два независимых `standard/full` real-Anki E2E прошли;
- оба public artifacts валидны;
- telemetry race устранён и подтверждён;
- roadmap boundary `E2E-I2` не нарушена;
- PR/merge/release не выполнялись.

## Следующий допустимый шаг

Следующий отдельный platform stage:

```text
E2E-I2 — Browser smoke progress
```

Он должен начинаться как отдельная bounded задача и не должен переоткрывать `E2E-I1`, если не обнаружена конкретная регрессия его schema/security/artifact contract.
