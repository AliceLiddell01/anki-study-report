# E2E-I2 — Browser smoke progress: итоговый отчёт

**Дата закрытия:** 2026-07-24  
**Репозиторий:** `AliceLiddell01/anki-study-report`  
**Ветка:** `platform/e2e-i2-browser-smoke-progress`  
**Base:** `core`  
**Base SHA:** `38483b3c6ff59f7bc71b03806e9dcdaadb255fa3`  
**Финальный implementation SHA:** `e25bd0b24e32ce4717ed2dbda138d802f707f6d5`  
**Статус:** `COMPLETE`

## 1. Цель этапа

`E2E-I2` устраняет длинный немой интервал внутри direct Playwright Library browser smoke. До этого внешний Docker lifecycle показывал одну крупную фазу `browser-smoke-first`, но не объяснял, какой route, theme, native preview anchor, telemetry stage или Cards state сейчас выполняется.

После этапа browser smoke имеет:

- детерминированный plan до запуска Chromium;
- стабильные item IDs и item kinds;
- live `START` / `PASS` / `FAIL` и `[current/total]`;
- monotonic item duration;
- item-level screenshot contribution;
- partial machine-readable evidence при failure;
- точный failed/active item;
- deterministic top-5 slowest items;
- fail-closed parity между plan и 18 browser screenshots;
- безопасную интеграцию с schema-v1 `run-events.jsonl` без dynamic global phase IDs.

## 2. Scope

### Выполнено

- browser execution plan;
- единый item wrapper;
- route/theme progress;
- telemetry progress по четырём смысловым стадиям;
- native-preview progress по трём anchors;
- Cards state progress для light/dark;
- final diagnostics item;
- browser report schema v2;
- screenshot performance evidence schema v2;
- partial failure evidence;
- E2E-I1 run-event integration через `message/info`;
- focused Node/Python tests;
- один risk-appropriate `standard/cards` real-Anki proof;
- русскоязычная документация и closeout.

### Не входило и не реализовано

- новые dashboard routes или preview anchors;
- новые продуктовые E2E-сценарии;
- visual regression и screenshot baselines;
- миграция на `@playwright/test`;
- Playwright HTML reporter/trace viewer;
- retries и flake quarantine;
- stable global failure codes и общий `failure-summary.json` (`E2E-I3`);
- cancellation/preflight redesign (`E2E-I4`);
- unique Fast CI build identity (`E2E-I5`);
- canonical final summary/history storage (`E2E-I6`);
- performance thresholds;
- browser parallelization или изменение workers;
- изменение dashboard payload/API;
- release path.

## 3. Реализация

### 3.1. Детерминированный plan

Новый модуль:

```text
docker/anki-e2e/browser-progress.mjs
```

Plan создаётся до `chromium.launch()` и содержит:

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

Фактический plan успешного proof:

```text
schemaVersion: 1
items: 23
expected screenshots: 18
telemetry: enabled
```

Распределение items:

| Kind | Количество | Screenshots |
| --- | ---: | ---: |
| `browser-launch` | 1 | 0 |
| `dashboard-setup` | 1 | 0 |
| `route-capture` | 10 | 10 |
| `telemetry` | 4 | 0 |
| `native-preview` | 3 | 6 |
| `scenario-cards` | 1 | 0 |
| `cards-route` | 2 | 2 |
| `diagnostics` | 1 | 0 |
| **Итого** | **23** | **18** |

### 3.2. Stable item IDs

Фактические группы:

```text
browser.launch
dashboard.setup
route.home.light
route.home.dark
route.cards.light
route.cards.dark
route.decks.light
route.decks.dark
route.profile.light
route.profile.dark
route.settings.light
route.settings.dark
telemetry.declined
telemetry.reliability
telemetry.feature
telemetry.offline
preview.words-preview
preview.grammar-preview
preview.java-preview
scenario.cards
cards-route.light
cards-route.dark
diagnostics.final
```

IDs формируются только из заранее ограниченных route/theme/anchor/step значений. Они не содержат token, URL, filesystem path или пользовательские данные.

### 3.3. Item wrapper

`BrowserProgress.run(itemId, operation)`:

1. проверяет planned/unique item;
2. фиксирует active item;
3. использует `performance.now()`;
4. немедленно пишет console START;
5. пишет safe `message/info` в `run-events.jsonl`;
6. выполняет operation;
7. проверяет screenshot delta;
8. сохраняет PASS или FAIL;
9. записывает partial report после lifecycle transition;
10. при failure повторно бросает исходную ошибку.

Retries отсутствуют.

### 3.4. Live console contract

Пример фактического успешного stream:

```text
[BROWSER] PLAN items=23 screenshots=18 telemetry=true
[BROWSER] [1/23] START browser-launch item=browser.launch
[BROWSER] [1/23] PASS browser-launch item=browser.launch duration=478ms screenshots=0
[BROWSER] [3/23] START route-capture item=route.home.light route=#/home theme=light
[BROWSER] [3/23] PASS route-capture item=route.home.light duration=1566ms screenshots=1
```

Controlled focused test подтверждает failure line вида:

```text
[BROWSER] [1/1] FAIL native-preview item=preview.words-preview duration=10ms screenshots=0 errorType=TypeError
```

Progress line не содержит raw stack, token-bearing URL или private path.

### 3.5. Run-event integration

Global protocol schema не изменён:

```text
schemaVersion: 1
phaseId: browser-smoke-first
eventKind: message
status: info
current: item order
total: plan item count
message: bounded item lifecycle marker
failureCode: null
```

Не создаются dynamic phase IDs. Python producer остаётся единственным schema/security validator. Node adapter использует `execFile`, аргументы передаются массивом, `shell: false`, non-zero exit является hard failure.

Фактический public stream успешного proof:

```text
path: artifacts/reports/run-events.jsonl
lines: 81
final event: run/pass
final duration: 31609 ms
```

Примеры structured messages:

```text
current=1 total=23 item=start id=browser.launch kind=browser-launch
current=1 total=23 item=pass id=browser.launch kind=browser-launch durationMs=478 screenshots=0
current=3 total=23 item=start id=route.home.light kind=route-capture
current=3 total=23 item=pass id=route.home.light kind=route-capture durationMs=1566 screenshots=1
```

### 3.6. Structured evidence

Browser report:

```text
reports/browser-smoke-first.json
schemaVersion: 2
```

Он содержит прежние поля и новые:

```text
plan
progress
items
slowestItems
screenshotPerformance
```

Performance evidence:

```text
reports/screenshot-performance.json
schemaVersion: 2
```

Success proof:

```text
completed: 23/23
failedItemId: null
activeItemId: null
expectedScreenshotCount: 18
actualScreenshotCount: 18
all item statuses: pass
```

### 3.7. Fail-closed screenshot accounting

Проверяются одновременно:

```text
sum(item.expectedScreenshots)
= plan.expectedScreenshotCount
= screenshots.length
= фактические browser screenshots
= 18
```

Каждый item также проверяет свой screenshot delta. Существующие независимые PowerShell guards сохранены:

- 10 dashboard page screenshots;
- 6 real-deck native-preview screenshots;
- 2 Cards state screenshots;
- zero synthetic screenshots.

### 3.8. Сохранённые diagnostics

Не изменена семантика:

```text
consoleEvents
pageErrors
failedRequests
unexpectedExternalRequests
```

Сохранены:

- favicon filtering;
- external origin boundary;
- console failure только для `type === "error"`;
- Playwright `requestfailed` как network failure, а не автоматический HTTP 4xx/5xx failure;
- URL token redaction.

## 4. Тесты

Добавлены:

```text
tests/browser_progress.test.mjs
tests/test_browser_progress_node.py
```

Обновлены профильные contract tests:

```text
tests/test_e2e_screenshot_contract.py
tests/test_telemetry_e2e_harness.py
tests/test_docker_smoke_helpers.py
tests/test_e2e_harness_reuse.py
```

Focused Node tests проверяют:

- deterministic plan;
- 18 screenshots;
- telemetry conditionality;
- START перед operation;
- PASS duration/delta;
- exact FAIL item;
- original exception rethrow;
- producer failure hard-fail;
- unknown/duplicate item rejection;
- screenshot mismatch failure;
- deterministic slowest sorting;
- safe error summary.

Статические Python tests проверяют:

- plan создаётся и печатается до Chromium launch;
- direct `playwright` import сохранён;
- `@playwright/test` и retries отсутствуют;
- safe `execFile` adapter;
- schema-v1 `message/info` integration;
- diagnostics и `networkidle` сохранены;
- Docker copy включает новый `.mjs`;
- harness reuse allowlist включает только профильные E2E files/tests.

## 5. Хронология cloud verification

### 5.1. Первый Fast CI

```text
Run: 30046170723
SHA: 8ac1e471823e876986a24ceebe2e231b58385941
Result: FAIL
```

Причина: старый test assertion искал literal preview-anchor list непосредственно в `smoke-browser.mjs`, хотя source of truth был вынесен в plan module.

### 5.2. Второй Fast CI

```text
Run: 30046963209
SHA: 1c0d8181beb701098ab24b81c35d4ddb69155eb2
Result: FAIL
```

Причина: промежуточный assertion ожидал прямой импорт `PREVIEW_ANCHOR_IDS`, но entrypoint корректно исполняет plan items по `candidate.kind === "native-preview"`.

Production code ради старых tests не изменялся. Финальный test проверяет фактическую архитектуру: `buildBrowserPlan`, native-preview item execution и anchor constants в plan module.

### 5.3. Финальный Fast CI

```text
Run ID: 30048028664
Result: PASS
Branch: platform/e2e-i2-browser-smoke-progress
Tested SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Run attempt: 1
Structured duration: 139375 ms
```

Проверки:

```text
Vitest: 69 files, 342 tests — PASS
pytest: 909 passed, 2 skipped — PASS
Vite build/bundle/assets copy — PASS
package build/check — PASS
exact package metadata/check — PASS
run-events.jsonl — PASS
```

Fast CI diagnostics artifact:

```text
ID: 8579972296
Name: ci-fast-30048028664-1
Digest: sha256:79cb979ac38c0bb2718eb87d3d4acb26cdd17262981f23e264c85fb18bd76756
```

Exact package artifact:

```text
ID: 8579972839
Name: ci-package-e25bd0b24e32ce4717ed2dbda138d802f707f6d5-30048028664-1
Artifact digest: sha256:47674f11d057c32139e121672129291e09581db30041dc3f83cc558b3ed06a3b
Inner .ankiaddon SHA-256: 5cff912c3ea9ae03b1c495b28699c3c93d7ac9c12b84832d1765d77fe518ddc2
```

Новый package-producing Fast CI был необходим: current branch включал merged E2E-I1 documentation changes вне fail-closed harness-only allowlist относительно старого package SHA.

## 6. Targeted real-Anki proof

```text
Run ID: 30049216529
Job: Real Anki Desktop (standard / cards)
Result: PASS
Mode: standard
Scope: cards
Verify restart: false
Resource telemetry: true
Screenshot workers: 3
Fast CI source run: 30048028664
Package tested SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
E2E checkout SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Package source: fast-ci-artifact
Workflow duration: 102 s
Canonical duration: 31.377 s
Browser phase: 19.552 s
Browser item evidence duration: 19.305 s
Screenshots: 18
```

Artifact:

```text
ID: 8580366654
Name: ci-e2e-standard-30049216529-1
Size: 5693318 bytes
Digest: sha256:04d3945e594c01cf292fb1f7a2a56e4734ccc37e27bd094cd27f9d5cb92127a7
```

GitHub artifact transport digest и SHA-256 внутреннего `.ankiaddon` являются разными identities и проверяются отдельно.

### Browser result

```text
ok: true
browser report schema: 2
plan schema: 1
items: 23
completed: 23
failed: 0
expected screenshots: 18
actual screenshots: 18
```

Diagnostics:

```text
consoleEvents: 0
pageErrors: 0
failedRequests: 0
unexpectedExternalRequests: 0
```

### Slowest browser items

| Item | Duration |
| --- | ---: |
| `cards-route.light` | 2015 ms |
| `cards-route.dark` | 1901 ms |
| `route.home.light` | 1566 ms |
| `preview.grammar-preview` | 1238 ms |
| `preview.words-preview` | 1229 ms |

Эти значения являются observational evidence. Performance threshold не вводился.

## 7. Что намеренно не запускалось

```text
второй targeted run: не запускался — первый required proof прошёл
standard/full: не запускался — runner/artifact lifecycle не требовал full по test matrix
restart: false — targeted cards proof
perf100: не запускался
warm repeat: не запускался
worker comparison: не запускался
intentionally failing cloud run: не запускался
local full Docker после cloud PASS: не запускался
```

Controlled failure доказан focused Node test, а не намеренно сломанным cloud E2E.

## 8. Completion criteria

| Критерий | Результат |
| --- | --- |
| Plan до Chromium launch | PASS |
| Deterministic machine-readable plan | PASS |
| START/PASS/FAIL для значимых items | PASS |
| Live current/total | PASS |
| Per-item duration | PASS |
| Exact route/theme/anchor/step | PASS |
| Partial failure evidence | PASS |
| Browser report plan/items/slowest | PASS |
| Screenshot accounting = 18 | PASS |
| Existing route/preview/Cards coverage | PASS |
| Existing diagnostics semantics | PASS |
| Valid schema-v1 run-events | PASS |
| Dynamic global phase IDs отсутствуют | PASS |
| Direct Playwright Library сохранён | PASS |
| Retries/visual regression не добавлены | PASS |
| Focused tests | PASS |
| Fast CI exact package | PASS |
| Один required real-Anki proof | PASS |
| Closeout/documentation | PASS |
| E2E-I3–I6 не реализованы | PASS |

## 9. Остаточные границы

1. `failureCode` остаётся `null`; stable taxonomy относится к `E2E-I3`.
2. Общий `failure-summary.json` не создан; это `E2E-I3`.
3. Cancellation/preflight UX не менялся; это `E2E-I4`.
4. Unique non-release build identity не добавлялась; это `E2E-I5`.
5. Общий canonical final summary/history storage не реализован; это `E2E-I6`.
6. Item timings не являются performance gate.
7. Artifact ZIP не коммитится в repository; report сохраняет run/artifact identities и digests.

Ни одна из этих границ не блокирует завершение `E2E-I2`.

## 10. Решение

```text
E2E-I2: COMPLETE
```

Следующий отдельный этап:

```text
E2E-I3 — Stable failure diagnostics
```

Он не начат в этой ветке. PR открывается отдельно в `core`, без merge и auto-merge.