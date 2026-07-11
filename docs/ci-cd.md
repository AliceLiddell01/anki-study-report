# CI Foundation

Снимок документации: 2026-07-11.

В проекте реализованы быстрый автоматический Fast CI и отдельный ручной Full
Docker / Anki E2E. CD, release automation и публикация на AnkiWeb отсутствуют.

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

Она выполняет repository hygiene, pytest, TypeScript typecheck, Vitest,
production build с копированием assets в add-on, сборку `.ankiaddon` и две
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

Каждый run пытается загрузить artifact с именем:

```text
ci-fast-<run-id>-<run-attempt>
```

Структура:

```text
ci-fast/
├─ ci-summary.md
├─ ci-summary.json
├─ environment.txt
├─ logs/
│  └─ fast-check.log
└─ package/
   └─ anki_study_report-ci.ankiaddon
```

Package — краткоживущий non-release CI build, а не release. Artifact хранится
14 дней и не коммитится. Upload выполняется через `if: always()` и требует
наличия artifact directory; падение canonical command остаётся падением job.

`ci-summary.json` использует `schemaVersion: 1` и содержит repository, exact
commit SHA/ref/event, workflow/run metadata, runner и runtime versions,
canonical command, result/timestamps, `checks[]`, `artifactFiles[]` и
`failureCategory`. `ci-summary.md` также добавляется в GitHub Step Summary.
Summary и environment не содержат tokens, token-bearing URLs, пользовательские
Anki paths или profile data.

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

## Не входит в CI Foundation

- Docker/реальный Anki Desktop E2E;
- strict APKG browser smoke и Perf100;
- Codex CI consumer;
- автоматическая local fallback orchestration;
- tag/release/AnkiWeb CD;
- deployment, self-hosted runners, OIDC и secrets.

Будущие этапы могут добавить отдельного consumer машиночитаемого результата,
управляемый local fallback и release CD, но они не должны ослаблять или
дублировать текущую canonical test logic.

## Full Docker / Anki E2E

`.github/workflows/ci-e2e.yml` — второй независимый CI-контур. Он использует
standard x64 runner `ubuntu-24.04`, PowerShell 7 и установленный Docker Engine /
Docker Compose. Workflow остаётся manual-only после bootstrap и имеет один
typed choice input:

| Mode | Project command |
| --- | --- |
| `standard` | `run_full_check.ps1 -DockerOnly` |
| `strict-apkg` | `run_full_check.ps1 -DockerOnly -RequireApkgFixture` |
| `perf100` | `run_full_check.ps1 -DockerOnly -RequireApkgFixture -Perf100` |

Workflow не повторяет `run-e2e.sh`, APKG import или browser smoke. Он выбирает
только заранее заданный режим и вызывает существующую project orchestration.
Fast CI при этом не запускается повторно.

Runner contract проверен по official GitHub runner-images inventory:
`ubuntu-24.04` является stable standard x64 label и включает Docker Engine,
Docker Compose и PowerShell 7. Workflow имеет `permissions: contents: read`,
`persist-credentials: false`, timeout 90 минут и concurrency по ref/mode.

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
- пишет stable `ci-e2e-summary.json` schema v1 и Markdown Step Summary.

Artifact загружается через `if: always()` и хранится 7 дней. Canonical E2E exit
code сохраняется отдельно и восстанавливается после export/upload/cleanup:
диагностика не может превратить project failure в PASS.

`workflow_dispatch` доступен только когда workflow уже находится в default
branch. Поэтому первый branch cloud proof использует временный exact-branch
`push` trigger; перед merge он удаляется. Final exact-master proof выполняется
manual dispatch для `strict-apkg`, затем `perf100`. `LOCAL PASS != GITHUB CI
PASS`; infrastructure failure также нужно отличать от project failure.
