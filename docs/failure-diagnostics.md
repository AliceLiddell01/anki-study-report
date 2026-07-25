# Стабильная диагностика отказов Fast CI и Docker E2E

**Статус:** реализованный контракт `E2E-I3`
**Schema canonical failure summary:** v1
**Run-event schema:** current v2; historical v1 остаётся валидируемой
**Производители:** `fast-ci`, `docker-e2e`
**Дата подтверждения:** 2026-07-24

## Назначение

Контракт сохраняет первый функциональный root cause между Fast CI, Docker orchestration, browser smoke, manifest/sanitizer/cleanup и публичным GitHub artifact.

Он не заменяет raw logs, timing, browser report, screenshots или `run-events.jsonl`. `failure-summary.json` является bounded canonical index над существующим evidence.

## Источники истины

```text
docker/anki-e2e/failure_registry.py  stable codes/categories/phase mapping
docker/anki-e2e/failure_schema.py    document schema v1
docker/anki-e2e/failure_entry.py     failure entry schema v1
docker/anki-e2e/failure_store.py     atomic primary/secondary storage
docker/anki-e2e/failure_safety.py    security and path validation
docker/anki-e2e/failure_protocol.py  public API and CLI
scripts/failure_artifact_protocol.py source/public artifact bridge
```

## Stable taxonomy

### Fast CI

| Code | Category | Default exit class |
| --- | --- | ---: |
| `ASR-FAST-DEPENDENCY` | `validation` | 2 |
| `ASR-FAST-VALIDATION` | `validation` | 2 |
| `ASR-FAST-FRONTEND` | `validation` | 2 |
| `ASR-FAST-PYTHON` | `validation` | 2 |
| `ASR-FAST-PACKAGE` | `package_identity` | 3 |
| `ASR-FAST-FINALIZATION` | `artifact_manifest` | 6 |
| `ASR-FAST-CANCELLED` | `cancellation` | 130 |
| `ASR-FAST-UNKNOWN` | `unknown` | 2 |

### Docker E2E

| Code | Category | Default exit class |
| --- | --- | ---: |
| `ASR-E2E-VALIDATION` | `validation` | 2 |
| `ASR-E2E-PACKAGE-IDENTITY` | `package_identity` | 3 |
| `ASR-E2E-ENVIRONMENT-IDENTITY` | `environment_identity` | 3 |
| `ASR-E2E-REAL-DECK-CONTRACT` | `validation` | 3 |
| `ASR-E2E-ANKI-STARTUP` | `anki_startup` | 4 |
| `ASR-E2E-READINESS` | `readiness` | 4 |
| `ASR-E2E-API-SMOKE` | `api_smoke` | 5 |
| `ASR-E2E-BROWSER-ITEM` | `browser_item` | 5 |
| `ASR-E2E-TELEMETRY` | `telemetry` | 5 |
| `ASR-E2E-RESTART` | `restart` | 4 |
| `ASR-E2E-ARTIFACT-MANIFEST` | `artifact_manifest` | 6 |
| `ASR-E2E-SANITIZATION` | `sanitization` | 6 |
| `ASR-E2E-CLEANUP` | `cleanup` | 7 |
| `ASR-E2E-CANCELLED` | `cancellation` | 130 |
| `ASR-E2E-UNKNOWN` | `unknown` | 5 |

Разрешённые категории:

```text
validation
package_identity
environment_identity
anki_startup
readiness
api_smoke
browser_item
telemetry
restart
artifact_manifest
sanitization
cleanup
cancellation
unknown
```

Разрешённые exit classes:

```text
2 3 4 5 6 7 130 143
```

`SIGINT`/130 и `SIGTERM`/143 сохраняют cancellation-compatible exit semantics. Полный redesign cancellation остаётся `E2E-I4`.

## Canonical schema v1

```json
{
  "schemaVersion": 1,
  "result": "failure",
  "producer": "docker-e2e",
  "primary": {
    "failureCode": "ASR-E2E-BROWSER-ITEM",
    "category": "browser_item",
    "domain": "e2e",
    "phaseId": "browser-smoke-first",
    "itemId": "route.cards.dark",
    "itemKind": "route-capture",
    "errorType": "AssertionError",
    "summary": "Browser smoke item failed",
    "occurredAtUtc": "2026-07-24T00:00:00.000Z",
    "elapsedMs": 12345,
    "originalExitCode": 1,
    "originalSignal": null,
    "exitClass": 5,
    "evidencePaths": ["reports/browser-smoke-first.json"],
    "rawDiagnosticPaths": ["diagnostics/anki_study_report.log"]
  },
  "secondary": [
    {
      "failureCode": "ASR-E2E-CLEANUP",
      "category": "cleanup",
      "domain": "e2e",
      "phaseId": null,
      "itemId": null,
      "itemKind": null,
      "errorType": "CleanupError",
      "summary": "Docker E2E cleanup failed",
      "occurredAtUtc": "2026-07-24T00:00:01.000Z",
      "elapsedMs": 13345,
      "originalExitCode": 1,
      "originalSignal": null,
      "exitClass": 7,
      "evidencePaths": [],
      "rawDiagnosticPaths": ["diagnostics/anki-stderr-first.log"]
    }
  ],
  "context": {
    "lastSuccessfulPhaseId": "api-smoke-first",
    "lastSuccessfulItemId": "route.cards.light",
    "activePhaseId": "browser-smoke-first",
    "activeItemId": "route.cards.dark"
  },
  "cleanup": {
    "status": "failure",
    "failureCount": 1
  }
}
```

Failure entry field order фиксирован:

```text
failureCode category domain phaseId itemId itemKind errorType summary
occurredAtUtc elapsedMs originalExitCode originalSignal exitClass
evidencePaths rawDiagnosticPaths
```

## Primary / secondary algorithm

1. Первая запись `primary` создаёт canonical root cause.
2. Следующая попытка записать primary не заменяет первую.
3. Manifest, sanitizer, wrapper и cleanup failures добавляются в `secondary`.
4. Secondary entries дедуплицируются по code/phase/item/summary.
5. Cancellation codes не допускаются как secondary.
6. `cleanup.failureCount` обязан совпадать с числом cleanup entries.
7. Public summary обязан быть семантически и байтово каноничен относительно validated source summary.

## Bounded contract

```text
summary:            до 512 UTF-8 bytes
errorType:          до 80 UTF-8 bytes
secondary entries:  до 16
paths per list:     до 16
path:               до 240 UTF-8 bytes
whole document:     до 32 KiB
```

Запрещены token-bearing URLs, Authorization headers, private Linux/Windows absolute paths, private keys, GitHub/OpenAI-like secrets, control characters и workflow-command injection.

Разрешены только safe relative evidence paths. Raw stack и arbitrary exception text не становятся stable code.

## Evidence paths

### Fast CI

```text
runtime:  ci-fast/failure-summary.json
artifact: failure-summary.json
```

### Docker E2E

```text
container: reports/failure-summary.json
public:    artifacts/reports/failure-summary.json
markdown:  failure-summary.md
```

Успешный run не содержит `failure-summary.json`. Наличие summary при success или отсутствие summary при failure является contract violation.

## Run-event integration

Current writers используют schema v2:

- `failureCode` обязателен для terminal `fail`/`cancel`;
- `failureCode` запрещён для success/info;
- phase failure, final run failure и canonical primary обязаны иметь одинаковый code;
- historical schema v1 остаётся валидируемой;
- mixed v1/v2 stream запрещён;
- dynamic browser phase IDs не добавлены.

## Browser integration и закрытие замечаний E2E-I2

Browser plan вынесен в `browser-plan.mjs`. Browser report schema v3:

- `operationDurationMs` измеряет только operation, без producer/persist overhead;
- progress использует `terminalItems`, `passedItems`, `failedItems`, `skippedItems`, `remainingItems`, `totalItems`;
- producer metrics: `runEventProducerCalls`, `runEventProducerDurationMs`, `runEventProducerFailures`;
- exact failed/active item сохраняется;
- daemon, batching и retries не добавлены.

Telemetry browser item получает `ASR-E2E-TELEMETRY`; остальные browser items — `ASR-E2E-BROWSER-ITEM`.

## GitHub presentation

GitHub получает одну primary annotation и компактный Markdown summary. Secondary failures остаются в canonical document и не скрывают root cause.

## Verification

Final implementation:

```text
SHA: 2ee3c238bd0db2866abb1b97e399baf4fd256136
```

Fast CI:

```text
run ID: 30090001597
result: PASS
package SHA-256: 336ed74353b07388a6dbe99a1160a9d1b3e7e5e70eeb490ac9b35d81df4329d5
```

Real-Anki:

```text
run ID: 30098237291
mode/scope: standard/full
result: PASS
browser items: 23/23
screenshots: 18/18
run-events final: run/pass
```

Полный historical evidence находится в [`../reports/ci/e2e-i3-stable-failure-diagnostics-closeout.md`](../reports/ci/e2e-i3-stable-failure-diagnostics-closeout.md).

## Out of scope

- cancellation/preflight redesign — `E2E-I4`;
- non-release build identity — `E2E-I5`;
- canonical final summary/history — `E2E-I6`;
- retries/quarantine;
- visual regression;
- performance thresholds.
