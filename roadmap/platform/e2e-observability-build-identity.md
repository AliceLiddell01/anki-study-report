# Roadmap наблюдаемости E2E, диагностики и идентичности сборки

**Статус:** в работе; `E2E-I1` и `E2E-I2` завершены, следующий этап — `E2E-I3`  
**Трек:** Platform / CI  
**База:** real-deck E2E foundation из PR #133  
**Scope:** наблюдаемость Fast CI и real-Anki Docker E2E, диагностика, cancellation, preflight, non-release build identity и performance evidence.

## Зачем существует этот roadmap

Real-deck E2E foundation уже предоставляет сильный execution contour:

- exact handoff пакета из Fast CI или release;
- три committed рабочие APKG;
- детерминированные сценарии реальных карточек без synthetic content;
- API, browser, restart, telemetry и artifact evidence;
- structured Fast CI timing и E2E phase/resource telemetry;
- разделение package/harness identities с fail-closed reuse.

Оставшаяся задача — сделать этот contour наблюдаемым и однозначным без ручного восстановления по нескольким слоям PowerShell, Bash, Python, Node.js и GitHub Actions.

Roadmap разделён ровно на шесть крупных этапов. Implementation tasks и commits не создают дополнительных уровней `I2.1`, `I2a` и подобных.

## Общие инварианты

Ни один этап не должен:

- ослаблять exact package identity;
- разрешать cloud source-build fallback;
- менять production payload только на одной стороне;
- открывать dashboard server наружу;
- логировать dashboard token или token-bearing URL;
- ослаблять sanitizer, media validation, action allowlists или APKG checks;
- коммитить runtime artifacts, screenshots, logs, tokens или `.ankiaddon`;
- заменять real-Anki gate synthetic-only tests;
- добавлять retries вместо устранения root cause;
- превращать item progress в dynamic global phase registry;
- вводить performance threshold без отдельного measurement decision.

Внешние API подтверждают поведение инструментов, но внутренний контракт определяется production code, tests и этим roadmap.

## Текущее состояние

```text
E2E-I1 — COMPLETE
E2E-I2 — COMPLETE
E2E-I3 — следующий, не начат
E2E-I4 — запланирован
E2E-I5 — запланирован
E2E-I6 — запланирован
```

## E2E-I1 — Единый live run protocol

**Статус:** `COMPLETE`.

### Цель

Создать один schema-versioned lifecycle contract для Fast CI и Docker E2E, чтобы крупные phases были видны live и сохранялись как deterministic JSONL evidence.

### Реализовано

- `docker/anki-e2e/run_event_protocol.py`;
- producers `fast-ci` и `docker-e2e`;
- stable run/phase registries;
- immediate console output;
- deterministic UTF-8 JSONL;
- cross-process append и locking;
- schema/security validation;
- success/failure/cancel lifecycle;
- artifact manifest/public exporter integration;
- transient sidecar exclusion;
- plain non-interactive Docker Compose output;
- controlled failure и concurrency tests.

### Evidence paths

```text
Fast CI: ci-fast/run-events.jsonl
Docker: reports/run-events.jsonl
Public: artifacts/reports/run-events.jsonl
```

### Подтверждение

```text
implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Fast CI: 30039103625 — PASS
standard/full: 30039372012 — PASS
standard/full: 30039708429 — PASS
PR #134: merged
core merge SHA: 38483b3c6ff59f7bc71b03806e9dcdaadb255fa3
```

### Не реализовано в I1

- browser route/theme/preview item progress;
- stable failure taxonomy;
- cancellation/preflight redesign;
- unique non-release build identity;
- canonical final summary/history.

Closeout: [`../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md).

## E2E-I2 — Прогресс browser smoke

**Статус:** `COMPLETE`.

### Цель

Устранить длинный silent interval внутри direct Playwright Library browser smoke и показать точный route/theme/anchor/telemetry step без миграции на `@playwright/test`.

### Реализовано

- deterministic plan до `chromium.launch()`;
- stable item IDs и known kinds;
- единый `BrowserProgress.run()` wrapper;
- `PLAN`, `START`, `PASS`, `FAIL`, `[current/total]`;
- monotonic `performance.now()` durations;
- per-item screenshot contribution;
- partial failure report;
- exact active/failed item;
- deterministic top-5 slowest items;
- browser report schema v2;
- screenshot performance schema v2;
- schema-v1 `message/info` integration с `phaseId=browser-smoke-first`;
- Node → Python `execFile` adapter без shell interpolation;
- fail-closed 18-screenshot parity;
- focused Node/Python tests;
- один targeted real-Anki proof.

### Фактический plan

```text
items: 23
screenshots: 18
browser-launch: 1
dashboard-setup: 1
route-capture: 10
telemetry: 4
native-preview: 3
scenario-cards: 1
cards-route: 2
diagnostics: 1
```

Stable groups:

```text
browser.launch
dashboard.setup
route.<route>.<theme>
telemetry.<step>
preview.<anchor>
scenario.cards
cards-route.<theme>
diagnostics.final
```

### Coverage сохранён

```text
5 routes × 2 themes = 10 screenshots
3 native preview anchors × 2 themes = 6 screenshots
Cards state light/dark = 2 screenshots
Итого = 18
```

Сохраняются:

- `networkidle` route navigation;
- structural/hash assertions;
- theme bootstrap;
- native render/Shadow DOM/script/AV checks;
- Cards overflow checks;
- page/request/external/console diagnostics;
- token redaction;
- direct `playwright` import.

### Run-event integration

Global schema v1 не менялась:

```text
phaseId=browser-smoke-first
eventKind=message
status=info
current/total=item position/plan count
failureCode=null
```

Dynamic browser phase IDs не добавлены.

### Structured evidence

```text
reports/browser-smoke-first.json    schema v2
reports/screenshot-performance.json schema v2
reports/run-events.jsonl             schema v1
```

Browser report содержит:

```text
plan
progress
items
slowestItems
```

и сохраняет прежние diagnostics/proof fields.

### Подтверждение

```text
implementation SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Fast CI: 30048028664 — PASS
standard/cards: 30049216529 — PASS
artifact ID: 8580366654
artifact digest: sha256:04d3945e594c01cf292fb1f7a2a56e4734ccc37e27bd094cd27f9d5cb92127a7
browser items: 23/23 PASS
screenshots: 18/18
page/request/external/console errors: 0
```

### Что намеренно не запускалось

- `standard/full`;
- restart;
- `perf100`;
- warm repeat;
- worker comparison;
- intentionally failing cloud run;
- второй successful targeted run.

Targeted `standard/cards` был достаточен: изменения затрагивали browser harness/report evidence, но не общий restart lifecycle.

### Не реализовано в I2

- stable global failure codes;
- общий `failure-summary.json`;
- cancellation/preflight redesign;
- unique build identity;
- canonical summary/history;
- retries;
- visual regression;
- performance gates.

Closeout: [`../../reports/ci/e2e-i2-browser-smoke-progress-closeout.md`](../../reports/ci/e2e-i2-browser-smoke-progress-closeout.md).

## E2E-I3 — Stable failure diagnostics

**Статус:** следующий, не начат.

### Цель

Сделать первичный функциональный failure однозначным между Fast CI, Docker orchestration, browser smoke, public artifact и GitHub summary.

### В scope

- bounded stable `failureCode` taxonomy;
- primary failure vs secondary cleanup/upload failures;
- один canonical `failure-summary.json`;
- exact phase/item identity;
- safe error category/summary;
- links/paths на существующие raw diagnostics;
- controlled tests для разных failure classes;
- backward-compatible integration с schema-v1 events или явная schema migration.

### Требования

Failure summary должен различать минимум:

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
```

Точная taxonomy определяется после аудита текущих failure paths. Не использовать arbitrary exception text как stable code.

### Out of scope

- cancellation mechanics (`E2E-I4`);
- build identity (`E2E-I5`);
- historical performance dashboard (`E2E-I6`);
- retries/quarantine.

### Completion criteria

- first root cause не теряется за final wrapper exception;
- primary и secondary failures различимы;
- public summary не содержит secrets/private paths;
- run-events/artifact remain valid;
- controlled failure evidence покрывает taxonomy;
- один risk-appropriate cloud proof после concrete implementation.

## E2E-I4 — Cancellation и preflight

**Статус:** запланирован.

### Цель

Сделать cancel/preflight отдельным однозначным lifecycle, не смешанным с функциональным failure.

### В scope

- explicit preflight result;
- cancel propagation между workflow, PowerShell, Compose и container;
- cleanup after cancellation;
- terminal `run/cancel` consistency;
- artifact policy для cancelled runs;
- concurrency cancellation behavior.

### Out of scope

- changing product behavior;
- automatic retries;
- build identity;
- performance history.

## E2E-I5 — Non-release build identity

**Статус:** запланирован.

### Цель

Назначить однозначную идентичность exact non-release build, независимо от workflow display names и человеческих labels.

### В scope

- build identity schema;
- package tested SHA;
- package artifact ID/digest;
- inner package SHA-256;
- harness SHA;
- workflow source SHA;
- GHCR environment digest;
- source/reuse mode;
- canonical identity in summaries/artifacts.

### Инварианты

- package и harness identities остаются независимыми;
- docs commit не притворяется package identity;
- artifact transport digest не заменяет inner package hash;
- release identity остаётся отдельным contract.

## E2E-I6 — Canonical final summary и history

**Статус:** запланирован.

### Цель

Свести compatible evidence в один canonical final summary и определить bounded history для измерений.

### В scope

- canonical run summary;
- compatible-run comparison rules;
- phase/item performance aggregation;
- p50/p95 только для сопоставимых contours;
- first-run pass rate;
- artifact footprint;
- retention/history format;
- observational regression reporting.

### Не входит автоматически

- blocking performance thresholds;
- runner upgrade;
- cache/retry/split optimization;
- external telemetry service.

Любая оптимизация активируется отдельно через CI 7–10 после измеренного bottleneck.

## Verification policy для всех E2E-I этапов

1. Классифицировать diff: package-impacting, harness-only или docs-only.
2. Запустить focused tests и syntax checks.
3. Controlled failure проверять локально/focused, если cloud failure не нужен.
4. Новый Fast CI запускать только по package/reuse boundary.
5. Выполнить ровно один risk-required real-Anki proof после последнего concrete fix.
6. После failure сначала изучить artifact/log/root cause.
7. Не повторять successful unchanged package/harness pair.
8. Docs-only closeout commits после successful gates не требуют нового Docker/Fast CI.

## Security boundary

Structured progress/failure/build evidence может содержать только:

- stable IDs;
- bounded enums;
- durations/counts;
- safe relative paths;
- exact public SHA/digest identities;
- sanitized summary.

Запрещены:

- token/credentials;
- token-bearing URL;
- authorization headers;
- private absolute paths;
- card HTML/user content;
- arbitrary environment dump;
- raw stack в live progress.

## Следующий допустимый шаг

```text
E2E-I3 — Stable failure diagnostics
```

Он должен быть отдельной bounded веткой/задачей. Завершение `E2E-I2` не разрешает автоматически начинать `E2E-I4–I6` или CI optimization stages.