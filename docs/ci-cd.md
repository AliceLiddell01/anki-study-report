# CI/CD

**Снимок документации:** 2026-07-24.

Проект использует три независимых cloud-контура:

```text
Fast CI                         canonical non-Docker checks + exact package producer
Full Docker / Anki E2E          real-Anki consumer exact package + current E2E harness
Gated Release Delivery          exact release artifact + standard/full + publication gates
```

Fast CI публикует advisory verification plan, но не запускает тяжёлый E2E автоматически. Порядок запусков определён в [`verification-run-policy.md`](verification-run-policy.md).

Связанные контракты:

- повторное использование package: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md);
- единый live lifecycle: [`run-event-protocol.md`](run-event-protocol.md).

## Fast CI

Workflow:

```text
.github/workflows/ci-fast.yml
```

Canonical command:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Fast CI выполняет:

- repository hygiene;
- Python tests;
- один canonical TypeScript typecheck;
- Vitest;
- production dashboard build;
- bundle/assets checks;
- `.ankiaddon` build;
- package validation;
- verification planner;
- structured timing/summary;
- schema-validated live run-event stream.

Fast CI не запускает Docker или Anki Desktop.

### Runtimes

```text
Python 3.11
Node.js 20
pnpm 9.15.9
```

### Runner и permissions

Fast CI использует GitHub-hosted `windows-2025`, PowerShell 7 и read-only contents permission. Checkout выполняется с `persist-credentials: false`. Secrets, OIDC, deployment и self-hosted runner не нужны.

Значения `github.*`, которые используются PowerShell, передаются через `env`, а не встраиваются в inline executable script text.

### Fast CI artifacts

| Artifact | Условие | Содержимое | Retention |
| --- | --- | --- | --- |
| diagnostics | `if: always()` | logs, verification plan, summaries, environment, timing, `run-events.jsonl` | 14 дней |
| exact package | только после полного Fast CI PASS | `anki_study_report.ankiaddon`, `package-metadata.json` | 7 дней |

Package metadata schema v1 фиксирует:

```text
testedCommitSha
sourceHeadSha
sourceBaseSha
packageSha256
packageSizeBytes
```

Artifact transport digest и внутренний package SHA-256 являются разными identities и проверяются отдельно.

Transient writer sidecars:

```text
run-events.jsonl.lock
run-events.jsonl.state.json
```

не включаются в `ci-summary.json.artifactFiles` и не считаются evidence.

### Live run protocol Fast CI

Fast CI создаёт:

```text
ci-fast/run-events.jsonl
```

`scripts/ci_fast_timing.py` остаётся каноническим timing API и одновременно публикует:

```text
run/start
phase/start
phase/pass | phase/fail | phase/skip
run/pass | run/fail | run/cancel
```

Registry timing и run-events проверяются на равенство при импорте. Финальный stream валидируется до загрузки diagnostics artifact.

Пример console output:

```text
[00:12.040] [FAST] [frontend-vitest] START
[00:52.603] [FAST] [frontend-vitest] PASS duration=40563ms
```

## Full Docker / Anki E2E

Workflow:

```text
.github/workflows/ci-e2e.yml
```

Runner:

```text
ubuntu-24.04
PowerShell 7
Docker Engine / Docker Compose
```

Cloud permissions:

```yaml
contents: read
actions: read
packages: read
```

### Package sources

Cloud workflow принимает только:

```text
manual/reusable E2E  → fast-ci-artifact
release caller       → release-artifact
```

Cloud `source-build` отклоняется до registry login. Локальный Docker может использовать source build как development/diagnostic contour.

### Package и harness являются разными identities

Для manual Fast CI handoff:

```text
Fast CI run
→ exact package tested commit + package SHA-256
→ current E2E harness/workflow commit
→ ancestry + complete changed-path validation
→ exact GHCR environment
→ real Anki E2E
```

Если package и harness commits совпадают, режим `exact-tree` требует пустой diff.

Если commits различаются, режим `harness-only` разрешён только когда весь diff проходит fail-closed allowlist. Production add-on, frontend, package/build/dependency и unrelated paths блокируют reuse.

Это означает:

- исправление только `docker/anki-e2e/`, artifact exporter или handoff consumer не требует нового Fast CI;
- package-impacting изменение требует новый package-producing Fast CI;
- release всегда использует exact current release artifact, а не старый Fast CI package.

### Handoff validation

Consumer:

1. Проверяет package-source inputs.
2. Получает exact Fast CI run и artifact IDs.
3. Проверяет diagnostics.
4. Проверяет package metadata и internal SHA-256.
5. Проверяет package commit ancestry.
6. Получает полный diff до current workflow/harness SHA.
7. Проверяет каждый path через allowlist.
8. Staging-ит package в `docker/anki-e2e/local-input/`.
9. Запускает current E2E harness.
10. Проверяет package SHA после E2E.
11. Публикует package/harness reuse evidence.

Fallback на source build запрещён.

### Modes и scopes

Canonical modes:

```text
standard
perf100
```

Legacy `strict-apkg` input нормализуется в `standard`; отдельного synthetic/APKG режима нет.

Scopes:

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

Targeted scope меняет product assertions, но не отключает real-deck manifest/checksum/import/inventory/anchor/scenario foundation.

### GHCR environment

Cloud E2E использует только exact digest из:

```text
docker/anki-e2e/environment-image-lock.json
```

Mutable tags, cloud BuildKit/GHA cache, PAT fallback и automatic visibility changes запрещены. Локальная Dockerfile/Compose build path не является cloud fallback.

### Live run protocol Docker E2E

Raw E2E создаёт:

```text
reports/run-events.jsonl
```

Public artifact содержит:

```text
artifacts/reports/run-events.jsonl
```

`run-e2e.sh` публикует START/terminal status для каждой крупной phase и сохраняет прежний `e2e-telemetry.py` contour.

Пример:

```text
[00:10.112] [E2E] [browser-smoke-first] START
[00:42.316] [E2E] [browser-smoke-first] PASS duration=32204ms
```

Success manifest обязан индексировать `reports/run-events.jsonl`. Public exporter валидирует source stream до копирования и public copy после копирования. Missing/invalid stream при success является hard failure.

### Compose output в CI

В CI wrapper задаёт:

```text
COMPOSE_ANSI=never
COMPOSE_PROGRESS=plain
COMPOSE_MENU=0
COMPOSE_STATUS_STDOUT=1
```

и запускает:

```text
docker compose --ansi never --progress plain run --no-TTY ...
```

Local interactive output сохраняется, если `CI`/`GITHUB_ACTIONS` не заданы.

## Public E2E artifact

Raw readiness с token не загружается.

`scripts/prepare_ci_e2e_artifacts.py`:

- экспортирует только allowlisted structured evidence;
- удаляет token query parameters;
- создаёт redacted readiness без token;
- редактирует workspace/private absolute paths;
- сохраняет safe relative paths;
- отклоняет secrets/private keys/token-bearing URLs;
- проверяет manifest duplicates/traversal/missing files;
- публикует package и harness SHA отдельно;
- независимо валидирует reuse evidence;
- дважды валидирует run-event stream;
- сохраняет canonical E2E exit code до upload/cleanup и восстанавливает его в конце.

Artifact upload не может превратить functional failure в PASS.

## Real-deck collection contract

Docker импортирует только:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Import выполняется через public Anki API. Synthetic notes/cards/templates/media, external APKG override и cloning запрещены.

Подробнее: [`docker-e2e.md`](docker-e2e.md).

## Manual commands

Запустить новый package-producing Fast CI:

```bash
gh workflow run ci-fast.yml --ref <branch>
```

Запустить targeted E2E с существующим verified package:

```bash
gh workflow run ci-e2e.yml \
  --repo AliceLiddell01/anki-study-report \
  --ref <branch> \
  -f mode=standard \
  -f scope=cards \
  -f screenshot_workers=auto \
  -f resource_telemetry=true \
  -f verify_restart=true \
  -f fast_ci_run_id=<successful-package-producing-run>
```

Наблюдение:

```bash
gh run watch <run-id> --exit-status
gh run view <run-id> --log-failed
gh run download <run-id> --dir <output>
```

Run сопоставляется с exact package и harness identities, а не только с названием branch.

## Failure policy

Project failure диагностируется по первому failed step, summary и artifact. Финальные `Restore canonical result`/wrapper exceptions только возвращают ранее сохранённый код и не являются автоматически root cause.

Infrastructure failure: runner provisioning/GitHub outage/queued stale/timed out/cancelled по инфраструктурной причине. Rerun допустим после классификации.

Ключевые правила:

```text
LOCAL FALLBACK PASS != GITHUB CI PASS
NO SOURCE-BUILD FALLBACK IN CLOUD
NO NEW FAST CI FOR VALIDATED HARNESS-ONLY DIFF
NO REPEAT OF SUCCESSFUL PACKAGE/HARNESS PAIR
CONSOLE TEXT != ЕДИНСТВЕННЫЙ ИСТОЧНИК ИСТИНЫ
```

## Gated release

`.github/workflows/release.yml` сохраняет PR contract validation, но production build/publish выполняется только manual dispatch с разрешённой ветки и версии.

Release sequence:

```text
exact release build
→ package validation
→ release-artifact standard/full
→ draft GitHub Release
→ protected AnkiWeb publication
→ public verification
```

Release package SHA-256 проверяется до и после real-Anki E2E. Production credentials доступны только защищённому publisher job.

## Подтверждённая реализация E2E-I1

```text
Implementation SHA: a376a1e5556b26043d29fadcf01698972bd1b2ba
Fast CI: 30039103625 — PASS
First standard/full E2E: 30039372012 — PASS
Final standard/full E2E: 30039708429 — PASS
Package SHA-256: 9ac537e77ed32fb1dd65f79d5e84084a1b4f0e301c0215d9d5b61b8bf2d99fbf
PR в core: не создан
Merge в core: не выполнен
```

Подробный отчёт: [`../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md`](../reports/ci/e2e-i1-unified-live-run-protocol-closeout.md).
