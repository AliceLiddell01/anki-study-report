# CI/CD

**Снимок документации:** 2026-07-23.

Проект использует три независимых cloud-контура:

```text
Fast CI                         canonical non-Docker checks + exact package producer
Full Docker / Anki E2E          real-Anki consumer exact package + current E2E harness
Gated Release Delivery          exact release artifact + standard/full + publication gates
```

Fast CI публикует advisory verification plan, но не запускает тяжёлый E2E автоматически. Порядок запусков определён в [`verification-run-policy.md`](verification-run-policy.md).

Контракт повторного использования package: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md).

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
- structured timing/summary.

Fast CI не запускает Docker или Anki Desktop.

### Runtimes

```text
Python 3.11
Node.js 20
pnpm 9.15.9
```

### Runner и permissions

Fast CI использует GitHub-hosted `windows-2025`, PowerShell 7 и read-only contents permission. Checkout выполняется с `persist-credentials: false`. Secrets, OIDC, deployment и self-hosted runner не нужны.

### Fast CI artifacts

| Artifact | Condition | Contents | Retention |
| --- | --- | --- | --- |
| diagnostics | `if: always()` | logs, verification plan, summaries, environment, timing | 14 days |
| exact package | только после полного Fast CI PASS | `anki_study_report.ankiaddon`, `package-metadata.json` | 7 days |

Package metadata schema v1 фиксирует:

```text
testedCommitSha
sourceHeadSha
sourceBaseSha
packageSha256
packageSizeBytes
```

Artifact transport digest и внутренний package SHA-256 являются разными identities и проверяются отдельно.

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
- сохраняет canonical E2E exit code до upload/cleanup и восстанавливает его в конце.

Artifact upload не может превратить functional failure в PASS.

## Real-deck collection contract

Docker imports only:

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

Project failure диагностируется по failed step, summary и artifact. Local PASS не отменяет red cloud run.

Infrastructure failure: runner provisioning/GitHub outage/queued stale/timed out/cancelled по инфраструктурной причине. Rerun допустим после классификации.

Ключевые правила:

```text
LOCAL FALLBACK PASS != GITHUB CI PASS
NO SOURCE-BUILD FALLBACK IN CLOUD
NO NEW FAST CI FOR VALIDATED HARNESS-ONLY DIFF
NO REPEAT OF SUCCESSFUL PACKAGE/HARNESS PAIR
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

## Подтверждённая реализация

Package producer:

```text
Fast CI run: 30013925137
package commit: bd0355c315197cfb659cb28b32b63a4931b73458
package SHA-256: 3ae8439ba18cac82b7e8bb6b240223970cb6403130abf1f909168273ff39baf8
```

Final full consumer:

```text
E2E run: 30022393738
harness commit: 1a84eabaacb5c368f92ae4952e732d8610619f95
reuse mode: harness-only
result: PASS
```

Полный отчёт: [`../reports/ci/real-deck-e2e-foundation-closeout.md`](../reports/ci/real-deck-e2e-foundation-closeout.md).
