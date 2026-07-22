# Codex local environment

Снимок окружения: **2026-07-22**.

Этот документ описывает фактический локальный профиль, который используется,
когда владелец выбирает **Codex mode** для задачи Anki Study Report. Он не
назначает Codex постоянным режимом проекта и не отменяет ChatGPT mode. Активный
режим выбирается владельцем для конкретной задачи и может временно зависеть от
доступных лимитов или нужного типа работы.

Общие правила выбора режима находятся в [`ai-work-modes.md`](ai-work-modes.md),
Codex-specific процесс — в [`codex-agent-rules.md`](codex-agent-rules.md).

## Surface и environment profile

Текущий подтверждённый контур:

```text
Surface: ChatGPT desktop app on Windows, Codex local worktree task
Environment profile: Anki extension
Agent runtime: WSL
Integrated terminal shell: WSL
Files open with: VS Code
```

Это не Codex CLI, не VS Code extension и не cloud task. Точный номер версии
настольного приложения не является репозиторным контрактом.

Setup и cleanup в профиле должны использовать отдельные Linux scripts. Факт
сохранения их последней редакции в UI проверяется владельцем отдельно; репозиторий
не должен делать вид, что настройка интерфейса подтверждена только по наличию
этого документа.

## WSL и filesystem

Текущая среда:

```text
Arch Linux under WSL 2
systemd enabled
native Linux filesystem
```

Основной source checkout на момент снимка:

```text
/home/kykla/projects/anki-study-report-r7-manual
```

Codex выполняет каждую задачу в отдельном worktree. Использовать переданные
профилем переменные:

```text
CODEX_SOURCE_TREE_PATH  source checkout
CODEX_WORKTREE_PATH     current task worktree
```

Путь task worktree является динамическим. Скрипты не должны hard-code путь
конкретной прошлой задачи.

Рабочее дерево должно оставаться в `/home/...`, а не в `/mnt/c/...`. Не смешивать
Linux и Windows executables или filesystem paths без отдельной необходимости.

## Toolchain

Setup обязан проверить наличие Linux-версий:

```text
git
node
pnpm
uv
```

Проектный Python создаётся как:

```text
.venv/bin/python
```

Версия берётся из `.python-version`; для текущего проекта это Python 3.11.
Системный Arch `python3` может иметь другую версию и не является проектным
runtime. Не полагаться на необязательный `python` alias.

Текущий host-tooling snapshot:

```text
Node 20.20.2
pnpm 9.15.9
system python3 3.14.6
Docker Engine 29.6.2
Docker Compose 5.3.1
Docker Buildx 0.35.0
Docker context default
```

Номера версий являются диагностическим снимком, а не вечным pin. Источником
поддерживаемых проектных версий остаются repository config, lockfiles и CI.

Для критических verification commands допустимо удалить `/mnt/*` entries из
process `PATH`, чтобы Windows executables не затеняли Linux tooling. Ожидаются
Linux paths вроде `/usr/bin/git`, `/usr/bin/docker` и `/usr/bin/pwsh`.

Canonical `scripts/run_full_check.ps1` сохраняет Windows candidates для Windows
CI, но в Linux/WSL выбирает только native command names и отвергает `.exe`,
`.cmd`, `.bat`, Windows-style и `/mnt/<drive>/...` executable paths.

## Permanent environment preflight

Каждая новая Codex task до чтения task checkout как актуального source of truth,
branch creation, dependency setup, edits или tests выполняет:

```bash
bash scripts/codex-environment-preflight.sh \
  --expected-base origin/core \
  --fetch \
  --require-clean
```

Preflight является read-only относительно tracked files и local branches. Он:

- требует явные `CODEX_SOURCE_TREE_PATH` и `CODEX_WORKTREE_PATH` без fallback на
  current directory;
- требует, чтобы оба реальных пути находились под `/home/...` и не разрешались
  через symlink в `/mnt/*`;
- подтверждает exact repository identity для source checkout и task worktree;
- отвергает Windows executables и mounted-drive tool paths;
- проверяет Node, pnpm и Python versions по актуальным repository config;
- проверяет HTTPS/SSH transport, `core.sshCommand`, `ssh.variant`, `GIT_SSH` и
  `GIT_SSH_COMMAND` без вывода credentials;
- при `--fetch` выполняет только `git fetch origin --prune`, проверяет
  authentication и фиксирует exact SHA `origin/core`;
- сообщает ahead/behind local `core`, но не fast-forward, reset или move branches;
- при `--require-clean` блокирует tracked и untracked changes, ничего не удаляя.

Canonical owner transport после локального repair:

```text
HTTPS origin
GitHub CLI authentication
GitHub CLI credential helper
```

`CODEX_SOURCE_TREE_PATH` и `CODEX_WORKTREE_PATH` являются repository environment
contract, а не заявленным публичным OpenAI API. Факт того, что desktop Codex
project/profile сохранил source folder и предоставляет dynamic worktree variable,
остаётся owner-verified platform acceptance. Отсутствующая dynamic variable или
повторное открытие `/mnt/*` является blocker; current directory не используется
как неявная замена.

Режимы:

```text
default    local environment/config checks, без network call
--fetch    git fetch origin --prune и freshness/authentication checks
--offline  запрет network calls для unit tests и локальной диагностики
--require-clean  fail на tracked/untracked changes
```

Exit codes:

```text
0  PASS
2  environment/path/tool/config blocker
3  GitHub authentication или fetch blocker
4  repository identity, expected-base или dirty-state blocker
```

Output имеет bounded machine-readable-ish summary и не содержит token, credential
value, полного environment dump или token-bearing remote URL.

## Docker

Используется native Docker Engine внутри Arch WSL:

```text
socket: /var/run/docker.sock
services: docker.service, containerd.service
context: default
```

Docker Desktop, Docker Desktop WSL integration и remote Docker context не
являются текущим контуром.

Codex может использовать уже работающий daemon и запускать разрешённые задачей
build/test commands. Без отдельного согласования нельзя:

- устанавливать или обновлять системные Docker packages;
- менять daemon configuration;
- выполнять `systemctl enable/disable`;
- удалять чужие images, volumes или containers;
- делать глобальный Docker cleanup.

## Setup contract

Linux setup script должен:

1. Перейти в `${CODEX_WORKTREE_PATH:?CODEX_WORKTREE_PATH is not set}`.
2. Проверить `git`, `node`, `pnpm` и `uv`.
3. Прочитать `.python-version`.
4. Создать или переиспользовать `.venv` нужной версии.
5. Установить `requirements-dev.txt` в `.venv`.
6. Выполнить `pnpm install --frozen-lockfile`.
7. Проверить Python source через `ast.parse` без генерации bytecode.
8. Вывести версии основных инструментов и фактический worktree.

Рекомендуемая переменная процесса:

```bash
export PYTHONDONTWRITEBYTECODE=1
```

Setup не должен:

- запускать `sudo pacman` или другой system package manager;
- менять WSL, systemd, `/etc/wsl.conf` или Windows settings;
- запускать или настраивать Docker daemon;
- собирать Docker image;
- запускать real-Anki E2E;
- менять Git history, commit или push;
- сбрасывать unrelated changes.

Если обязательный системный инструмент отсутствует, setup завершает работу с
понятной ошибкой вместо скрытого изменения системы.

## Cleanup contract

Automatic cleanup удаляет только generated project outputs:

```text
__pycache__/
.pytest_cache/
web-dashboard/dist/
anki_study_report/web_dashboard/
anki_study_report.ankiaddon
known temporary local-input APKG created by the task
```

Cleanup сохраняет:

```text
.venv/
web-dashboard/node_modules/
Docker images and volumes
e2e-artifacts/
E2E screenshots
diagnostics and logs
```

E2E evidence сохраняется, потому что оно может быть необходимо для анализа
failure или owner review. Его последующее удаление выполняется осознанно после
закрытия задачи.

Cleanup не выполняет:

```text
git reset --hard
git clean -fdx
git checkout .
git restore .
docker compose down -v
system-wide Docker prune
```

Он не должен затрагивать параллельные worktrees или чужую диагностику.

## Git и автономность

В своём task worktree Codex может:

- fetch актуальных refs;
- создать одну task branch от актуального `origin/core`;
- читать и изменять repository files;
- устанавливать project-local dependencies;
- запускать tests, typecheck, build, package validation и разрешённый Docker E2E;
- делать логические commits;
- push собственной branch;
- создать или обновить один основной PR в `core`;
- исправлять свой PR после CI или review.

По умолчанию Codex готовит проверенный PR и останавливается для owner review.
Merge в `core` допускается только когда конкретный prompt прямо его разрешает.

Без отдельного разрешения запрещены:

- force-push;
- прямое переписывание `core` или `master`;
- merge в `master`;
- удаление чужих branches;
- изменение system/global configuration;
- действия вне repository worktree;
- создание controller/trigger/status PR chains.

## Verification boundary

Полная автономность разрешена для focused project checks. Docker real-Anki E2E
разрешён, когда он требуется `test-matrix.md`, `verification-run-policy.md` или
реальным integration risk.

E2E не используется как пошаговый debugger. Сначала выполняются focused checks,
затем targeted E2E для локализованного риска и один final full gate для готового
кандидата, если он обязателен. Successful unchanged exact-SHA run не повторяется
без новой причины.

## Что остаётся task-specific

Следующее не закрепляется этим environment contract и должно задаваться конкретным
prompt:

- активный режим ChatGPT или Codex;
- модель и reasoning effort;
- product scope и completion criteria;
- нужна ли task branch/PR;
- разрешён ли merge в `core`;
- required test set;
- нужен ли постоянный report в `reports/`.

Так временное использование доступного Codex quota не превращается в постоянный
репозиторный default, а возвращение к ChatGPT mode не требует изменения этих
документов.
