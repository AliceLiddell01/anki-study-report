# Единый протокол событий выполнения

**Статус:** реализованный контракт `E2E-I1`, schema v1  
**Производители:** `fast-ci`, `docker-e2e`  
**Дата подтверждения:** 2026-07-24

## Назначение

Fast CI и real-Anki Docker E2E публикуют один и тот же жизненный цикл выполнения в двух представлениях:

1. немедленная стабильная строка в консоли;
2. одна детерминированная JSON-запись на строку в `run-events.jsonl`.

Протокол решает две задачи:

- длительная операция больше не выглядит зависшей: начало и завершение каждой крупной фазы видны сразу;
- итоговый artifact содержит машинно проверяемое доказательство последовательности фаз, статусов и длительностей.

`run-events.jsonl` дополняет существующие Fast CI timing, E2E phase/resource telemetry, raw logs, screenshots и artifact manifest. Он не заменяет их и не является внешней logging-системой.

## Границы этапа

В `E2E-I1` реализованы только события уровня run/phase и безопасные informational messages.

Не входят в этот контракт:

- item-level прогресс маршрутов, тем и native previews внутри browser smoke — это `E2E-I2`;
- стабильная таксономия failure codes и primary/secondary failure summary — это `E2E-I3`;
- отдельный preflight/cancellation contract — это `E2E-I4`;
- non-release build identity — это `E2E-I5`;
- единый финальный summary и история производительности — это `E2E-I6`.

Поэтому `failureCode` в schema v1 зарезервирован, но в `E2E-I1` всегда равен `null`.

## Поток данных

```text
Fast CI command / Docker phase
→ schema-validated event
→ стабильная console line
→ append-only JSONL
→ финальная validation
→ diagnostics/public artifact
```

Основная реализация:

```text
docker/anki-e2e/run_event_protocol.py
```

Интеграционные точки:

```text
.github/workflows/ci-fast.yml
scripts/ci_fast_timing.py
scripts/write_ci_fast_summary.ps1
docker/anki-e2e/run-e2e.sh
docker/anki-e2e/write-artifact-manifest.py
scripts/run_anki_e2e_docker.ps1
scripts/prepare_ci_e2e_artifacts.py
```

## Пути evidence

```text
Fast CI:
  ci-fast/run-events.jsonl

Raw Docker E2E:
  reports/run-events.jsonl

Публичный E2E artifact:
  artifacts/reports/run-events.jsonl
```

Fast CI stream входит в обычный diagnostics artifact `ci-fast-<run-id>-<attempt>`.

Docker stream находится внутри `reports/`, поэтому автоматически индексируется artifact manifest. Успешный manifest обязан содержать `reports/run-events.jsonl`.

Public artifact exporter:

1. валидирует исходный Docker stream до копирования;
2. копирует его через существующую redaction/allowlist boundary;
3. повторно валидирует публичную копию;
4. при успешном E2E отклоняет отсутствие stream fail closed.

## Schema v1

Каждая строка содержит ровно следующие поля и именно в таком порядке:

```json
{"schemaVersion":1,"timestampUtc":"2026-07-24T00:00:00.000Z","elapsedMs":0,"producer":"fast-ci","phaseId":"run","eventKind":"run","status":"start","durationMs":null,"current":null,"total":null,"message":"pipeline=canonical","failureCode":null}
```

| Поле | Контракт |
| --- | --- |
| `schemaVersion` | integer `1` |
| `timestampUtc` | UTC ISO-8601 с миллисекундами и завершающим `Z` |
| `elapsedMs` | неотрицательное целое число от инициализации run |
| `producer` | `fast-ci` или `docker-e2e` |
| `phaseId` | стабильный ID из registry соответствующего producer |
| `eventKind` | `run`, `phase` или `message` |
| `status` | закрытое значение lifecycle |
| `durationMs` | неотрицательная длительность завершённого события либо `null` |
| `current`, `total` | парные bounded progress counters либо оба `null` |
| `message` | необязательная public-safe однострочная UTF-8 строка, максимум 512 bytes |
| `failureCode` | зарезервирован для `E2E-I3`, в schema v1 этапа `E2E-I1` равен `null` |

### Lifecycle values

```text
run:
  start | pass | fail | cancel

phase:
  start | pass | fail | skip | cancel

message:
  info
```

### Семантика завершённого stream

Финализированный stream обязан:

- начинаться ровно одним `run/start`;
- содержать только одного producer;
- использовать только зарегистрированные phase IDs;
- иметь неубывающий `elapsedMs`;
- заканчиваться ровно одним `run/pass`, `run/fail` или `run/cancel`;
- не содержать событий после финального run result;
- быть UTF-8 без BOM;
- завершать каждую запись символом `\n`;
- использовать compact deterministic JSON без произвольных пробелов и перестановки полей.

## Консольное представление

Пример Docker E2E:

```text
[00:37.842] [E2E] [browser-smoke-first] START
[01:10.995] [E2E] [browser-smoke-first] PASS duration=33153ms
```

Пример Fast CI:

```text
[00:12.040] [FAST] [frontend-vitest] START
[00:52.603] [FAST] [frontend-vitest] PASS duration=40563ms
```

Правила:

- Fast CI использует domain marker `[FAST]`;
- Docker E2E использует `[E2E]`;
- ANSI-цвет не является частью контракта;
- status печатается в верхнем регистре;
- duration добавляется только к завершённому событию;
- progress печатается как `[current/total]`, когда оба значения заданы;
- message добавляется только после schema/security validation;
- строка никогда не может начинаться с `::`, чтобы не превращаться в случайную GitHub workflow command.

## Гарантии безопасности

Validator отклоняет:

- неизвестные `schemaVersion`, producer, event kind, status и phase ID;
- отрицательные или логически несовместимые timing/progress values;
- `current` без `total`, `total` без `current`, `current > total` или `total = 0`;
- control characters, multiline values, tab и NUL;
- сообщения длиннее 512 UTF-8 bytes;
- строки события длиннее 2048 UTF-8 bytes;
- token-bearing URLs;
- `Authorization: Bearer ...`;
- common GitHub/OpenAI-style secret forms и private-key markers;
- Windows absolute paths, UNC paths и private Linux absolute paths;
- BOM, partial line, malformed JSON и non-deterministic serialization;
- непредусмотренный `failureCode` до `E2E-I3`.

Протокол не разрешает логировать dashboard token, полный token-bearing URL, private profile path, credentials или collection data.

## Гарантии append

Writer использует:

- cross-platform exclusive lock;
- append-only UTF-8 запись;
- один завершённый JSON object на одну запись;
- `fsync` после append;
- отдельный runtime state sidecar;
- неубывающий `elapsedMs`, даже если несколько короткоживущих процессов пишут одновременно.

Windows использует `msvcrt.locking`, Linux — `fcntl.flock`.

Transient sidecars:

```text
run-events.jsonl.lock
run-events.jsonl.state.json
```

Они не являются evidence, удаляются после финализации и не включаются в Fast CI `artifactFiles`.

## Registry Fast CI

Источник истины для Fast CI phase metadata:

```text
scripts/ci_fast_timing.py
```

Registry timing и registry run events проверяются на равенство при импорте. Рассинхронизация является hard failure.

Schema v1 допускает следующие IDs:

```text
run
install-python-dependencies
install-frontend-dependencies
changelog-check
frontend-typecheck-tests
frontend-vitest
frontend-typecheck-build
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

Не каждая допустимая фаза обязана выполняться в каждом run: фактический набор определяется canonical Fast CI pipeline.

## Registry Docker E2E

Schema v1 допускает:

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

`frontend-dependency-install`, `frontend-build` и `addon-package` относятся к local `source-build`. Cloud E2E с exact prebuilt package использует `exact-package-validation`.

`browser-smoke-first` намеренно остаётся одной крупной фазой. Детализация routes/themes/previews должна добавляться только в `E2E-I2`, не через новые вложенные roadmap-этапы.

## Интеграция с Fast CI timing

`scripts/ci_fast_timing.py` остаётся каноническим источником structured timing и одновременно публикует run events.

Соответствие статусов:

```text
Fast CI timing success  → run-event pass
Fast CI timing failure  → run-event fail
Fast CI skipped         → run-event skip
Fast CI cancelled       → run-event cancel
```

CLI сохраняет прежний API:

```text
initialize
start
finish
finalize
validate
render
```

При `finalize` незавершённая timing-фаза закрывается как failure и получает соответствующее `phase/fail` событие. После этого публикуется финальный run result и выполняется полная validation stream.

## Интеграция с Docker E2E

`docker/anki-e2e/run-e2e.sh` использует пары:

```text
phase_start <phase-id> <telemetry-name>
phase_end <success|failed|skipped>
```

Run-event protocol и прежний `e2e-telemetry.py` работают параллельно:

- run events отвечают за единый live lifecycle и machine-readable JSONL;
- phase/resource telemetry сохраняет подробные timing/resource reports;
- raw logs сохраняют stack traces и низкоуровневую диагностику.

При shell failure cleanup:

1. закрывает активную фазу как `phase/fail`;
2. сохраняет прежний telemetry phase failure;
3. останавливает Anki и background helpers;
4. формирует manifest;
5. завершает stream через `run/fail`;
6. валидирует stream;
7. сохраняет исходный canonical exit status.

## Docker Compose output

В CI `scripts/run_anki_e2e_docker.ps1` устанавливает:

```text
COMPOSE_ANSI=never
COMPOSE_PROGRESS=plain
COMPOSE_MENU=0
COMPOSE_STATUS_STDOUT=1
```

И запускает Compose как:

```text
docker compose --ansi never --progress plain run --no-TTY ...
```

Это отключает интерактивное меню, TTY animation и ANSI-зависимое оформление в GitHub Actions. Локальный интерактивный вывод не меняется, пока процесс явно не работает в `CI`/`GITHUB_ACTIONS` либо пользователь самостоятельно не задаёт эти переменные.

## Validation CLI

Пример проверки завершённого Fast CI stream:

```bash
python docker/anki-e2e/run_event_protocol.py validate \
  --output ci-fast/run-events.jsonl \
  --producer fast-ci
```

Проверка Docker stream:

```bash
python docker/anki-e2e/run_event_protocol.py validate \
  --output reports/run-events.jsonl \
  --producer docker-e2e
```

Проверка ещё выполняющегося stream допускается только явно:

```bash
python docker/anki-e2e/run_event_protocol.py validate \
  --output reports/run-events.jsonl \
  --producer docker-e2e \
  --allow-running
```

## Правила расширения

При добавлении новой крупной фазы необходимо одновременно:

1. добавить стабильный kebab-case `phaseId` в registry нужного producer;
2. подключить `start` и terminal status в orchestration;
3. не передавать private/raw data через `message`;
4. добавить focused contract/integration test;
5. обновить этот документ;
6. при изменении публичного artifact contract обновить manifest/exporter tests;
7. не создавать новый roadmap substage только ради одной implementation-фазы.

Нельзя:

- динамически строить phase IDs из пользовательских данных;
- использовать console text как единственный источник истины;
- ослаблять validator для прохождения старого artifact;
- включать transient lock/state sidecars в evidence inventory;
- менять timing registry только на одной стороне;
- публиковать item-level browser details под видом завершения `E2E-I2`.

## Проверки контракта

Focused tests покрывают:

- schema и deterministic serialization;
- unknown status/kind/phase rejection;
- UTC/timing/progress bounds;
- message/line limits;
- token/path/secret/control-character rejection;
- success и controlled failure lifecycle;
- cross-process concurrent append без повреждённых строк;
- Fast CI timing/registry parity;
- Docker orchestration wiring;
- обязательность stream в success manifest;
- source/public stream validation в exporter;
- deterministic non-interactive Compose mode;
- отсутствие tracked generated JSONL;
- исключение transient sidecars из Fast CI inventory.

## Подтверждённая реализация

Контракт подтверждён на exact commit:

```text
a376a1e5556b26043d29fadcf01698972bd1b2ba
```

Проверочные runs:

```text
Fast CI:              30039103625 — PASS
первый standard/full: 30039372012 — PASS
финальный full:        30039708429 — PASS
```

Оба E2E runs сформировали валидный stream из 34 событий:

```text
17 START
17 PASS
финал: run/pass
```

Подробный исторический отчёт: [`../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md).
