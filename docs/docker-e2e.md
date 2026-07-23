# Docker E2E

**Снимок документации:** 2026-07-24.

Подробная техническая инструкция: [`../docker/anki-e2e/README.md`](../docker/anki-e2e/README.md).

Связанные контракты:

- правила запусков: [`verification-run-policy.md`](verification-run-policy.md);
- package/harness reuse: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md);
- live run events и browser items: [`run-event-protocol.md`](run-event-protocol.md);
- test classification: [`test-matrix.md`](test-matrix.md).

## Назначение

Docker E2E устанавливает exact add-on package в реальный Anki Desktop 26.05 внутри изолированного Linux-профиля и проверяет runtime-риски, которые не закрываются pytest/Vitest:

- startup hooks и profile lifecycle;
- loopback token-protected dashboard;
- exact package installation layout;
- native card rendering и Shadow DOM;
- real audio/GIF/image media;
- Cards, Triage, exact recheck и Inspection Profiles;
- telemetry lifecycle и restart persistence;
- browser console/page/request/network behavior;
- deterministic browser plan, item progress и screenshot accounting;
- public artifact sanitizer и exact identities.

Полный real-Anki Docker E2E является integration gate, а не обычным циклом разработки.

## Источник collection

Контур использует только committed рабочие APKG:

```text
fixtures/real-decks/Words__N1.apkg
fixtures/real-decks/文法__N5.apkg
fixtures/real-decks/Java.apkg
fixtures/real-decks/manifest.json
```

Запрещены:

- synthetic notes/cards/templates/media;
- runtime generation content fixtures;
- fallback на искусственную collection;
- ручное редактирование imported content ради теста.

Scheduling/revlog/due/interval/ease/suspended/buried scenarios могут изменяться, но notes/cards/templates/media не клонируются и не переписываются.

## Exact package identity

Cloud E2E принимает:

```text
manual run → exact successful Fast CI artifact
release run → exact release artifact
```

Cloud source-build fallback запрещён.

Для Fast CI source проверяются отдельно:

- Fast CI run ID;
- tested commit SHA;
- artifact ID/name/digest;
- `.ankiaddon` SHA-256;
- E2E checkout SHA;
- package source mode;
- ancestry и complete diff при harness-only reuse.

GitHub artifact transport digest и SHA-256 внутреннего `.ankiaddon` являются разными identities.

## Environment identity

Cloud consumer использует immutable GHCR digest:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:<digest>
```

Проверяются:

- digest;
- `linux/amd64` platform;
- environment contract SHA-256;
- publication/reuse proof;
- resolved Compose contract.

Local Docker build разрешён только как development/diagnostic fallback.

## Основной execution contour

1. Проверить mode/scope/runtime inputs.
2. Разрешить exact Fast CI/release package.
3. Проверить package metadata и SHA-256.
4. Подтвердить immutable GHCR environment.
5. Создать fresh profile и empty collection.
6. Импортировать три real APKG через public Anki importer.
7. Построить inventory и доказать zero synthetic content.
8. Разрешить stable anchors по GUID/template ordinal.
9. Применить только scheduling/state scenarios.
10. Установить add-on package.
11. Запустить Anki и дождаться readiness.
12. Выполнить API smoke.
13. Выполнить plan-driven browser smoke.
14. Для full scope — restart и restart-specific API/telemetry proof.
15. Сформировать manifest и public-safe artifact.
16. Валидировать run-event stream и artifact inventory.
17. Очистить Docker state.
18. Восстановить canonical result.

## Scope и restart

Поддерживаемые scopes:

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

`verify_restart=auto` означает restart только для `full`.

Для `E2E-I2` required proof использован:

```text
mode=standard
scope=cards
verify_restart=false
resource_telemetry=true
screenshot_workers=auto → 3
```

## Unified run lifecycle

Docker orchestration пишет:

```text
reports/run-events.jsonl
```

Public exporter копирует validated stream в:

```text
artifacts/reports/run-events.jsonl
```

Крупные phases сохраняются stable и registry-backed. Browser smoke остаётся одной phase:

```text
browser-smoke-first
```

Item-level progress передаётся как schema-v1 `message/info` с `current/total`.

## Browser smoke plan

Plan строится в `docker/anki-e2e/browser-progress.mjs` до `chromium.launch()`.

Поля:

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

Фактический plan при включённой telemetry:

| Kind | Items | Screenshots |
| --- | ---: | ---: |
| browser launch | 1 | 0 |
| dashboard setup | 1 | 0 |
| route capture | 10 | 10 |
| telemetry stages | 4 | 0 |
| native previews | 3 | 6 |
| scenario cards | 1 | 0 |
| Cards state | 2 | 2 |
| final diagnostics | 1 | 0 |
| **Всего** | **23** | **18** |

Telemetry items отсутствуют, если endpoint выключен. Screenshot total остаётся 18.

## Browser coverage

### Dashboard routes

Две themes для каждого route:

```text
home
cards
decks
profile
settings
```

Итого: 10 page screenshots.

Сохраняются:

- `page.goto(..., waitUntil: "networkidle")`;
- structural `main` assertion;
- exact hash assertion;
- theme bootstrap через init script;
- dialog dismissal;
- desktop viewport.

### Native previews

Один item на anchor:

```text
preview.words-preview
preview.grammar-preview
preview.java-preview
```

Каждый item включает:

- `/api/search/inspect`;
- exact card validation;
- `renderSource === "anki_native"`;
- front/back HTML;
- raw sound/play marker prohibition;
- expected HTML classes;
- Shadow DOM rendering;
- script prohibition;
- light и dark screenshots.

Итого: 6 screenshots.

### Cards scenarios

`scenario.cards` проверяет:

- action/recheck candidate;
- low-success candidate;
- suspended queue state;
- buried queue state;
- zero cloned content.

`cards-route.light` и `cards-route.dark` проверяют:

- Cards route rendering;
- zero raw AV markers;
- zero horizontal overflow;
- real-deck inbox screenshots.

Итого: 2 state screenshots.

### Telemetry stages

При включённом endpoint plan содержит:

```text
telemetry.declined
telemetry.reliability
telemetry.feature
telemetry.offline
```

Сохраняются:

- zero outbound при declined consent;
- purpose isolation;
- batch delivery;
- bounded UI queueing duration;
- offline persistent queue proof.

Каждая из 25 API event submissions не становится отдельным item.

## Item lifecycle

`BrowserProgress.run()`:

- запрещает unknown/duplicate item;
- немедленно печатает START;
- пишет safe run-event message;
- использует `performance.now()`;
- проверяет screenshot delta;
- сохраняет PASS/FAIL;
- пишет partial report;
- повторно бросает исходную ошибку;
- не выполняет retries.

Пример:

```text
[BROWSER] PLAN items=23 screenshots=18 telemetry=true
[BROWSER] [3/23] START route-capture item=route.home.light route=#/home theme=light
[BROWSER] [3/23] PASS route-capture item=route.home.light duration=1566ms screenshots=1
```

## Structured browser evidence

Основной report:

```text
reports/browser-smoke-first.json
schemaVersion: 2
```

Содержит:

```text
ok
label
plan
progress
items
slowestItems
anchors
scenarioCards
cardsRoute
telemetryClient
screenshots
consoleEvents
pageErrors
failedRequests
unexpectedExternalRequests
screenshotPerformance
error — только failure/raw diagnostics
```

Performance report:

```text
reports/screenshot-performance.json
schemaVersion: 2
```

Per-item record:

```text
id
kind
status
order
durationMs
expectedScreenshots
actualScreenshots
screenshotPaths
route/theme/anchorId/step — применимые поля
errorType/safeErrorSummary — failure only
```

`slowestItems` — top-5, сортировка duration descending, затем stable order.

Performance values informational и не являются gate.

## Screenshot accounting

Browser smoke fail closed проверяет:

```text
sum(expectedScreenshots)
= plan.expectedScreenshotCount
= screenshots.length
= 18
```

Каждый item проверяет собственный delta.

PowerShell wrapper независимо требует:

```text
10 page screenshots
6 real-deck preview screenshots
0 synthetic/legacy screenshots
2 Cards state screenshots в общем artifact contract
```

## Browser diagnostics

Сохраняются arrays:

```text
consoleEvents
pageErrors
failedRequests
unexpectedExternalRequests
```

Semantics:

- `requestfailed` — network-level failure;
- HTTP error response сам по себе не является `requestfailed`;
- favicon failure отфильтровывается;
- external origin запрещён;
- console failure — только `type === "error"`;
- token удаляется из URL evidence.

## Failure evidence

При browser failure report содержит:

```text
failedItemId
activeItemId
completed/total
expected/actual screenshot count
item kind
route/theme/anchorId/step
item duration
errorType
safeErrorSummary
raw error stack в существующем error field
```

Run-event message не содержит raw stack или private values. До `E2E-I3`:

```text
failureCode = null
```

Controlled failure проверяется focused Node test; намеренно сломанный cloud E2E не требуется.

## Public artifact

Success artifact обязан содержать:

- artifact manifest schema v2;
- exact `.ankiaddon`;
- Fast CI handoff;
- GHCR provenance;
- real-deck manifest/import/inventory/anchors/scenarios;
- API report;
- browser report schema v2;
- screenshot performance schema v2;
- run-events JSONL;
- 18 screenshots;
- resource evidence, если включено;
- redacted readiness и diagnostics.

Public exporter:

1. валидирует source manifest/stream;
2. копирует allowlisted evidence;
3. redacts token/private paths;
4. сканирует secret-like text;
5. валидирует public copy.

## Canonical commands

Local source-build diagnostic:

```powershell
.\scripts\run_anki_e2e_docker.ps1 -Mode standard -Scope cards
```

Cloud targeted proof:

```bash
gh workflow run ci-e2e.yml \
  --repo AliceLiddell01/anki-study-report \
  --ref <branch> \
  -f mode=standard \
  -f scope=cards \
  -f screenshot_workers=auto \
  -f resource_telemetry=true \
  -f verify_restart=false \
  -f fast_ci_run_id=<successful-fast-ci-run>
```

## Подтверждение E2E-I2

```text
implementation SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Fast CI: 30048028664 — PASS
standard/cards: 30049216529 — PASS
artifact: ci-e2e-standard-30049216529-1
artifact ID: 8580366654
artifact digest: sha256:04d3945e594c01cf292fb1f7a2a56e4734ccc37e27bd094cd27f9d5cb92127a7
screenshots: 18
browser items: 23/23 PASS
page/request/external/console errors: 0
```

Итоговый отчёт: [`../reports/ci/e2e-i2-browser-smoke-progress-closeout.md`](../reports/ci/e2e-i2-browser-smoke-progress-closeout.md).