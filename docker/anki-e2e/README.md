# Docker real-Anki E2E

**Снимок документации:** 2026-07-24.

Этот контур запускает exact add-on package в реальном Anki Desktop 26.05 внутри Docker, поднимает loopback token-protected dashboard и проверяет API, browser behavior, native rendering, media, telemetry, restart, live run lifecycle и публично безопасные artifacts.

Полный Docker E2E — integration gate.

Связанные контракты:

- политика запусков: [`../../docs/verification-run-policy.md`](../../docs/verification-run-policy.md);
- package/harness reuse: [`../../docs/e2e-package-harness-reuse.md`](../../docs/e2e-package-harness-reuse.md);
- run events и browser items: [`../../docs/run-event-protocol.md`](../../docs/run-event-protocol.md);
- обзор Docker E2E: [`../../docs/docker-e2e.md`](../../docs/docker-e2e.md).

## Collection source

Disposable collection содержит только committed рабочие decks:

```text
fixtures/real-decks/Words__N1.apkg
fixtures/real-decks/文法__N5.apkg
fixtures/real-decks/Java.apkg
fixtures/real-decks/manifest.json
```

Импорт выполняется через public `Collection.import_anki_package(...)`. Synthetic notes/cards/templates/media и fallback content запрещены.

## Основные entrypoints

```text
run-e2e.sh                         canonical container orchestration
smoke-api.py                       API smoke
smoke-browser-wrapper.mjs          scope wrapper
smoke-browser.mjs                  direct Playwright browser entrypoint
browser-progress.mjs               deterministic plan/item progress
run_event_protocol.py              global schema-v1 producer/validator
write-artifact-manifest.py         manifest schema v2
verify-telemetry-restart.py        restart proof
```

Dockerfile копирует все `*.mjs` после dependency/Anki layers, затем:

```text
smoke-browser.mjs         → smoke-browser-core.mjs
smoke-browser-wrapper.mjs → smoke-browser.mjs
```

Поэтому новый `browser-progress.mjs` доступен entrypoint без изменения дорогих image layers.

## Execution order

Canonical contour:

```text
exact package validation
→ fresh profile
→ empty collection
→ real APKG import/inventory/anchors
→ scheduling/state scenarios
→ add-on install
→ first Anki start/readiness
→ API smoke
→ plan-driven browser smoke
→ optional restart proof
→ manifest/public artifact
→ cleanup/final result
```

## Live run protocol

Container stream:

```text
/e2e/artifacts/reports/run-events.jsonl
```

Крупные phases публикуются через shell helpers:

```text
phase_start
phase_pass
phase_fail
phase_skip
```

`browser-smoke-first` остаётся одной stable global phase. Browser entrypoint пишет item lifecycle как safe `message/info` events с `current/total`.

## Browser plan

`browser-progress.mjs` строит plan до запуска Chromium.

Фактический plan с telemetry:

```text
23 items
18 expected screenshots
```

Items:

```text
browser.launch
dashboard.setup
10 × route.<route>.<theme>
4 × telemetry.<step>
3 × preview.<anchor>
scenario.cards
2 × cards-route.<theme>
diagnostics.final
```

Plan validation требует:

- schemaVersion `1`;
- unique stable IDs;
- known kinds;
- sequential order;
- non-negative expected screenshots;
- exact `countsByKind` parity;
- exact screenshot sum;
- public-safe bounded fields.

## Browser item wrapper

`BrowserProgress.run(itemId, operation)`:

1. принимает только planned item;
2. запрещает concurrent/duplicate completion;
3. фиксирует `performance.now()`;
4. печатает START;
5. вызывает schema-v1 Python producer;
6. выполняет operation;
7. проверяет screenshot delta;
8. сохраняет PASS или FAIL;
9. обновляет partial browser report;
10. повторно бросает исходную ошибку.

Producer adapter использует:

```text
execFile
shell: false
array arguments
non-zero exit → hard failure
```

Retries отсутствуют.

## Console progress

```text
[BROWSER] PLAN items=23 screenshots=18 telemetry=true
[BROWSER] [1/23] START browser-launch item=browser.launch
[BROWSER] [1/23] PASS browser-launch item=browser.launch duration=478ms screenshots=0
[BROWSER] [3/23] START route-capture item=route.home.light route=#/home theme=light
[BROWSER] [3/23] PASS route-capture item=route.home.light duration=1566ms screenshots=1
```

Progress line не содержит raw stack, token-bearing URL, credentials или absolute private paths.

## Route coverage

Routes:

```text
home
cards
decks
profile
settings
```

Themes:

```text
light
dark
```

Каждый route/theme — отдельный item и один screenshot. Итого 10.

Сохраняются:

- `waitUntil: "networkidle"`;
- visible `main`;
- exact hash;
- init-script theme bootstrap;
- dialog dismissal;
- full-page screenshot.

## Native preview coverage

Anchors:

```text
words-preview
grammar-preview
java-preview
```

Каждый anchor — один item с двумя screenshots. Внутри:

- `/api/search/inspect`;
- exact card identity;
- native render source;
- front/back HTML;
- raw AV marker prohibition;
- expected class checks;
- Shadow DOM;
- zero scripts;
- light/dark capture.

Итого 6.

## Cards state coverage

`scenario.cards` проверяет реальные imported card states без content cloning.

```text
cards-route.light
cards-route.dark
```

проверяют zero raw AV markers, zero horizontal overflow и создают 2 state screenshots.

## Telemetry coverage

При наличии `ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT` plan содержит:

```text
telemetry.declined
telemetry.reliability
telemetry.feature
telemetry.offline
```

Проверяются zero outbound, purpose isolation, bounded batch delivery и persistent offline queue. Отдельные event POST calls не являются plan items.

## Final diagnostics

`diagnostics.final` проверяет:

```text
pageErrors.length === 0
actionable failedRequests.length === 0
unexpectedExternalRequests.length === 0
consoleErrors.length === 0
```

Favicon failure фильтруется. `requestfailed` сохраняет Playwright network semantics; HTTP 4xx/5xx не классифицируется автоматически как network failure.

## Browser reports

```text
reports/browser-smoke-first.json    schema v2
reports/screenshot-performance.json schema v2
reports/screenshot-performance.md
```

Browser report содержит:

```text
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
```

Failure report дополнительно сохраняет partial progress, exact failed item и raw error в существующем diagnostics field.

## Screenshot fail-closed contract

```text
10 route screenshots
6 native preview screenshots
2 Cards state screenshots
= 18
```

Проверяются:

- item delta;
- plan expected total;
- final `screenshots.length`;
- independent PowerShell category counts;
- zero synthetic/legacy screenshot paths.

## Public artifact

Success artifact включает:

```text
artifact-manifest.json
package/anki_study_report.ankiaddon
reports/run-events.jsonl
reports/browser-smoke-first.json
reports/screenshot-performance.json
real-deck reports
API reports
resource reports, если включены
18 screenshots
redacted readiness
diagnostics
```

Public exporter валидирует source и public copy, redacts token/private paths и отклоняет secret-like content.

## Verification commands

Node:

```bash
node --check docker/anki-e2e/browser-progress.mjs
node --check docker/anki-e2e/smoke-browser.mjs
node --test tests/browser_progress.test.mjs
```

Focused pytest:

```bash
python -m pytest \
  tests/test_browser_progress_node.py \
  tests/test_e2e_screenshot_contract.py \
  tests/test_docker_smoke_helpers.py \
  tests/test_run_event_protocol.py \
  tests/test_run_event_integration.py \
  tests/test_run_event_controlled_failure.py \
  tests/test_telemetry_e2e_harness.py \
  tests/test_e2e_harness_reuse.py
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

## Последний подтверждённый proof

```text
implementation SHA: e25bd0b24e32ce4717ed2dbda138d802f707f6d5
Fast CI: 30048028664 — PASS
standard/cards: 30049216529 — PASS
artifact ID: 8580366654
artifact digest: sha256:04d3945e594c01cf292fb1f7a2a56e4734ccc37e27bd094cd27f9d5cb92127a7
browser items: 23/23 PASS
screenshots: 18/18
diagnostics errors: 0
```

Closeout: [`../../reports/ci/e2e-i2-browser-smoke-progress-closeout.md`](../../reports/ci/e2e-i2-browser-smoke-progress-closeout.md).