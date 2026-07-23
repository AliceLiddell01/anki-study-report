# Docker real-Anki E2E

**Снимок документации:** 2026-07-24.

Этот контур запускает exact add-on package в реальном Anki Desktop 26.05 внутри Docker, поднимает loopback token-protected dashboard и проверяет API, browser behavior, native rendering, media, notifications, telemetry, restart, live run lifecycle и публично безопасные artifacts.

Полный Docker E2E — integration gate.

Связанные контракты:

- политика запусков: [`../../docs/verification-run-policy.md`](../../docs/verification-run-policy.md);
- package/harness reuse: [`../../docs/e2e-package-harness-reuse.md`](../../docs/e2e-package-harness-reuse.md);
- единый live-протокол: [`../../docs/run-event-protocol.md`](../../docs/run-event-protocol.md).

## Collection source

Disposable collection содержит только данные из:

```text
fixtures/real-decks/words-n1.apkg
fixtures/real-decks/grammar-n5.apkg
fixtures/real-decks/java-core.apkg
```

Manifest:

```text
fixtures/real-decks/manifest.json
```

Запрещены:

- synthetic notes/cards/note types/templates/media;
- `asr-e2e-render-fixtures.apkg` как runtime source;
- external/local-only APKG override;
- fallback collection;
- legacy importer/backend fallback;
- cloning notes/cards;
- concrete fixture identifiers вне manifest.

## Pipeline

1. Использовать current E2E harness checkout.
2. Для local `source-build` собрать frontend/package; для cloud установить exact prebuilt package.
3. Инициализировать live stream через `run/start`.
4. Создать fresh disposable profile и empty collection.
5. Валидировать manifest, sizes и SHA-256.
6. Импортировать три packages через `Collection.import_anki_package(ImportAnkiPackageRequest)`.
7. Построить inventory и доказать zero synthetic content.
8. Разрешить anchors по GUID/template ordinal.
9. Проверить fingerprints, fields, media capabilities и HTML classes.
10. Применить только scheduling/revlog/due/interval/ease/suspended/buried scenarios.
11. Установить add-on.
12. Для `full/notifications` seed notification state из real-deck anchors.
13. Запустить Anki и дождаться readiness.
14. Выполнить API и browser smoke.
15. Подготовить offline telemetry queue.
16. При необходимости выполнить restart и persistence proof.
17. Проверить package SHA после E2E.
18. Сформировать artifact manifest.
19. Завершить и валидировать `run-events.jsonl`.
20. Создать redacted public artifact.
21. Cleanup и restore canonical exit code.

Thin adapters:

```text
seed-collection.py                  empty collection only
import-apkg-fixture.py              mandatory manifest-driven import
mark-apkg-cards-problematic.py      generic study-state scenarios only
```

## Единый live-протокол

Основная реализация:

```text
run_event_protocol.py
```

Raw stream:

```text
reports/run-events.jsonl
```

Public stream:

```text
artifacts/reports/run-events.jsonl
```

Console output:

```text
[00:10.112] [E2E] [browser-smoke-first] START
[00:42.316] [E2E] [browser-smoke-first] PASS duration=32204ms
```

В `run-e2e.sh` каждая крупная операция использует:

```text
phase_start <phase-id> <telemetry-name>
phase_end <success|failed|skipped>
```

`phase_start` сначала публикует live event, затем запускается команда. `phase_end` сохраняет прежний phase timing и terminal run event.

Если shell command падает:

1. active phase закрывается как FAIL;
2. прежний telemetry phase фиксирует failure;
3. cleanup останавливает Anki и helpers;
4. manifest создаётся, когда это безопасно;
5. stream завершается через `run/fail`;
6. canonical exit code сохраняется.

`run-events.jsonl` не заменяет raw logs или stack traces.

## Registry Docker E2E schema v1

```text
run
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

`browser-smoke-first` остаётся одной крупной phase. Item-level route/theme/preview progress относится к `E2E-I2`.

## Live logging real-deck helpers

Длительные real-deck стадии дополнительно используют prefix:

```text
[real-decks]
```

Ожидаются сообщения о manifest/checksum/import/inventory/anchors/scenarios/browser result.

При ошибке `real-deck-failure.json` содержит stage, subject ID, error type/message, last completed step и traceback. Fallback не выполняется.

Live run protocol использует только bounded public-safe messages и не копирует raw traceback в JSONL.

## Package sources

### Local `source-build`

```powershell
./scripts/run_anki_e2e_docker.ps1
./scripts/run_full_check.ps1 -DockerOnly
```

Контейнер использует prepared dependency store, собирает dashboard и package.

Фазы:

```text
frontend-dependency-install
frontend-build
addon-package
```

### Cloud `fast-ci-artifact`

Manual/reusable workflow получает `fast_ci_run_id` и exact package.

Package commit и current harness commit могут различаться. Reuse допускается только после ancestry + complete changed-path allowlist validation.

Изменение только allowlisted E2E harness не требует нового Fast CI.

Фаза:

```text
exact-package-validation
```

### `release-artifact`

Release caller передаёт exact current release archive и SHA-256. Это отдельный production proof.

## Local commands

```powershell
./scripts/run_anki_e2e_docker.ps1
./scripts/run_full_check.ps1 -DockerOnly
./scripts/run_full_check.ps1 -DockerOnly -CleanDocker
./scripts/run_anki_e2e_docker.ps1 -BuildOnly
./scripts/run_anki_e2e_docker.ps1 -NoBuild
./scripts/run_full_check.ps1 -DockerOnly -Perf100
```

WSL:

```bash
pwsh -NoProfile -File ./scripts/run_anki_e2e_docker.ps1
```

## Cloud command

```bash
gh workflow run ci-e2e.yml \
  --repo AliceLiddell01/anki-study-report \
  --ref <branch> \
  -f mode=standard \
  -f scope=<scope> \
  -f screenshot_workers=auto \
  -f resource_telemetry=true \
  -f verify_restart=<auto|true|false> \
  -f fast_ci_run_id=<successful-package-producing-run>
```

## Modes

```text
standard
perf100
```

`perf100` выбирает 100 distinct imported cards и не клонирует content.

Legacy `strict-apkg` input нормализуется в `standard`.

## Scopes

```text
full
global
stats
decks
activity
cards
settings
notifications
```

Scope не отключает imports/checksums/inventory/anchors/scenarios.

`full` автоматически требует restart.

## Required reports

```text
reports/real-deck-manifest-report.json
reports/real-deck-import-report.json
reports/collection-inventory.json
reports/anchor-resolution-report.json
reports/scenario-application-report.json
reports/api-smoke-first.json
reports/browser-smoke-first.json
reports/run-events.jsonl
reports/e2e-phase-timings.json
reports/e2e-performance-summary.json
```

При restart дополнительно создаются restart API/telemetry reports.

Успешный artifact manifest обязан индексировать `reports/run-events.jsonl`. Missing/invalid stream является hard failure.

## Inventory and scenario invariants

```text
contentSource = committed-real-apkg-only
syntheticNotes = 0
syntheticCards = 0
syntheticMedia = 0
notesCreated = 0
cardsCreated = 0
notesOrCardsCloned = 0
```

## Browser evidence

```text
screenshots/pages/<route>/<light|dark>.png
screenshots/cards/real-decks/<preview>/<light|dark>.png
screenshots/states/cards/real-deck-inbox/<light|dark>.png
```

Проверяются native front/back, real media, Java class contour, Cards states, no page/console/request errors и no unexpected external network.

## Notifications

`seed-notification-lifecycle.py` использует PASS reports:

```text
anchor-resolution-report.json
scenario-application-report.json
```

Card anchors:

```text
cards-action-recheck
cards-low-success
```

Public proof schema v2 не содержит raw entity IDs.

## Telemetry

Browser harness проверяет consent/purpose batches, затем создаёт offline persistent queue. Restart verifier проверяет восстановление, delivery, deletion и credential destruction.

Исправленный sender contract:

- пустой consent transition не запускает sender;
- existing queue запускает forced send;
- threshold `25` запускает `request_send(force=True)`;
- periodic interval не блокирует threshold delivery;
- active sender coalesces follow-up request;
- deletion contract не изменён.

Regression test:

```text
tests/test_telemetry_threshold_delivery.py
```

## Package/harness reuse reports

```text
ci-e2e-raw/e2e-harness-reuse.json
artifacts/reports/e2e-harness-reuse.json
```

Evidence содержит package commit, harness/workflow commit, reuse mode, count/hash/list changed paths.

## Compose output в CI

При `CI=true` или `GITHUB_ACTIONS=true` PowerShell wrapper задаёт:

```text
COMPOSE_ANSI=never
COMPOSE_PROGRESS=plain
COMPOSE_MENU=0
COMPOSE_STATUS_STDOUT=1
```

Run invocation:

```text
docker compose --ansi never --progress plain run --no-TTY ...
```

Local interactive output сохраняется без CI mode.

## Security

- loopback-only dashboard;
- token не логируется;
- raw readiness не публикуется;
- read-only workspace/package mounts;
- media traversal/absolute path rejection;
- no iframe/JS card execution;
- private absolute path redaction;
- safe relative path preservation;
- secret/private-key rejection;
- run-event schema/security validation;
- source и public JSONL проверяются отдельно;
- runtime outputs не коммитятся.

## Failure contract

Hard failure при package/import/anchor/fingerprint/content mutation, package reuse boundary, package hash, API/browser/restart/notification/telemetry, run-event stream, artifact manifest или sanitizer error.

Public artifact загружается даже после failure, когда это безопасно, но canonical result восстанавливается после upload/cleanup.

Финальный wrapper step `Restore canonical result` не является автоматически root cause: он только возвращает сохранённый результат предыдущего функционального contour.

## Updating working decks

1. Заменить только нужный `.apkg`.
2. Проверить provenance/authorization.
3. Пересчитать size/SHA-256.
4. Получить inventory.
5. Проверить anchors/fingerprints/media.
6. Обновить manifest.
7. Выполнить focused tests.
8. Выполнить policy-compliant real-Anki proof.

Не менять generic harness ради конкретного слова/media filename. Identifiers хранятся в manifest.

## Подтверждённый closeout E2E-I1

```text
Implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Fast CI package run: 30039103625 — PASS
First standard/full: 30039372012 — PASS
Final standard/full: 30039708429 — PASS
Package SHA-256: 9ac537e77ed32fb1dd65f79d5e84084a1b4f0e301c0215d9d5b61b8bf2d99fbf
```

Оба E2E runs:

```text
run events: 34
START: 17
PASS: 17
final: run/pass
screenshots: 18
telemetry restart/deletion: PASS
```

Отчёты:

- [`../../reports/ci/real-deck-e2e-foundation-closeout.md`](../../reports/ci/real-deck-e2e-foundation-closeout.md);
- [`../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md).
