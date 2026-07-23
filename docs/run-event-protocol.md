# Единый протокол событий выполнения

**Статус:** реализованный контракт `E2E-I1` + browser item integration `E2E-I2`  
**Schema:** global run-event schema v1  
**Производители:** `fast-ci`, `docker-e2e`  
**Дата подтверждения:** 2026-07-24

## Назначение

Fast CI и real-Anki Docker E2E публикуют жизненный цикл выполнения в двух согласованных представлениях:

1. немедленная стабильная строка в консоли;
2. детерминированная JSON-запись на строку в `run-events.jsonl`.

Протокол делает длительные операции наблюдаемыми и сохраняет машинно проверяемое evidence. Он дополняет, но не заменяет:

- Fast CI timing;
- Docker E2E phase timing;
- resource telemetry;
- browser report;
- screenshots;
- raw diagnostics;
- artifact manifest.

## Границы этапов

### E2E-I1

Реализованы:

- run lifecycle;
- stable phase lifecycle;
- informational messages;
- deterministic JSONL;
- cross-process append;
- security validation;
- artifact/public-export integration;
- plain non-interactive Compose output.

### E2E-I2

Сохранена global schema v1. Внутри одной фазы `browser-smoke-first` добавлен безопасный item-level прогресс через `message/info`:

- deterministic browser plan;
- `current/total`;
- item `START` / `PASS` / `FAIL`;
- route/theme/anchor/telemetry identity;
- per-item duration в bounded message;
- machine-readable browser report schema v2.

### Остаётся вне текущего контракта

- stable global `failureCode` taxonomy и общий failure summary — `E2E-I3`;
- cancellation/preflight redesign — `E2E-I4`;
- unique non-release build identity — `E2E-I5`;
- canonical final summary/history storage — `E2E-I6`.

## Файлы evidence

### Fast CI

```text
private/live: ci-fast/run-events.jsonl
artifact:     run-events.jsonl
```

### Docker E2E

```text
container/live: reports/run-events.jsonl
public:         artifacts/reports/run-events.jsonl
```

Transient sidecars:

```text
run-events.jsonl.lock
run-events.jsonl.state.json
```

являются runtime coordination state и не входят в final evidence inventory.

## Schema v1

Каждая JSONL-строка имеет фиксированную форму:

```json
{
  "schemaVersion": 1,
  "timestampUtc": "2026-07-23T22:16:53.608Z",
  "elapsedMs": 31603,
  "producer": "docker-e2e",
  "phaseId": "browser-smoke-first",
  "eventKind": "message",
  "status": "info",
  "durationMs": null,
  "current": 3,
  "total": 23,
  "message": "item=start id=route.home.light kind=route-capture",
  "failureCode": null
}
```

### Поля

| Поле | Тип | Назначение |
| --- | --- | --- |
| `schemaVersion` | integer | версия global schema; сейчас `1` |
| `timestampUtc` | string | UTC timestamp в ISO-8601 |
| `elapsedMs` | integer | неубывающее время от начала run |
| `producer` | enum | `fast-ci` или `docker-e2e` |
| `phaseId` | enum | stable ID из registry производителя |
| `eventKind` | enum | `run`, `phase`, `message` |
| `status` | enum | lifecycle status |
| `durationMs` | integer/null | длительность завершённого run/phase |
| `current` | integer/null | bounded progress position |
| `total` | integer/null | bounded progress total |
| `message` | string/null | безопасное краткое пояснение |
| `failureCode` | null | зарезервировано для `E2E-I3` |

## Lifecycle

### Run

```text
run/start
...
run/pass | run/fail | run/cancel
```

Finalized stream содержит ровно один terminal run event и заканчивается им.

### Phase

```text
phase/start
phase/pass | phase/fail | phase/skip | phase/cancel
```

Phase IDs заранее перечислены в registry. Dynamic phase IDs запрещены.

### Message

```text
eventKind=message
status=info
durationMs=null
```

Message не является отдельной глобальной фазой. Он используется для bounded progress внутри существующей phase.

## Stable registries

`docker/anki-e2e/run_event_protocol.py` хранит:

```text
FAST_CI_PHASES
DOCKER_E2E_PHASES
```

Fast CI timing registry и run-event registry должны совпадать fail closed.

Для Docker E2E сохраняются крупные orchestration phases, включая:

```text
exact-package-validation
profile-bootstrap
empty-collection-bootstrap
real-deck-import
scenario-preparation
anki-start-first
readiness-first
api-smoke-first
browser-smoke-first
restart
readiness-restart
api-smoke-restart
telemetry-restart
manifest
```

Наличие `browser-smoke-first` одной общей phase является сознательным контрактом `E2E-I2`.

## Console format

Общий producer выводит строки вида:

```text
[00:12.731] [E2E] [browser-smoke-first] INFO [3/23] item=start id=route.home.light kind=route-capture
```

Browser entrypoint дополнительно выводит читаемый presentation-layer:

```text
[BROWSER] PLAN items=23 screenshots=18 telemetry=true
[BROWSER] [3/23] START route-capture item=route.home.light route=#/home theme=light
[BROWSER] [3/23] PASS route-capture item=route.home.light duration=1566ms screenshots=1
```

Presentation lines не заменяют structured evidence.

## Browser item integration

### Plan

`docker/anki-e2e/browser-progress.mjs` строит plan до `chromium.launch()`:

```text
schemaVersion
label
mode
scope
telemetryEnabled
expectedScreenshotCount
itemCount
countsByKind
items[]
```

Фактический `standard/cards` plan:

```text
items: 23
screenshots: 18
route-capture: 10
telemetry: 4
native-preview: 3
cards-route: 2
```

### Stable item IDs

Примеры:

```text
browser.launch
dashboard.setup
route.home.light
route.cards.dark
telemetry.reliability
telemetry.feature
preview.words-preview
scenario.cards
cards-route.light
diagnostics.final
```

Item IDs:

- deterministic;
- bounded;
- не содержат token, URL, filesystem path или user-controlled values;
- не регистрируются как global phase IDs.

### Browser message grammar

```text
item=start id=<id> kind=<kind>
item=pass id=<id> kind=<kind> durationMs=<n> screenshots=<n>
item=fail id=<id> kind=<kind> durationMs=<n> errorType=<bounded-type>
item=info id=<id> milestone=<bounded-marker>
```

`message` ограничен global validator. Raw stack и arbitrary exception message в stream не публикуются.

### Node → Python adapter

Browser adapter:

- использует `execFile`;
- не использует shell interpolation;
- передаёт аргументы отдельными array elements;
- вызывает общий `run_event_protocol.py`;
- ждёт producer completion;
- рассматривает non-zero exit как hard failure.

JavaScript не дублирует Python schema/security validator.

## Browser report schema v2

`reports/browser-smoke-<label>.json` сохраняет прежние diagnostics и добавляет:

```json
{
  "schemaVersion": 2,
  "ok": true,
  "plan": {
    "schemaVersion": 1,
    "itemCount": 23,
    "expectedScreenshotCount": 18,
    "countsByKind": {}
  },
  "progress": {
    "completed": 23,
    "total": 23,
    "failedItemId": null,
    "activeItemId": null,
    "expectedScreenshotCount": 18,
    "actualScreenshotCount": 18
  },
  "items": [],
  "slowestItems": []
}
```

Каждый item record содержит:

```text
id
kind
status
order
durationMs
expectedScreenshots
actualScreenshots
screenshotPaths
route/theme/anchorId/step — только когда применимо
errorType/safeErrorSummary — только при failure
```

## Screenshot accounting

Browser smoke работает fail closed:

```text
sum(plan.items.expectedScreenshots)
= plan.expectedScreenshotCount
= screenshots.length
= 18
```

Каждый item отдельно проверяет screenshot delta.

Сохраняются независимые wrapper guards:

```text
10 route screenshots
6 native real-deck preview screenshots
2 Cards state screenshots
0 synthetic screenshots
```

## Determinism

Требования к JSONL:

- UTF-8 без BOM;
- ровно одна JSON object на строку;
- newline terminator;
- deterministic key order/serialization;
- bounded line size;
- неубывающий `elapsedMs`;
- один producer на stream;
- один final run event.

Browser plan:

- строится из constant route/theme/anchor/kind registries;
- имеет unique IDs и последовательный `order`;
- `countsByKind` пересчитывается из `items`;
- screenshot total пересчитывается из `items`.

## Cross-process append

Python producer:

- использует platform-specific exclusive lock;
- пишет через append descriptor;
- выполняет `fsync`;
- корректирует elapsed time только вверх;
- удаляет sidecars после finalization.

Focused test проверяет 24 concurrent writers без corruption.

## Security и privacy

Запрещено публиковать в progress/evidence:

- dashboard token;
- token-bearing URL;
- Authorization headers;
- telemetry credential;
- absolute private path;
- environment dump;
- collection/profile content;
- card HTML;
- arbitrary raw stack в run-event message.

Разрешены:

- stable phase/item IDs;
- known route ID;
- theme;
- known anchor ID;
- known telemetry step;
- duration;
- screenshot count;
- safe relative screenshot path;
- bounded error type/summary в browser report.

Public exporter валидирует source stream и скопированный public stream. Artifact text проходит current token/private-path/secret sanitizer.

## Diagnostics semantics

`E2E-I2` не меняет Playwright diagnostics:

```text
consoleEvents
pageErrors
failedRequests
unexpectedExternalRequests
```

`requestfailed` означает network-level failure. HTTP 4xx/5xx response сам по себе не попадает в него. Favicon failure фильтруется прежним guard. Console failure проверяет `type === "error"`.

## Validation CLI

Initialize:

```bash
python docker/anki-e2e/run_event_protocol.py initialize \
  --output reports/run-events.jsonl \
  --producer docker-e2e
```

Emit phase/message:

```bash
python docker/anki-e2e/run_event_protocol.py emit \
  --output reports/run-events.jsonl \
  --producer docker-e2e \
  --phase-id browser-smoke-first \
  --event-kind message \
  --status info \
  --current 3 \
  --total 23 \
  --message "item=start id=route.home.light kind=route-capture"
```

Validate:

```bash
python docker/anki-e2e/run_event_protocol.py validate \
  --output reports/run-events.jsonl \
  --producer docker-e2e
```

## Тестовое покрытие

Основные tests:

```text
tests/test_run_event_protocol.py
tests/test_run_event_integration.py
tests/test_run_event_controlled_failure.py
tests/test_ci_fast_run_events.py
tests/test_ci_fast_workflow.py
tests/test_ci_e2e_workflow.py
tests/test_prepare_ci_e2e_artifacts_reimport.py
tests/browser_progress.test.mjs
tests/test_browser_progress_node.py
tests/test_e2e_screenshot_contract.py
tests/test_docker_smoke_helpers.py
```

Проверяются:

- schema/security/determinism;
- lifecycle success/failure;
- registry parity;
- concurrent append;
- artifact double validation;
- browser plan order/counts;
- item lifecycle и original-error rethrow;
- producer hard failure;
- partial failure evidence;
- screenshot accounting;
- safe error summary;
- direct Playwright architecture;
- отсутствие retries/dynamic phases.

## Подтверждение

### E2E-I1

```text
Fast CI: 30039103625 — PASS
standard/full: 30039372012 — PASS
standard/full: 30039708429 — PASS
```

### E2E-I2

```text
implementation SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Fast CI: 30048028664 — PASS
standard/cards: 30049216529 — PASS
browser plan: 23/23 PASS
screenshots: 18/18
run-events: final run/pass
```

Исторические доказательства:

- [`../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md);
- [`../reports/ci/e2e-i2-browser-smoke-progress-closeout.md`](../reports/ci/e2e-i2-browser-smoke-progress-closeout.md).