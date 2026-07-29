# E2E-I6 — каноническая итоговая сводка и bounded history: итоговый отчёт

**Дата:** 2026-07-26  
**Статус:** `COMPLETE`; локальная и облачная приёмка пройдены  
**Трек:** Platform / CI  
**PR:** #142  
**Целевая ветка:** `core`  
**Implementation candidate:** `00e1e98f91b454a1fa0c5fef5b3530884f01ec32`  
**Base SHA:** `210a04ef8e849012af4cc480d86c0c5f65f2b89a`

Этот документ является historical closeout evidence. Актуальный production contract находится в [`../../docs/e2e-final-summary-history.md`](../../docs/e2e-final-summary-history.md). При противоречии приоритет имеют production code, tests и `docs/`.

## 1. Цель этапа

E2E-I6 должен был завершить observability/build-identity track одним однозначным итогом real-Anki E2E и bounded историей сопоставимых запусков.

До этапа итог приходилось восстанавливать по нескольким отдельным evidence-файлам, workflow steps и artifact metadata. После этапа один canonical summary определяет:

- фактический результат запуска;
- степень завершённости finalization;
- terminal event и exit semantics;
- build identity и compatibility key;
- проверки и performance projections;
- pre-upload artifact footprint;
- безопасные evidence references;
- финальный cleanup/public-export state.

История добавляет post-upload metadata, first-run pass accounting, сопоставимые percentile aggregates и informational regression observations без превращения CI в performance gate.

## 2. Реализованный scope

### 2.1 Canonical final summary

Добавлен единый файл:

```text
reports/final-run-summary.json
```

Публичная semantically identical копия:

```text
artifacts/reports/final-run-summary.json
```

Ключевые свойства:

- schema v1;
- closed object model;
- deterministic UTF-8 JSON;
- максимум 64 KiB;
- atomic writes;
- safe POSIX relative evidence paths;
- независимая валидация raw и public documents;
- semantic parity raw/public;
- SHA-256 exact public bytes.

### 2.2 Result и finalization semantics

Поддерживаются результаты:

```text
success
failure
cancelled
```

И уровни finalization:

```text
complete
partial
minimal
unavailable
```

Нормальный успешный run обязан завершиться как:

```text
result=success
finalizationStatus=complete
terminal.event=run/pass
terminal.failureCode=null
terminal.signal=null
terminal.exitCode=0
finalState.cleanupStatus=success
finalState.artifactPreparationStatus=success
finalState.publicValidated=true
```

Functional failure сохраняет bounded projection canonical `failure-summary.json`. Cancellation сохраняет immutable signal-time `cancellation-summary.json` и отдельно добавляет post-signal host cleanup result. Setup/preflight failure не создаёт вымышленную build identity.

### 2.3 Cross-evidence validation

Builder сопоставляет structured evidence по следующим областям:

- workflow execution identity;
- terminal run event;
- functional failure summary;
- cancellation signal/exit snapshot;
- release/non-release build identity;
- static/runtime preflight;
- browser plan/progress/report;
- screenshot counters;
- phase timings;
- resource summary reference;
- artifact manifest/inventory/footprint;
- final cleanup и public artifact preparation.

Результат не выводится из console text.

### 2.4 Compatibility и candidate identity

Добавлен deterministic compatibility key по hard dimensions execution contour. Cloud и local contours не смешиваются.

В compatibility key не входят run ID, timestamps, branch/PR title, artifact name, package commit, harness commit или build identity digest.

Для first-run reliability используется отдельный candidate key:

```text
non-release: identity kind + build identity digest + compatibility key
release: exact release artifact identity + compatibility key
```

Release и non-release candidates не смешиваются.

### 2.5 Bounded history

Добавлен compact history contract:

```text
reports/e2e-run-history.json
```

Границы:

```text
retention horizon: 90 дней
maximum total entries: 120
maximum entries per compatibility key: 30
```

Поддерживаются continuity states `bootstrap`, `append` и `reset`. Invalid previous history сбрасывается fail closed, но текущая валидная запись сохраняется.

### 2.6 First-run pass rate

Eligible candidate учитывается только при:

```text
runPurpose=acceptance
contour=cloud
mode!=perf100
valid candidate key
runAttempt=1
finalizationStatus=complete
result=success|failure
```

Controlled, measurement, cancelled, local, partial/minimal, rerun-attempt и duplicate candidate runs получают явную exclusion reason и не искажают first-run pass rate.

### 2.7 Performance aggregation

История агрегирует только compatible successful samples.

Percentile rules:

```text
p50: inclusive method, минимум 3 samples
p95: inclusive method, минимум 20 samples
```

Отсутствующие, несовместимые, failed и cancelled metrics исключаются явно.

### 2.8 Artifact footprint и transport metadata

Canonical summary хранит только pre-upload footprint. GitHub artifact ID, digest, size, expiry и upload duration появляются после upload только в history entry.

Transport metadata проверяется по GitHub run/repository/artifact identity и не подменяет внутренний package SHA-256 либо build identity digest.

### 2.9 Legacy compatibility

Сохранены derived projections:

```text
ci-e2e-summary.json
ci-e2e-summary.md
reports/e2e-performance-summary.json
```

Legacy projections не определяют результат, terminal state, compatibility или final timings самостоятельно.

### 2.10 Regression observations

Добавлены:

```text
reports/e2e-regression-observations.json
reports/e2e-regression-observations.md
```

Classification строго:

```text
observational-only
```

Observations не публикуют `::error`, не создают blocking threshold и не активируют CI optimization автоматически.

### 2.11 GitHub Actions integration

В `.github/workflows/ci-e2e.yml` добавлен последовательный lifecycle:

1. final Docker state capture;
2. bounded Docker cleanup;
3. raw canonical summary;
4. public sanitizer/export;
5. final raw/public canonical summary и legacy projections;
6. основной artifact upload;
7. upload metadata resolution;
8. поиск предыдущей bounded history;
9. merge/aggregate/render observations;
10. отдельный compact history artifact;
11. compact GitHub Step Summary;
12. отдельный bounded cancellation tail.

## 3. Изменённые области

Implementation candidate относительно `core` затрагивал 27 файлов:

- `.github/workflows/ci-e2e.yml`;
- `docs/e2e-final-summary-history.md`;
- canonical summary modules в `scripts/e2e_final_summary*`;
- bounded history modules в `scripts/e2e_final_summary_history*`;
- GitHub history transport;
- cancellation preparation;
- fail-closed harness reuse allowlist;
- focused contract, history, transport, artifact и workflow tests;
- обновлённые static contracts для нового canonical workflow lifecycle.

Product runtime, dashboard API, frontend payload и UI не менялись.

## 4. Локальная верификация

### 4.1 Canonical environment

```text
OS contour: Arch Linux в WSL
Python: 3.11.15 через pyenv
Node.js: 20.20.2
pytest: 9.1.1
jsonschema: 4.26.0
```

Системный Arch Python 3.14 сохранён для distribution packages, но project-local `.python-version` теперь стабильно выбирает Python 3.11.

### 4.2 Полный Python suite

```text
1081 passed
17 subtests passed
```

### 4.3 Focused и structural checks

Подтверждены:

- `py_compile` для новых modules/tests;
- `git diff --check`;
- static workflow contracts;
- canonical summary success/failure/cancellation/setup cases;
- raw/public parity;
- deterministic serialization;
- safe-path/security validation;
- history bounds/dedup/reset;
- first-run eligibility/exclusions;
- inclusive percentile minimums;
- artifact integration;
- GitHub transport validation;
- fail-closed harness reuse.

### 4.4 Harness reuse verdict

Полный implementation diff классифицирован как:

```text
reuseAllowed=true
reuseMode=harness-only
changedFileCount=27
```

После финального contract fix был создан новый exact Fast CI package, поэтому cloud acceptance не зависела от устаревшего package artifact.

## 5. Fast CI acceptance

```text
workflow: Fast CI
run ID: 30166328801
run attempt: 1
head SHA: 00e1e98f91b454a1fa0c5fef5b3530884f01ec32
result: success
job: Frontend, Python and package
job duration: 3m50s
```

Все steps завершились успешно, включая canonical fast pipeline, verification plan, package preparation, diagnostics upload и exact package upload.

### Artifacts

```text
exact package artifact ID: 8621706488
name: ci-package-00e1e98f91b454a1fa0c5fef5b3530884f01ec32-30166328801-1
size: 745761 bytes
digest: sha256:9f2b3ca04b43cb8d3b7a10669aeb461c6508ec20fc0b90cab96bad71622a7343

Fast CI diagnostics artifact ID: 8621706395
name: ci-fast-30166328801-1
size: 14686 bytes
digest: sha256:2434a6ceb249c059e73550a357ae94524b657eab3fcd1aa63589be1b0c7a0272
```

## 6. Full Docker / Anki E2E acceptance

```text
workflow: Full Docker / Anki E2E
run ID: 30166561184
run attempt: 1
mode: standard
scope: full
run purpose: acceptance
resource telemetry: false
verify restart: auto
head SHA: 00e1e98f91b454a1fa0c5fef5b3530884f01ec32
Fast CI source run: 30166328801
result: success
job: Real Anki Desktop (standard / full)
job duration: 2m47s
```

Успешно прошли exact Fast CI handoff, static/runtime preflight, GHCR environment verification, non-release build identity, canonical Docker-only E2E, package hash verification, public evidence export, final cleanup, canonical summary, main artifact upload, bounded history и Step Summary.

### Canonical result

```text
result: success
finalizationStatus: complete
terminal.event: run/pass
terminal.failureCode: null
terminal.signal: null
terminal.exitCode: 0
cleanupStatus: success
artifactPreparationStatus: success
publicValidated: true
compatibilityKey: sha256:52efbdcc0c17b3257ea19c51f6f3d2c3a77a0c4de269d27ab38560815b552ed9
canonical summary SHA-256: bc5410fd5edc17cecd16fc29c470e31de7ce47b9d94fadd4c6c92896cc3fd566
```

### Main artifact

```text
artifact ID: 8621761591
name: ci-e2e-standard-30166561184-1
size: 6836461 bytes
digest: sha256:11dc6f3963dbd6b91059cdab27260bb7c1b41237d11d0adb8df4a36ca662fe05
```

### Compact history artifact

```text
artifact ID: 8621762124
name: ci-e2e-history-30166561184-1
size: 6308 bytes
digest: sha256:0e545d0e46f87adaac8e1f73ef8ae864fc2df3234a05f9825340dc4ff6cb9c5c
continuity: bootstrap
entries: 1
history SHA-256: b7f32f4aee158b04880cad5061e15f43a06aee4d544903f36e89b36322106a80
regression classification: observational-only
```

Compact history artifact содержал ровно разрешённые файлы:

```text
reports/final-run-summary.json
reports/e2e-run-history.json
reports/e2e-history-aggregation.json
reports/e2e-regression-observations.json
reports/e2e-regression-observations.md
```

Logs, screenshots, packages, browser item arrays, failure stacks и environment dumps в history artifact отсутствовали.

## 7. Retention

Во время acceptance repository ceiling для Actions artifacts был равен 14 дням. Поэтому уже созданный history artifact сохранил 14-дневный expiry.

После acceptance настройка repository artifact/log retention была изменена:

```text
previous: 14 days
current: 90 days
maximum allowed: 90 days
```

GitHub применяет изменение только к новым artifacts. Повторять уже успешный unchanged E2E только ради нового expiry не требовалось. Следующие compact history artifacts смогут получить запрошенные workflow 90 дней.

## 8. Security и safety review

Подтверждено сохранение следующих границ:

- exact Fast CI package identity не ослаблена;
- package и harness identities остаются независимыми;
- cloud source-build fallback не добавлен;
- release identity остаётся отдельным contract;
- sanitizer/public exporter валидирует итог независимо;
- token, authorization header и token-bearing URL не допускаются;
- private absolute paths не допускаются;
- card HTML и user content не попадают в summary/history;
- arbitrary environment dump и raw stack не публикуются;
- history artifact ограничен строгим allowlist;
- cancellation evidence остаётся bounded и отдельным от normal tail.

## 9. Что намеренно не запускалось

После final exact-SHA acceptance не выполнялись:

- второй successful `standard/full`;
- warm-cache repeat;
- `perf100`;
- screenshot worker comparison;
- visual regression;
- intentionally failing cloud run;
- новый controlled cancellation A/B;
- retry/quarantine/sharding experiments;
- external telemetry/history service;
- blocking performance thresholds.

Эти проверки не требовались риском E2E-I6. Successful unchanged package/harness pair не повторялся.

## 10. Найденные и устранённые проблемы

В процессе интеграции были обнаружены и устранены:

- лишние blank lines at EOF;
- отсутствие repository-local `scripts/` import bootstrap в новых tests;
- устаревший сокращённый non-release identity fixture;
- stale static workflow contracts со старыми step names;
- неполная локальная Python environment setup;
- выбор системного Python 3.14 вместо project-local Python 3.11;
- generated `__pycache__` внутри add-on tree;
- launcher-only ошибки чтения verification plan output и передачи boolean workflow input.

Ни одна из этих проблем не была скрыта ослаблением production validation или tests. Исправления либо приводили fixtures/contracts к production behavior, либо исправляли локальные launchers/environment.

## 11. Документация

Актуализированы:

- корневой `README.md`;
- `docs/README.md`;
- `docs/ai-handoff.md`;
- `roadmap/README.md`;
- `roadmap/platform/README.md`;
- `roadmap/platform/e2e-observability-build-identity.md`;
- `reports/README.md`;
- PR #142 description.

Актуальный contract:

- [`../../docs/e2e-final-summary-history.md`](../../docs/e2e-final-summary-history.md)

## 12. Итог и merge readiness

E2E-I6 удовлетворяет completion criteria:

- canonical summary существует и валидируется;
- history bounded и детерминирована;
- compatibility/candidate rules реализованы;
- first-run pass и percentile rules покрыты tests;
- regression reporting informational-only;
- local canonical suite полностью зелёный;
- Fast CI exact package принят;
- один risk-required `standard/full` real-Anki E2E принят;
- main/history artifacts проверены;
- PR #142 имеет `mergeStateStatus=CLEAN`;
- владелец явно разрешил слияние.

На момент создания отчёта:

```text
PR #142: OPEN / DRAFT / CLEAN
merge: разрешён владельцем, ещё не выполнен
core merge SHA: будет зафиксирован post-merge docs sync
```

После слияния E2E-I roadmap завершён. Следующий Platform/CI stage не активируется автоматически. CI 7–12 требуют отдельного измеренного trigger и отдельного решения владельца.
