# E2E-I3 — Stable failure diagnostics: итоговый отчёт

**Статус:** `COMPLETE`
**Дата:** 2026-07-24
**Ветка:** `platform/e2e-i3-stable-failure-diagnostics`
**Base:** `core`
**Implementation SHA:** `2ee3c238bd0db2866abb1b97e399baf4fd256136`

## Итог

Реализован единый bounded failure contract для Fast CI и real-Anki Docker E2E:

- reviewed stable code registry;
- canonical `failure-summary.json` schema v1;
- immutable first primary failure;
- bounded secondary manifest/sanitizer/cleanup failures;
- exact phase и browser item identity;
- safe summaries и relative evidence paths;
- original exit code/signal и stable exit class;
- schema-v2 run-event parity;
- historical schema-v1 validation;
- public source/copy validation;
- одна primary GitHub annotation;
- browser timing/progress/producer metrics, закрывающие замечания E2E-I2.

## Опубликованные implementation commits

```text
04fdeaa2  Add stable CI and E2E failure taxonomy
ce13cb93  Integrate stable failures with run events
8532f991  Clarify browser timing and failure evidence
c799a026  Preserve Docker E2E primary failures through cleanup
6380ade3  Publish validated E2E failure artifacts
c234afa9  Allow exact package reuse for E2E-I3 harness changes
2ee3c238  Fix full Fast CI compatibility for E2E diagnostics
```

## Taxonomy

Registry:

```text
docker/anki-e2e/failure_registry.py
```

Fast CI codes:

```text
ASR-FAST-DEPENDENCY
ASR-FAST-VALIDATION
ASR-FAST-FRONTEND
ASR-FAST-PYTHON
ASR-FAST-PACKAGE
ASR-FAST-FINALIZATION
ASR-FAST-CANCELLED
ASR-FAST-UNKNOWN
```

Docker E2E codes:

```text
ASR-E2E-VALIDATION
ASR-E2E-PACKAGE-IDENTITY
ASR-E2E-ENVIRONMENT-IDENTITY
ASR-E2E-REAL-DECK-CONTRACT
ASR-E2E-ANKI-STARTUP
ASR-E2E-READINESS
ASR-E2E-API-SMOKE
ASR-E2E-BROWSER-ITEM
ASR-E2E-TELEMETRY
ASR-E2E-RESTART
ASR-E2E-ARTIFACT-MANIFEST
ASR-E2E-SANITIZATION
ASR-E2E-CLEANUP
ASR-E2E-CANCELLED
ASR-E2E-UNKNOWN
```

Categories:

```text
validation package_identity environment_identity anki_startup readiness
api_smoke browser_item telemetry restart artifact_manifest sanitization
cleanup cancellation unknown
```

Exit classes:

```text
2 3 4 5 6 7 130 143
```

## Canonical summary

Schema v1:

```text
schemaVersion
result
producer
primary
secondary[]
context
cleanup
```

Algorithm:

```text
primary browser/API failure
+ secondary manifest/sanitizer/cleanup failure
=
immutable primary + separate bounded secondary failures
```

Limits:

```text
secondary <= 16
document <= 32 KiB
summary <= 512 UTF-8 bytes
paths per list <= 16
```

Raw/public paths:

```text
Fast CI runtime:  ci-fast/failure-summary.json
Docker runtime:   reports/failure-summary.json
Docker public:    artifacts/reports/failure-summary.json
GitHub Markdown:  failure-summary.md
```

Successful final artifacts correctly do not contain `failure-summary.json`.

## Run-event schema decision

- current writers: schema v2;
- historical schema v1: валидируется;
- mixed versions: fail closed;
- `phase/fail`, `run/fail` и canonical primary: одинаковый failure code;
- success/info events: `failureCode=null`;
- cancellation code reserved without реализации E2E-I4 mechanics.

Final successful streams:

```text
Fast CI: schema v2, final run/pass
Docker:  schema v2, final run/pass
```

## Browser contract и замечания E2E-I2

Закрыты три неблокирующих замечания:

1. `operationDurationMs` исключает run-event producer и persistence overhead.
2. Progress разделён на terminal/pass/fail/skip/remaining/total counters.
3. Producer calls/duration/failures измеряются bounded observationally.

Финальный browser evidence:

```text
schema: v3
items: 23/23 PASS
screenshots: 18/18
failedItemId: null
activeItemId: null
producer calls: 55
producer failures: 0
page errors: 0
failed requests: 0
unexpected external requests: 0
```

Daemon, batching и retries не добавлены.

## Локальная проверка

После последнего implementation fix:

```text
focused repaired Python tests: 82 PASS
full Python suite: 962 PASS, 1 SKIPPED
focused E2E-I3 Python tests: 64 PASS
focused Node tests: 16 PASS
frontend typecheck/build/bundle/copy: PASS
Python compile: PASS
Node syntax: PASS
Bash syntax: PASS
git diff --check: PASS
```

Skipped test:

```text
tests/test_package_artifact.py — package не был заранее собран в локальном source tree
```

Cloud Fast CI затем построил и проверил exact package.

## Development failure и root-cause correction

Промежуточный Fast CI run `30087274155` корректно завершился failure на фазе `python-pytest` с primary code `ASR-FAST-PYTHON`.

После изучения diagnostics были исправлены:

- canonical public failure-summary restoration;
- stable public mismatch error;
- browser constants tests после выделения `browser-plan.mjs`;
- historical v1/current v2 test expectations;
- Windows runner Bash launcher expectation.

Blind rerun не выполнялся. После concrete fix был создан новый commit `2ee3c238…` и один новый final Fast CI.

## Final Fast CI proof

```text
run ID: 30090001597
attempt: 1
result: PASS
tested SHA: 2ee3c238bd0db2866abb1b97e399baf4fd256136
diagnostics artifact ID: 8595362427
diagnostics artifact: ci-fast-30090001597-1
diagnostics digest: sha256:091d5e102a1dd71b094afe2e0710b66b7012a1f9dabf6af53a9b6b81c588e1bd
package artifact ID: 8595363084
package artifact: ci-package-2ee3c238bd0db2866abb1b97e399baf4fd256136-30090001597-1
package transport digest: sha256:132ebf94ca586950b5a4211a5cd8ad921734b77f2d7dcc192860ce2991514be7
inner .ankiaddon SHA-256: 336ed74353b07388a6dbe99a1160a9d1b3e7e5e70eeb490ac9b35d81df4329d5
package size: 750680 bytes
```

Package source decision: новый package-producing Fast CI был обязателен, потому что complete diff от последнего E2E-I2 package включал documentation/roadmap paths вне fail-closed harness allowlist. Allowlist не ослаблялся.

## Final real-Anki proof

```text
run ID: 30098237291
attempt: 1
result: PASS
mode/scope: standard/full
resource telemetry: true
restart policy: auto
screenshot workers: 3
package source: Fast CI run 30090001597
package tested SHA: 2ee3c238bd0db2866abb1b97e399baf4fd256136
E2E checkout SHA: 2ee3c238bd0db2866abb1b97e399baf4fd256136
artifact ID: 8598549935
artifact: ci-e2e-standard-30098237291-1
artifact digest: sha256:c004f58093d7d2880450b29ccc9b74537c1c7263e272f237a421f397dd2ab55c
workflow duration: 145 s
canonical duration: 85.373 s
```

Runtime evidence:

```text
artifact manifest: success
run-events final: run/pass
browser items: 23/23 PASS
screenshots: 18/18
API first/restart: PASS
telemetry restart proof: PASS
page/request/external errors: 0
failure-summary.json in success artifact: absent
```

## Что не запускалось

- intentionally failing cloud run — controlled failures и фактический intermediate failure дали достаточное evidence;
- `perf100` — performance scope не менялся;
- warm repeat — неизменённую pair не повторяем;
- worker comparison — вне scope;
- visual regression — вне scope;
- второй successful full — запрещён stop-loss;
- local full после cloud PASS — не нужен;
- Fast CI/E2E после documentation-only tail — executable semantics не меняются.

## Out of scope

- E2E-I4 cancellation/preflight mechanics;
- E2E-I5 non-release build identity;
- E2E-I6 canonical final summary/history;
- retries/quarantine;
- visual regression;
- performance thresholds;
- release/publish changes;
- product payload/API/UI changes.

## Следующий этап

```text
E2E-I4 — Cancellation и preflight
```

E2E-I4 не начинался.
