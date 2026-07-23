# Roadmap наблюдаемости E2E, диагностики и идентичности сборки

**Статус:** в работе; `E2E-I1` завершён и подтверждён, следующий этап — `E2E-I2`  
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

Оставшаяся проблема заключается не в отсутствии диагностики. Существующие данные распределены между GitHub workflow YAML, PowerShell, Bash, Python и Node.js. Разработчику всё ещё приходится вручную восстанавливать:

- что именно выполняется сейчас;
- где произошёл первый функциональный failure;
- корректно ли обработана отмена;
- какой exact non-release build породил evidence;
- какие измерения можно сравнивать между совместимыми runs.

Этот roadmap объединяет существующие части в один согласованный run protocol. Он намеренно разделён ровно на шесть крупных поставляемых этапов. Нельзя создавать вложенные roadmap-уровни вроде `E2E-I2.1` или `E2E-I4a`: внутри этапа используются обычные implementation tasks и commits.

## Порядок поставки

```text
E2E-I1 Единый live-протокол выполнения — COMPLETE
→ E2E-I2 Прогресс browser smoke
→ E2E-I3 Стабильная диагностика failures
→ E2E-I4 Preflight и cancellation
→ E2E-I5 Идентичность non-release build
→ E2E-I6 Финальный summary и история производительности
```

Каждый этап обязан оставлять репозиторий в полезном, независимо проверяемом состоянии. Поздний этап может расширить schema раннего, но не должен делать ранний результат непригодным до завершения всех шести этапов.

## Общие инварианты

Все этапы сохраняют существующие platform/security contracts:

- реальный Anki Desktop остаётся integration boundary;
- cloud E2E использует immutable GHCR digest;
- package bytes остаются exact и проверяются SHA-256;
- package/harness reuse остаётся ancestry- и full-diff-validated;
- cloud E2E не имеет source-build fallback;
- public evidence не содержит token-bearing URL, private absolute path, profile data или credentials;
- synthetic notes/cards/templates/media не возвращаются;
- release остаётся manual, approval-gated и exact-artifact based;
- успешная неизменённая package/harness pair не перезапускается без конкретной причины;
- runtime artifacts, metrics, logs и screenshots не коммитятся.

## E2E-I1 — Единый live-протокол выполнения

**Статус:** COMPLETE  
**Дата подтверждения:** 2026-07-24  
**Финальный implementation SHA:** `a376a1e5556b26043d29fadcf01698972bd1b2ba`

**Цель:** заставить Fast CI и Docker E2E сообщать прогресс через одну стабильную event model, сохранив читаемый локальный console output.

### Реализовано

- Введён один schema-versioned run-event contract для Fast CI и real-Anki E2E.
- Каждое событие записывается одновременно в:
  - немедленный stdout/stderr output;
  - structured `run-events.jsonl`.
- Стандартизированы поля:
  - UTC timestamp;
  - elapsed duration;
  - producer;
  - phase ID;
  - event kind;
  - status;
  - optional progress counters;
  - optional bounded message;
  - `failureCode`, зарезервированный для `E2E-I3`.
- Использованы thin adapters существующих PowerShell/Bash/Python контуров без отдельного logging service.
- Stable phase IDs общие для console output, timing и validation.
- Docker/Compose output в CI переведён в plain non-interactive mode.
- Raw diagnostics, timing, resource telemetry и screenshots сохранены.
- Fast CI diagnostics и Docker public artifact содержат validated JSONL.
- Success manifest требует `reports/run-events.jsonl` fail closed.
- Добавлены security, controlled-failure и concurrent-append tests.
- В ходе финального E2E обнаружена и исправлена production telemetry race после consent transition.

### Фактическая форма console output

```text
[00:12.040] [FAST] [frontend-vitest] START
[00:52.603] [FAST] [frontend-vitest] PASS duration=40563ms

[00:10.112] [E2E] [browser-smoke-first] START
[00:42.316] [E2E] [browser-smoke-first] PASS duration=32204ms
```

### Completion criteria

| Критерий | Результат |
| --- | --- |
| Local/CI используют одинаковые phase names/statuses | PASS |
| Validator отклоняет unknown/unsafe values | PASS |
| Fast CI success stream | PASS |
| Docker E2E success stream | PASS |
| Controlled failure stream | PASS |
| Existing package/sanitizer/real-deck semantics сохранены | PASS |
| Exact package Fast CI | PASS — `30039103625` |
| Первый `standard/full` | PASS — `30039372012` |
| Финальный независимый `standard/full` | PASS — `30039708429` |

### Out of scope

- browser scenario expansion;
- item-level route/theme/preview progress;
- visual regression;
- performance thresholds;
- migration на external logging stack.

Актуальный контракт: [`../../docs/run-event-protocol.md`](../../docs/run-event-protocol.md).

Итоговый отчёт: [`../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md).

## E2E-I2 — Прогресс browser smoke

**Статус:** следующий этап, не начат.

**Цель:** устранить длинный silent interval внутри `smoke-browser.mjs` и публиковать полезный item-level timing.

### Deliverables

- Печатать browser smoke plan до запуска Chromium:
  - routes и themes;
  - native previews;
  - state checks;
  - telemetry contour при включении;
  - ожидаемое количество screenshots.
- Публиковать START/PASS/FAIL и duration для каждого route/theme capture.
- Публиковать START/PASS/FAIL и duration для каждого native preview anchor.
- Показывать progress scenario-card checks, Cards route inspection и telemetry lifecycle.
- Сохранять page errors, failed requests, console errors и external-request evidence.
- Расширить browser performance evidence per-item durations и списком самых медленных items.
- Сохранять direct Playwright API architecture, пока отдельное evidence-backed решение не обоснует миграцию на Playwright Test.

### Completion criteria

- Ни одна browser smoke операция, которая обычно длится больше нескольких секунд, не остаётся silent.
- Controlled browser failure указывает exact route, theme, anchor или telemetry step.
- Screenshot count и browser plan совпадают fail closed.
- Existing light/dark, native-preview и external-network assertions проходят.

### Out of scope

- новое route coverage;
- pixel/perceptual baseline comparison;
- automatic browser retries.

## E2E-I3 — Стабильная диагностика failures

**Статус:** запланирован после `E2E-I2`.

**Цель:** заменить generic exit-status reconstruction стабильной machine-readable taxonomy и кратким human summary.

### Deliverables

- Ввести reviewed registry стабильных string failure codes, например:
  - `ASR-E2E-PREFLIGHT-CONFIG`;
  - `ASR-E2E-COMPOSE-INVALID`;
  - `ASR-E2E-PACKAGE-HANDOFF`;
  - `ASR-E2E-REAL-DECK-CONTRACT`;
  - `ASR-E2E-ANKI-START`;
  - `ASR-E2E-READY-TIMEOUT`;
  - `ASR-E2E-API-SMOKE`;
  - `ASR-E2E-BROWSER-SMOKE`;
  - `ASR-E2E-RESTART`;
  - `ASR-E2E-ARTIFACT-SANITIZE`;
  - `ASR-E2E-CLEANUP`;
  - `ASR-E2E-CANCELLED`;
  - соответствующие Fast CI categories, где это полезно.
- Оставить process exit codes грубыми и документированными; аналитическим источником истины сделать string code.
- Фиксировать первый functional failure как primary.
- Записывать cleanup/sanitizer/uploader/summary failures как secondary, не перезаписывая root cause.
- На каждый failure формировать:
  - `reports/failure-summary.json`;
  - `reports/failure-summary.md`;
  - короткую console/GitHub annotation.
- Включать phase, elapsed time, last successful phase, safe message, exception type, cleanup status и relative evidence paths.
- Full stack trace оставлять только в detailed diagnostics.

### Completion criteria

- Один controlled failure получает одинаковый stable code локально и в GitHub Actions.
- Secondary cleanup failure не заменяет primary browser/API/runtime failure.
- Failure summaries проходят redaction/public-artifact boundary.
- Тесты блокируют случайное переименование или повторное использование published codes.

### Out of scope

- automatic rerun policy;
- flake classification/quarantine;
- автоматическое создание Issues.

## E2E-I4 — Preflight и cancellation

**Статус:** запланирован после `E2E-I3`.

**Цель:** отклонять invalid runs до дорогой Docker-работы и чисто завершать cancelled runs, не маскируя cancellation обычным failure.

### Deliverables

- Добавить один host-side preflight для local wrappers и cloud workflows до Docker pull/build/run.
- Проверять минимум:
  - mode, scope, workers и restart policy;
  - package-source combinations;
  - required files и writable artifact directory;
  - staged package metadata и SHA-256;
  - real-deck manifest, packages, sizes и checksums;
  - environment image lock и exact digest inputs;
  - safe relative paths и mount sources;
  - resolved `docker compose config --quiet` contract.
- Писать bounded `preflight-report.json`.
- Выполнять static validation до GHCR login/image pull, где это возможно.
- Аудировать `if: always()` и оставлять только короткую emergency finalization.
- Явно обрабатывать `SIGINT`, `SIGTERM`, Ctrl-C и PowerShell interruption.
- Маркировать cancellation как `cancelled` + `ASR-E2E-CANCELLED`.
- Делать cleanup idempotent и bounded:
  - остановить Anki;
  - остановить telemetry fake/resource sampler;
  - убрать Compose resources;
  - восстановить ownership, когда возможно;
  - сохранить исходный cancellation/result.

### Completion criteria

- Invalid configuration завершается до запуска container.
- Cancellation test не оставляет E2E containers/background helpers.
- Cancellation создаёт partial valid summary без ненужной тяжёлой artifact-работы.
- Original result восстанавливается после cleanup ровно один раз.

### Out of scope

- force-cancel через GitHub REST API;
- self-hosted runner lifecycle;
- broad Docker redesign.

## E2E-I5 — Идентичность non-release build

**Статус:** запланирован после `E2E-I4`.

**Цель:** дать каждому успешному non-release Fast CI package уникальную traceable identity без изменения canonical release SemVer.

### Модель

```text
canonicalVersion = release/product version из version.py
buildIdentity     = exact non-release CI execution identity
```

Display version может использовать SemVer pre-release/build metadata, например:

```text
1.2.0-ci.842+run.30013925137.attempt.1.pr.133.branch.test-real-deck.sha.bd0355c3
```

Числа выше — только пример.

### Deliverables

- Генерировать machine build ID вида `fast-<run-id>-a<attempt>`.
- Безопасно разрешать:
  - canonical version;
  - event type;
  - branch name;
  - Fast CI run ID/number;
  - run attempt;
  - PR number, когда он однозначен;
  - exact commit SHA.
- Для PR events использовать номер из event payload.
- Для branch/manual events записывать PR только при одном безопасном match; иначе `null`/`ambiguous`.
- Добавить generated build info в package, например `build_info.json`.
- Расширить `package-metadata.json` новой schema version.
- Экспортировать bounded runtime build info, чтобы E2E доказал:

```text
package metadata identity
= packaged build_info identity
= running add-on identity
```

- Сохранить release artifacts чистыми:
  - `channel=release`;
  - canonical version без изменения;
  - без обязательной branch/PR/run-specific display version.
- Документировать, что разные attempts намеренно дают разные package bytes.

### Completion criteria

- Два Fast CI attempts одного commit имеют разные build identities и hashes.
- E2E отклоняет mismatch metadata/package/runtime identity.
- Release preparation/package identity не меняются.
- Branch slugs/metadata bounded, deterministic и safe.

### Out of scope

- automatic canonical version bump;
- изменение AnkiWeb release semantics;
- замена exact package SHA-256 строкой версии.

## E2E-I6 — Финальный summary и история производительности

**Статус:** запланирован последним этапом контура.

**Цель:** формировать один authoritative result summary и сохранять compact metrics для будущего trend analysis.

### Deliverables

- Заменить fragmented end-of-run summaries одним canonical aggregator, который читает доступные partial reports.
- Генерировать:
  - `run-summary.json`;
  - `run-summary.md`;
  - один compact `GITHUB_STEP_SUMMARY` block.
- Включать:
  - SUCCESS / FAILURE / CANCELLED;
  - canonical version/build identity;
  - branch, PR и SHA;
  - package source и package SHA-256;
  - mode, scope, workers, restart;
  - completed checks;
  - primary/secondary failure codes;
  - last successful phase;
  - total duration;
  - slowest phases/browser items;
  - peak CPU/memory;
  - screenshot count;
  - artifact/cleanup status.
- Нормализовать Fast CI timing, E2E phase/browser timing, image preparation, resource telemetry и upload timing в `metrics/run-performance.json`.
- Хранить dimensions:
  - workflow;
  - mode/scope;
  - workers;
  - package source;
  - image digest/cache state;
  - Anki version;
  - build ID;
  - commit, branch и PR.
- Публиковать compact metrics artifact с более долгим retention, если policy разрешит.
- Определить guidance для p50/p95 и first-run pass rate.

### Completion criteria

- Success, controlled failure и cancellation создают valid canonical summary.
- Значения пересчитываются из source evidence, а не доверяют unchecked env strings.
- Timing/resource metrics остаются informational.
- Future analyzer сравнивает compatible runs без parsing console text.

### Out of scope

- performance blocking thresholds;
- внешний CI metrics dashboard/service;
- scheduled trend analyzer;
- automatic optimization по одному run.

## Verification policy этого roadmap

После каждого небольшого commit не запускается полный Docker matrix. Для каждого этапа:

1. добавить focused unit/contract tests;
2. выполнить relevant local non-Docker checks;
3. использовать controlled negative case, если этап касается failure/cancellation;
4. выполнить targeted real-Anki E2E затронутого contour;
5. выполнить один final `standard/full`, если меняется end-to-end lifecycle, package identity или canonical summary boundary;
6. не повторять успешную неизменённую package/harness pair.

Docs-only commits после уже успешных gates не требуют нового Fast CI/Docker без отдельной причины.

Весь roadmap завершён только после реализации, документирования и owner acceptance всех шести этапов. Это не активирует автоматически CI 7–12, visual regression или release publication.

## Внешние источники, использованные при проектировании

- GitHub Actions workflow commands и job summaries: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
- GitHub Actions cancellation behavior: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation
- Docker Compose predefined output variables: https://docs.docker.com/compose/how-tos/environment-variables/envvars/
- Docker Compose CLI/config: https://docs.docker.com/reference/cli/docker/compose/ и https://docs.docker.com/reference/cli/docker/compose/config/
- Playwright steps/reporters как справочный материал, а не обязательная миграция: https://playwright.dev/docs/api/class-test и https://playwright.dev/docs/test-reporters
- Semantic Versioning 2.0.0 pre-release/build metadata: https://semver.org/
