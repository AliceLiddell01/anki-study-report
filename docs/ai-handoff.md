# Передача контекста ИИ — Anki Study Report

**Снимок:** 2026-07-24

## С чего начать

Читайте источники в таком порядке:

1. [`../README.md`](../README.md);
2. этот файл;
3. [`../roadmap/README.md`](../roadmap/README.md);
4. профильный README соответствующего трека;
5. актуальные production-код и тесты в пределах задачи;
6. профильный контракт и последний closeout соответствующего этапа.

При противоречиях:

```text
актуальные production-код и тесты
→ актуальные README и профильные документы
→ свежие отчёты и артефакты
→ старые планы и сообщения
→ предположения
```

Не утверждайте, что файл, artifact или участок кода изучен, если он фактически не был открыт.

## Проект

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

Dashboard:

- доступен только через loopback;
- защищён token;
- получает ограниченные JSON/API-проекции;
- не предоставляет frontend прямой доступ к collection;
- рендерит карточки через sanitizer и Shadow DOM без JavaScript execution surface.

## Текущий Core

```text
base branch: core
current core head: 38483b3c6ff59f7bc71b03806e9dcdaadb255fa3
C1: завершён
C2 implementation/integration: завершены
C2 owner acceptance: повторно открыта после ручной UI-проверки
post-C2 manual acceptance remediation: отдельная задача, не входит в Platform
C3–C6: обязательный будущий путь к Core 1.0
release: не начат
```

Обязательный продуктовый путь:

```text
post-C2 manual acceptance remediation
→ C3 Core UI & Shell Consolidation
→ C4 First-party Data Independence
→ C5 Today v2
→ C6 Profile v2 Foundation
→ Core 1.0 owner acceptance
→ отдельное решение о release
```

Platform/CI не должен автоматически менять или блокировать эту очередь без явно документированной dependency.

## Текущий Platform / CI

```text
working branch: platform/e2e-i2-browser-smoke-progress
base branch: core
merge base: 38483b3c6ff59f7bc71b03806e9dcdaadb255fa3
E2E-I1: COMPLETE, merged через PR #134
E2E-I2: COMPLETE на feature branch
E2E-I2 PR: #135, open, not merged
E2E-I3: следующий, не начат
E2E-I4–I6: запланированы
merge/auto-merge E2E-I2: не выполнялись
release: не выполнялся
```

### E2E-I1

Единый schema-v1 lifecycle Fast CI и Docker E2E:

```text
Fast CI stream: ci-fast/run-events.jsonl
Docker stream: reports/run-events.jsonl
Public stream: artifacts/reports/run-events.jsonl
```

Подтверждение:

```text
implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Fast CI: 30039103625 — PASS
standard/full: 30039372012 — PASS
standard/full: 30039708429 — PASS
PR #134: merged
core merge SHA: 38483b3c6ff59f7bc71b03806e9dcdaadb255fa3
```

### E2E-I2

Детерминированный item-level browser smoke progress без миграции на `@playwright/test`.

Финальный implementation:

```text
SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Fast CI: 30048028664 — PASS
standard/cards: 30049216529 — PASS
PR: #135 — OPEN
```

Exact Fast CI package:

```text
artifact ID: 8579972839
artifact name: ci-package-e25bd0b24e32ce4717ed2dbda138d802f707f6d5-30048028664-1
artifact digest: sha256:47674f11d057c32139e121672129291e09581db30041dc3f83cc558b3ed06a3b
inner .ankiaddon SHA-256: 5cff912c3ea9ae03b1c495b28699c3c93d7ac9c12b84832d1765d77fe518ddc2
```

Targeted E2E artifact:

```text
artifact ID: 8580366654
artifact name: ci-e2e-standard-30049216529-1
artifact digest: sha256:04d3945e594c01cf292fb1f7a2a56e4734ccc37e27bd094cd27f9d5cb92127a7
mode/scope: standard/cards
restart: false
resource telemetry: true
screenshot workers: 3
workflow duration: 102 s
canonical duration: 31.377 s
```

Browser proof:

```text
plan schema: 1
browser report schema: 2
items: 23/23 PASS
screenshots: 18/18
failedItemId: null
activeItemId: null
pageErrors: 0
failedRequests: 0
unexpectedExternalRequests: 0
console errors: 0
run-events final: run/pass
```

## Browser smoke contract

Source of truth:

```text
docker/anki-e2e/browser-progress.mjs
```

Plan создаётся до `chromium.launch()` и содержит stable IDs/kinds/order/counts.

Фактические kinds:

```text
browser-launch
dashboard-setup
route-capture
telemetry
native-preview
scenario-cards
cards-route
diagnostics
```

Coverage:

```text
5 dashboard routes × light/dark = 10 screenshots
3 native preview anchors × light/dark = 6 screenshots
Cards state light/dark = 2 screenshots
Итого = 18
```

Routes:

```text
home
cards
decks
profile
settings
```

Preview anchors:

```text
words-preview
grammar-preview
java-preview
```

Telemetry stages:

```text
declined
reliability
feature
offline
```

`BrowserProgress.run()`:

- запрещает unknown и duplicate item;
- печатает START до operation;
- использует `performance.now()`;
- проверяет screenshot delta;
- сохраняет PASS/FAIL и partial report;
- повторно бросает исходную ошибку;
- не выполняет retries.

## Run-event integration

Global schema остаётся v1:

```text
phaseId=browser-smoke-first
eventKind=message
status=info
current/total=item order/plan count
failureCode=null
```

Dynamic browser phase IDs не добавлены.

Node adapter использует `execFile`, array arguments и `shell: false`. Non-zero producer exit hard-fails browser item.

## Evidence paths

```text
reports/browser-smoke-first.json     schema v2
reports/screenshot-performance.json  schema v2
reports/run-events.jsonl              schema v1
artifact-manifest.json                schema v2
```

Browser report содержит:

```text
plan
progress
items
slowestItems
```

и сохраняет прежние anchors/scenarios/Cards/telemetry/screenshots/diagnostics fields.

## Fail-closed screenshot accounting

```text
sum(item.expectedScreenshots)
= plan.expectedScreenshotCount
= screenshots.length
= 18
```

Дополнительно PowerShell wrapper независимо проверяет:

```text
10 page screenshots
6 real-deck preview screenshots
0 synthetic screenshots
Cards state screenshots в общем artifact contract
```

## Diagnostics semantics

Сохраняются:

```text
consoleEvents
pageErrors
failedRequests
unexpectedExternalRequests
```

- favicon failure фильтруется;
- HTTP 4xx/5xx сам по себе не считается Playwright `requestfailed`;
- external origin запрещён;
- console failure — только `type === "error"`;
- token удаляется из URL evidence.

## Package/harness policy

Новый package-producing Fast CI нужен, если diff может изменить `.ankiaddon` bytes/production behavior либо complete-diff reuse validator отклоняет reuse.

Harness-only reuse разрешён только через:

```text
scripts/validate_e2e_harness_reuse.py
```

Нельзя вручную объявить arbitrary diff безопасным.

Docs-only commits после успешного required proof не требуют повторного Fast CI/Docker без отдельной причины.

## Verification policy

Для browser progress changes минимум:

```text
node --check docker/anki-e2e/browser-progress.mjs
node --check docker/anki-e2e/smoke-browser.mjs
node --test tests/browser_progress.test.mjs
pytest профильных browser/run-event/screenshot/reuse tests
git diff --check
```

Обычный harness-only browser change требует одного risk-appropriate:

```text
mode=standard
scope=cards
verify_restart=false
resource_telemetry=true
```

Full нужен только при изменении shared runner/artifact/restart lifecycle.

Не запускать без отдельной задачи:

- второй successful run «для уверенности»;
- `perf100`;
- warm repeat;
- worker comparison;
- intentionally failing cloud run.

## Security invariants

Не ослаблять:

- loopback-only server;
- token validation;
- sanitizer и parser-backed CSS policy;
- media validation;
- action allowlists;
- APKG checksum/inventory/anchor validation;
- exact package/GHCR identity;
- public artifact redaction.

Не публиковать:

- token/credential;
- token-bearing URL;
- Authorization headers;
- absolute private paths;
- card HTML/user content;
- environment dump;
- raw stack в live progress.

## Cards и Inspection Profiles — краткие продуктовые инварианты

Card identity:

```text
Browser question
→ reviewer front
→ media_only | unavailable
```

Используются:

```text
displayText
displaySource
displayStatus
displayTruncated
```

Preview:

- compact — санитизированная native front;
- expanded modal — санитизированная native back;
- full preview только для active card;
- queue rows не читают media и не рендерят полный HTML;
- JavaScript карточек не выполняется.

Inspection Profiles:

```text
note type
→ Basic draft
→ bounded validation/sample
→ explicit confirmation
```

Unconfirmed/stale/corrupt profiles работают fail closed.

## Актуальные документы Platform

- [`run-event-protocol.md`](run-event-protocol.md);
- [`docker-e2e.md`](docker-e2e.md);
- [`test-matrix.md`](test-matrix.md);
- [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md);
- [`../roadmap/platform/README.md`](../roadmap/platform/README.md);
- [`../roadmap/platform/e2e-observability-build-identity.md`](../roadmap/platform/e2e-observability-build-identity.md).

Closeout:

- [`../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md);
- [`../reports/ci/e2e-i2-browser-smoke-progress-closeout.md`](../reports/ci/e2e-i2-browser-smoke-progress-closeout.md).

## Следующий допустимый Platform stage

```text
E2E-I3 — Stable failure diagnostics
```

Он должен начинаться как отдельная bounded задача. Не реализовывать в рамках текущей ветки:

- stable global failure codes;
- общий `failure-summary.json`;
- cancellation/preflight redesign;
- build identity;
- canonical final summary/history;
- retries/visual regression/performance thresholds.