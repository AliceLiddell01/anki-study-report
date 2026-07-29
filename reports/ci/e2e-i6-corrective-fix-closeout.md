# E2E-I6 — bounded corrective fix: итоговый отчёт

**Дата:** 2026-07-26  
**Статус:** `COMPLETE`; исправление и облачная приёмка подтверждены  
**Трек:** Platform / CI  
**PR:** #144 (`OPEN`, не влит)  
**Целевая ветка:** `core`  
**Base SHA:** `a49c4b301084e5ffd3915b4cfcacf7bb8c95a3cb`  
**Implementation candidate:** `afe650adbf3ba55cb6b59068a1127022b651fbf3`

Этот файл — historical closeout evidence для ограниченной corrective-правки уже завершённого E2E-I6. Он не активирует новый roadmap stage. Актуальный contract находится в [`../../docs/e2e-final-summary-history.md`](../../docs/e2e-final-summary-history.md); при противоречии приоритет имеют production code, tests и `docs/`.

## 1. Причина corrective-правки

После принятия E2E-I6 были подтверждены два дефекта представления evidence:

1. public artifact paths имеют prefix `artifacts/`, но footprint classifier категоризировал первый segment без нормализации. В принятом run все `71` файла и `6 823 785` uncompressed bytes ошибочно попали в `other`;
2. regression observations брали current values только из `summary.performance.metrics`, хотя `runEventProducerCalls` и `runEventProducerDurationMs` находятся в `summary.performance.producer`. Summary/history содержали `55` и `4193`, а observations выдавали `current=null` и `not-comparable`.

Functional result, package identity, product runtime, dashboard API и UI этим дефектом не менялись.

## 2. Исправление

### 2.1 Artifact footprint

- перед categorization удаляется ровно один точный optional prefix `artifacts/`;
- raw paths без этого prefix сохраняют прежнюю семантику;
- unknown top-level paths остаются `other`;
- двойной prefix не stripping-ится повторно;
- traversal, absolute, private и иные unsafe paths продолжают отклоняться существующей fail-closed validation.

### 2.2 Regression observations

Добавлен единый resolver текущего значения:

- canonical performance metrics — из `performance.metrics`;
- producer calls/duration — из `performance.producer`;
- pre-upload artifact bytes — из `artifactFootprint`;
- post-upload artifact size/duration — из current history entry.

Schema v1, percentile rules и informational-only contract не менялись.

### 2.3 Tests

Focused coverage проверяет:

- raw/public category parity;
- exact-prefix-only normalization;
- unknown, unsafe и double-prefix paths;
- суммы category counts/bytes и derived counters;
- producer equality между summary, history и observations;
- `insufficient-history` при одной sample;
- p50/p95 minimums;
- `not-comparable` при отсутствующем producer value;
- неизменность footprint/post-upload special metric sources.

## 3. Неуспешные диагностические запуски

### 3.1 Fast CI `30169335632`

**Результат:** `failure` до package artifact.

- tested SHA: `2dac7a198bab018592afd94c3c2b61b853a06735`;
- `1097 passed`, `3 failed`, `6 skipped`;
- два новых теста не учитывали predicted canonical summary в категории `reports`;
- один тест ошибочно считал redundant `./reports/...` unsafe traversal path;
- concrete correction: `afe650adbf3ba55cb6b59068a1127022b651fbf3`.

Diagnostics artifact:

```text
ID: 8622498294
digest: sha256:f438bb8526586e06131c51a244feaf78186eed16813f67968b368cb5583ce76d
```

### 3.2 standard/full `30169435615`

**Результат:** `failure` до Docker execution.

Workflow input содержал trailing whitespace в `fast_ci_run_id`. Run завершился на разрешении exact Fast CI source; static/runtime preflight, GHCR pull, real-Anki Docker E2E, browser smoke и artifact upload не выполнялись. Этот run не является functional E2E failure corrective implementation.

## 4. Успешная облачная приёмка

### 4.1 Fast CI

```text
run: 30169763775
attempt: 1
HEAD: afe650adbf3ba55cb6b59068a1127022b651fbf3
result: success
command: .\scripts\run_full_check.ps1 -SkipDocker
```

Artifacts:

```text
diagnostics ID: 8622618429
diagnostics digest: sha256:8bd57e6723b2f25f66fd4d23aeafd66fd0dfc9abbdb147b22e6a5cbc79c38bc9
package ID: 8622618537
package artifact digest: sha256:ed3ad6b54f8e73fc8ea5e9cc22d415c5ef1263d4d0053f6db1e3c4f508fdd8a3
package inner SHA-256: b68fe0b2d53d57e545efb4f0f4de229eec34c2c9f0b2835ca16755beaf1da8da
package size: 750680 bytes
```

### 4.2 telemetry-enabled standard/full

```text
run: 30169890912
attempt: 1
HEAD: afe650adbf3ba55cb6b59068a1127022b651fbf3
mode: standard
scope: full
runPurpose: acceptance
resourceTelemetry: true
restartExecuted: true
result: success
finalizationStatus: complete
terminal: run/pass
```

Exact handoff:

```text
packageSource: fast-ci-artifact
source Fast CI run: 30169763775
source tested SHA: afe650adbf3ba55cb6b59068a1127022b651fbf3
E2E workflow/harness SHA: afe650adbf3ba55cb6b59068a1127022b651fbf3
reuse mode in accepted build identity: exact-tree
changedFileCount: 0
```

Main artifact:

```text
ID: 8622647178
name: ci-e2e-standard-30169890912-1
digest: sha256:cfcf34691a0e5c81a8eb03a3b7487beba3da6fda05dbeb701fafbac899203e11
uploaded size: 6893280 bytes
```

History artifact:

```text
ID: 8622648096
name: ci-e2e-history-30169890912-1
digest: sha256:2f9579dab8fd60535aed0599e5c486c63d6c2e5cd97dd57a6a7257407d322a65
continuity: append
entries: 2
```

## 5. Проверенные результаты corrective-правки

### 5.1 Footprint after fix

```text
reports:     32 files / 2 417 053 bytes
screenshots: 18 files / 3 636 138 bytes
diagnostics: 13 files /    20 640 bytes
package:      1 file  /   750 680 bytes
runtime:      4 files /     5 659 bytes
html:         0 files /         0 bytes
other:        6 files /    49 926 bytes
----------------------------------------
total:       74 files / 6 880 096 bytes
```

Category totals exactly equal canonical `fileCount` and `totalUncompressedBytes`. Остаток `other` состоит только из ожидаемых служебных top-level файлов:

```text
artifacts/artifact-manifest.json
ci-e2e-summary.json
ci-e2e-summary.md
environment.txt
logs/docker-build-and-e2e.log
logs/docker-system.txt
```

Raw/public canonical summaries семантически равны.

### 5.2 Producer observations after fix

```text
runEventProducerCalls:
  summary: 55
  history: 55
  observations.current: 55
  status: insufficient-history

runEventProducerDurationMs:
  summary: 4711
  history: 4711
  observations.current: 4711
  status: insufficient-history
```

Обе metrics имеют `sampleCount=1` для текущего compatibility key; `p50` и `p95` корректно остаются `null`.

### 5.3 Functional и telemetry evidence

- preflight: `20/20` checks passed;
- browser: `23/23` terminal items passed;
- screenshots: `18/18`;
- first API smoke: pass;
- restart API smoke: pass;
- cleanup: success;
- source/public validation: success;
- resource telemetry: `87` samples, evidence present;
- telemetry restart persistence: pass;
- confirmed telemetry deletion: true;
- producer failures: `0`.

## 6. Scope и сохранённые границы

Изменены только:

```text
scripts/e2e_final_summary_common.py
scripts/e2e_final_summary_history_report.py
tests/test_e2e_final_summary_artifact_integration.py
tests/test_e2e_final_summary_history.py
```

Относительно `core` diff остаётся harness/test-only. Accepted E2E использовал новый exact Fast CI artifact того же HEAD, поэтому build identity закономерно зафиксировал `exact-tree`, а не cross-commit `harness-only` reuse.

Не добавлены:

- schema v2;
- blocking thresholds;
- retries;
- performance optimization;
- product/API/UI changes;
- CI 7–12;
- новый roadmap stage.

## 7. Не запускалось

- второй successful full «для уверенности»;
- `perf100`;
- warm-cache repeat;
- worker comparison;
- cancellation A/B;
- intentionally failing cloud run;
- visual regression;
- CI 7 measurement gate.

Эти проверки не требовались риском corrective diff.

## 8. Итог и оставшееся действие

Corrective implementation подтверждён одним successful Fast CI и одним successful telemetry-enabled `standard/full` на точном HEAD `afe650adbf3ba55cb6b59068a1127022b651fbf3`.

PR #144 остаётся открытым и не влит. Auto-merge не включён. После docs-only closeout повторный Fast CI или Docker E2E не требуется; оставшееся действие — обычный review и merge владельцем без активации следующего Platform/CI stage.
