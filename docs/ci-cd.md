# CI Foundation

Fast CI publishes the advisory output of `scripts/plan_verification.py`; it
never auto-starts expensive E2E. Run order is defined in
`verification-run-policy.md`.

Снимок документации: 2026-07-16.

В проекте реализованы Fast CI, переиспользуемый Full Docker / Anki E2E и
ручной gated release delivery для GitHub Releases и существующей AnkiWeb page.
Полный контракт публикации описан в `docs/release-automation.md`.

## Роль Fast CI

GitHub Actions workflow `.github/workflows/ci-fast.yml` — основной независимый
исполнитель быстрых проверок опубликованного commit. Локальные команды остаются
контуром разработки, воспроизведения падений и ручным fallback при
инфраструктурной недоступности GitHub Actions.

Тестовая логика не продублирована в YAML. И локальный fallback, и GitHub Actions
вызывают из корня репозитория одну canonical команду:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Она выполняет repository hygiene, pytest, ровно один canonical TypeScript
typecheck, Vitest, production build с копированием assets в add-on, сборку `.ankiaddon` и две
проверки архива. `web-dashboard/package.json` сохраняет более узкий
`pnpm run test:all` для frontend-oriented локальной работы, но не является
отдельным облачным pipeline.

Перед canonical command GitHub Actions устанавливает зависимости по
`requirements-dev.txt` и frozen `web-dashboard/pnpm-lock.yaml`. Это подготовка
окружения, а не вторая реализация тестов.

## Trigger matrix

| Событие | Scope |
| --- | --- |
| `push` | `master` и `codex/**` |
| `pull_request` | PR с base `master` |
| `workflow_dispatch` | ручной запуск |

`pull_request_target`, schedule, tag/release и deployment triggers не
используются.

## Runner и runtimes

Workflow использует один GitHub-hosted `windows-2025` job, PowerShell 7, без
matrix, Docker и Anki Desktop. GitHub перечисляет `windows-2025` как stable
standard runner label для GitHub-hosted workflows:
[Choosing the runner for a job](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job).

Project runtime contract:

```text
Python 3.11       .python-version
Node.js 20        .node-version
pnpm 9.15.9       web-dashboard/package.json packageManager
```

Node 20 является CI baseline; `engines` также разрешает локальные Node 21-24,
а pnpm остаётся на major 9. Actions pinned к полным
commit SHA официальных upstream releases; рядом с SHA указан проверенный tag.
Dependency cache привязан только к requirements/lockfile. Dashboard build,
`.ankiaddon`, runtime data и E2E outputs не кэшируются.

## Permissions и защита ресурсов

Workflow задаёт только:

```yaml
permissions:
  contents: read
```

Checkout использует `persist-credentials: false`. Secrets, write permissions,
OIDC, environments и self-hosted runners не нужны. Для одной ветки новый run
отменяет устаревший через `ci-fast-${{ github.ref }}`. Job имеет timeout 20
минут: fast pipeline обычно заметно короче, а зависший install/build не должен
расходовать приватную Actions quota бесконечно.

## Artifact contract

Fast CI публикует два независимых artifacts с разным назначением.

| Artifact | Condition | Name | Contents | Retention |
| --- | --- | --- | --- | --- |
| Diagnostics | `if: always()` | `ci-fast-<run-id>-<run-attempt>` | logs, verification plan, `ci-summary.json`, `ci-summary.md`, `environment.txt`, `timing/fast-ci-timing.json`, `timing/fast-ci-timing.md` | 14 дней |
| Exact package | только после успешного Fast contour и diagnostics upload | `ci-package-<tested-sha>-<run-id>-<run-attempt>` | ровно `anki_study_report.ankiaddon` и `package-metadata.json` | 7 дней |

Diagnostics больше не содержит package или package metadata. Его upload остаётся
доступным после test/build failure, а `ci-summary.json` сохраняет
`schemaVersion: 1` и описывает только diagnostics inventory через
`artifactFiles`. `ci-summary.md` также добавляется в GitHub Step Summary.

Exact package — краткоживущий non-release CI artifact, а не published release.
Он создаётся из уже собранного canonical package без повторной сборки, проходит
`package_addon.py --check-only` и загружается только через `if: success()` после
успешного diagnostics upload. Staging directory содержит ровно два файла, без
logs, hidden files, subdirectories и локальных путей.

`package-metadata.json` schema v1 различает:

- `testedCommitSha` — exact `github.sha`, то есть на PR обычно synthetic merge SHA;
- `sourceHeadSha` — head commit исходной ветки PR либо тот же SHA для push/dispatch;
- `sourceBaseSha` — base commit PR либо `null`, когда meaningful base отсутствует;
- `packageSha256` и `packageSizeBytes` — hash и размер внутренних package bytes.

GitHub `artifact-digest` относится к immutable transport artifact, а не к
`.ankiaddon`; он выводится после upload вместе с artifact ID в Step Summary и не
включается внутрь уже загруженного metadata. `artifact-url` и token-bearing URLs
не логируются. Summary, metadata и environment не содержат tokens,
пользовательские Anki paths, profile data или полный event payload.

## Structured Fast CI timing diagnostics

Fast CI ведёт schema-versioned observational timing в
`ci-fast/timing/fast-ci-timing.json` и рендерит компактный Markdown рядом. Внутри
repository scripts используются monotonic high-resolution интервалы для
установки dependencies, одного TypeScript typecheck, Vitest, Vite, bundle/assets,
pytest, package checks, verification planner, summary и exact-package staging.
Обычный локальный вызов без `-TimingOutput` сохраняет прежний контракт и не
создаёт runtime files.

GitHub action setup, checkout, cache restore/save, artifact upload и post-job
работа не подменяются внутренними таймерами: их длительности берутся из Jobs API
и logs после run. Step timestamps имеют более грубую granularity, поэтому два
источника анализируются отдельно. Cache enabled не считается доказанным exact
hit без соответствующего log/output evidence.

Инструментализация не является оптимизацией. Runner `windows-2025`, checkout
`fetch-depth: 0`, setup-python/setup-node caches, dependency commands, canonical
coverage и package producer contract сохранены. Удалённый PR #37 повторный
typecheck и phase `frontend-typecheck-build` не являются частью контракта.

## Fast CI package handoff to Docker E2E

Fast CI остаётся producer двух независимых artifacts и сам не исполняет Docker
E2E. Отдельно запущенный `Full Docker / Anki E2E` может opt-in использовать
exact Fast package через optional string input `fast_ci_run_id`; этот режим
фиксируется как `fast-ci-artifact`.

Consumer принимает только successful same-repository run workflow `Fast CI` с
событием `workflow_dispatch`, `push` или `pull_request`; fork-origin artifacts
отклоняются. Diagnostics и package разрешаются через GitHub API до скачивания и
загружаются по exact artifact IDs. Проверка transport digest выполняется
fail-closed и не заменяет внутренний `packageSha256`.

Validated diagnostics определяет exact `testedCommitSha`, после чего E2E делает
второй checkout этого commit. Package metadata связывается с source run,
checkout и исходным `sourceHeadSha`; invalid или неоднозначный run ID завершает
workflow ошибкой без fallback на source build. Fast package остаётся non-release
CI artifact и не смешивается с current-run release artifact path.

E2E запускается отдельно вручную либо существующим reusable caller. Stage 3 не
добавляет автоматический запуск E2E из Fast CI и не меняет Docker image,
BuildKit или GHA cache architecture. Перед интеграцией handoff требуется
отдельно подтвердить одним Fast CI run и одним targeted E2E run на exact branch
HEAD; real-Anki cloud PASS пока не считается выполненным.

Для public repository logs и artifacts потенциально доступны внешним читателям,
поэтому этот запрет распространяется и на stdout canonical pipeline. Нельзя
выводить secrets, PII, содержимое пользовательской collection или приватные
локальные пути. Первый public run разрешён только после pre-public audit из
`docs/public-repository-readiness.md`.

## Failure policy и локальный fallback

Test/build/package failure GitHub Actions означает ошибку проекта или
несовместимость среды. Её нужно диагностировать по failed step, summary и
artifact, затем воспроизвести той же canonical командой локально. Локальный
PASS не отменяет красный cloud run.

Infrastructure failure — невозможность получить run, runner provisioning
failure, GitHub outage либо run, который остался queued/stale/timed_out или был
отменён по инфраструктурной причине. В таком случае допустим ручной local
fallback:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Ключевое правило:

```text
LOCAL FALLBACK PASS != GitHub CI PASS
```

Автоматического переключения на локальный компьютер нет.

## Ручной запуск и наблюдение

```powershell
gh workflow run ci-fast.yml --ref <branch>
gh run list --workflow ci-fast.yml --commit <exact-sha>
gh run watch <run-id> --exit-status
gh run view <run-id> --log-failed
gh run download <run-id> --dir .\ci-fast-download
```

Run всегда сопоставляется с exact commit SHA, а не с «последним запуском».
Скачанный `ci-summary.json` должен содержать тот же SHA.

## Границы Fast CI

- Fast CI не исполняет Docker/реальный Anki Desktop E2E;
- strict APKG browser smoke и Perf100 не входят в Fast job;
- exact Fast package может быть входом отдельно запущенного Docker E2E;
- Codex CI consumer;
- автоматическая local fallback orchestration;
- deployment, self-hosted runners, OIDC и secrets.

Fast CI остаётся единственным PR-исполнителем canonical non-Docker pipeline.
Release workflow сохраняет PR trigger и check identities, но на PR выполняет
только release contract validation; heavy build получает `skipped` через
job-level условие. Manual dispatch сохраняет полный exact-artifact contour.

## Gated Release Delivery

`.github/workflows/release.yml` сохраняет `pull_request` trigger для base
`master`. На PR job `Validate release contract` выполняется, а
`Test and build exact release artifact` и все production jobs получают
`skipped` через job-level условия. Это сохраняет workflow/job identities для
branch protection, но не повторяет dependency installation, canonical command
`.\scripts\run_full_check.ps1 -SkipDocker` или создание release bundle.
Workflow-level `paths`/`paths-ignore` не используются.

Production dispatch разрешён только с текущего `master` и сериализован
concurrency group. Exact release archive проходит `standard/full` через reusable
`.github/workflows/ci-e2e.yml`, затем создаётся проверенный draft GitHub Release.
Stable channel продолжает в защищённом `ankiweb-production`; только этот job
получает environment secrets. GitHub Release становится публичным после
успешной проверки публичного AnkiWeb файла.

Write permissions разделены: draft/finalize jobs имеют только GitHub contents
write, publisher — только contents read и Environment secrets. PR, forks и
Fast CI production credentials не получают.

## Full Docker / Anki E2E

`.github/workflows/ci-e2e.yml` — второй независимый CI-контур. Он использует
standard x64 runner `ubuntu-24.04`, PowerShell 7 и установленный Docker Engine /
Docker Compose. Workflow остаётся manual-only после bootstrap и имеет typed
inputs `mode`, `scope`, `screenshot_workers`, `resource_telemetry`,
`verify_restart` и optional `fast_ci_run_id`:

| Mode | Project command |
| --- | --- |
| `standard` | `run_full_check.ps1 -DockerOnly` |
| `strict-apkg` | `run_full_check.ps1 -DockerOnly -RequireApkgFixture` |
| `perf100` | `run_full_check.ps1 -DockerOnly -RequireApkgFixture -Perf100` |

Scope независимо выбирает `full`, `global`, `stats`, `decks`, `activity`,
`cards` или `settings`. Targeted scopes — development contour с общими
startup/readiness/API/token/browser/artifact checks; release gate остаётся
`standard/full`. `auto` workers = 3 (range 1–4), `auto` restart = только full.
Strict APKG/Perf100 совместимы только с full/cards.

Workflow не повторяет `run-e2e.sh`, APKG import или browser smoke. Он выбирает
только заранее заданный режим и вызывает существующую project orchestration.
Fast CI при этом не запускается повторно.

Runner contract проверен по official GitHub runner-images inventory:
`ubuntu-24.04` является stable standard x64 label и включает Docker Engine,
Docker Compose и PowerShell 7. Workflow имеет только read-only permissions
`contents: read` и `actions: read`, использует `persist-credentials: false`,
timeout 90 минут и concurrency по ref/mode.

Cloud build требует официальный Anki release asset:

```text
version: 26.05
asset: anki-26.05-linux-x86_64.tar.zst
sha256: 6223d705563f71ab40ce072a5d96a3919c546d5dde1e4c49dc27975e70067274
source: GitHub Releases API asset digest, ankitects/anki release 26.05
```

`ANKI_REQUIRE_SHA256=1` делает отсутствие или несовпадение digest ошибкой
container build. Источник: [Anki 26.05 release](https://github.com/ankitects/anki/releases/tag/26.05).

### Public E2E artifact

Raw `e2e-artifacts/runtime/dashboard-ready.json` содержит token и никогда не
загружается. `scripts/prepare_ci_e2e_artifacts.py` создаёт отдельный `ci-e2e/`:

- удаляет token query parameters и известный runtime token;
- создаёт `dashboard-ready.redacted.json` без поля `token`;
- проверяет manifest paths на absolute/traversal/duplicates/missing files;
- отклоняет secret-like text и private home paths;
- сохраняет безопасные reports/screenshots/package и sanitized diagnostics;
- пишет `ci-e2e-summary.json` schema v2 и Markdown Step Summary с
  scope/workers/cache/build telemetry.

Artifact загружается через `if: always()` и хранится 7 дней. Canonical E2E exit
code сохраняется отдельно и восстанавливается после export/upload/cleanup:
диагностика не может превратить project failure в PASS.

Container image строится через pinned Buildx/build-push Actions, default
`docker` driver с включённым containerd image store и persistent
`type=gha,mode=max` zstd cache. Image попадает в runner без отдельного
docker-container export/import, а canonical
PowerShell contour запускает Compose без повторной сборки. Browser smoke
changes не инвалидируют Anki installation; pnpm lockfile-store также отдельный
layer. Runtime profile/token/readiness/screenshots не входят в build cache.

Public upload использует `compression-level: 0`. Manifest schema v2 индексирует
phase/screenshot/resource/performance reports; resource files optional только
при явно выключенной telemetry. Upload duration, artifact ID и digest
добавляются в GitHub Step Summary после upload. Полный baseline, formulas и
warm-cache policy: `docs/e2e-performance.md`.

`workflow_dispatch` требует наличия workflow в default branch, но run можно
направить на выбранную feature branch через exact ref. Для Stage 3 cloud proof
достаточны один Fast CI run и один targeted `standard/settings` E2E run на том же
branch HEAD; временный trigger не добавляется. Полные first/warm сравнения
относятся к отдельной performance-работе. `LOCAL PASS != GITHUB CI PASS`;
infrastructure failure также нужно отличать от project failure.

Structured changelog freshness входит в canonical local/Fast CI path:
`node scripts/run_python.mjs scripts/generate_changelog.py --check`. Product
notices дополнительно используют focused Python/Vitest suites; exact-SHA
real-Anki policy остаётся `settings` targeted и `full` при shared
runtime/package/E2E изменениях.
