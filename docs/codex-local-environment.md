# Локальная среда Codex

**Снимок:** 2026-07-30
**Статус:** authoritative local environment profile

Этот документ задаёт среду локального выполнения после того, как владелец выбрал
Codex mode. Он не меняет product scope, Git-полномочия конкретной задачи или
правила проверки из [`codex-agent-rules.md`](codex-agent-rules.md).

## Фиксированный профиль

```text
OS: Windows
Shell: PowerShell 7
Checkout: C:\Users\KykLa\Documents\anki-study-report
Working tree: existing main checkout
Task branch: existing owner-specified branch
```

Локально запрещены:

- WSL;
- Bash и Git Bash;
- `git worktree`;
- второй checkout;
- повторный clone репозитория;
- создание или переключение branch без отдельного прямого указания владельца.

Эти ограничения относятся только к локальной рабочей поверхности. Linux остаётся
допустимым:

- на GitHub Actions runners;
- внутри Docker containers;
- в cloud E2E и других штатных CI jobs.

## Checkout и paths

Все локальные команды запускаются из существующего checkout:

```text
C:\Users\KykLa\Documents\anki-study-report
```

Не создавать альтернативный рабочий корень, не зеркалировать repository в другой
каталог и не переносить задачу в отдельное рабочее дерево. Использовать Windows
paths и `-LiteralPath` для путей, которые могут содержать пробелы.

Перед mutation подтвердить, что фактическая branch совпадает с указанной
владельцем task branch и что unrelated dirty/untracked files не будут затронуты.

## PowerShell 7

Для native executables использовать argument arrays и проверять
`$LASTEXITCODE` сразу после каждого вызова:

```powershell
$statusArgs = @('status', '--short', '--branch')
& git @statusArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$headArgs = @('rev-parse', 'HEAD')
& git @headArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Для PowerShell cmdlets использовать named parameters или splatting и
`$ErrorActionPreference = 'Stop'` в bounded scripts. Не собирать исполняемые
команды строковой конкатенацией и не передавать их в другую shell.

Repository-owned `.ps1` entrypoints запускаются напрямую из PowerShell:

```powershell
$checkArgs = @('-SkipDocker')
& '.\scripts\run_full_check.ps1' @checkArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

## Toolchain

Версии Node.js, package manager и Python определяются current repository config,
lockfiles и canonical scripts. Перед изменением dependencies или окружения
сначала прочитать эти источники и выполнить read-only preflight:

```powershell
$gitVersionArgs = @('--version')
& git @gitVersionArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$nodeVersionArgs = @('--version')
& node @nodeVersionArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$pnpmVersionArgs = @('--version')
& pnpm @pnpmVersionArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$uvVersionArgs = @('--version')
& uv @uvVersionArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Не устанавливать или обновлять global tools, system packages, Docker settings
или project dependencies без необходимости в рамках текущей задачи. Не
использовать executable из другой OS surface.

Python repository scripts запускать через repository-owned runner:

```powershell
$scopeArgs = @('scripts/run_python.mjs', 'scripts/check_task_scope.py')
& node @scopeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

## Docker и cloud Linux

Локальный Docker запускается только через доступный Windows Docker context и
PowerShell entrypoint, когда его требует риск изменения или task contract.
Контейнеры могут быть Linux-контейнерами; это не разрешает переносить локальную
Git/filesystem работу в Linux shell.

GitHub Actions и cloud E2E продолжают использовать их штатные runner images и
container commands. Локальный PowerShell-only профиль не требует переписывать
workflow implementation и не запрещает Linux внутри CI.

## Git workflow

Codex работает в существующей task branch, указанной владельцем. В пределах
прямо разрешённой задачи можно:

- читать refs и PR metadata;
- изменять allowed paths;
- запускать проверки;
- создавать логические commits;
- выполнять обычный push;
- обновлять или создавать PR;
- выполнять Ready/merge только при отдельном прямом разрешении.

Без отдельного разрешения нельзя:

- создавать или переключать branch;
- создавать worktree или дополнительный checkout;
- повторно клонировать repository;
- force-push, переписывать историю или удалять branch;
- merge в `master`, release, deployment или publication.

## Task contract

Для нетривиального change использовать локальный ignored
`.agents/task-contract.toml`. Создать его из repository template можно так:

```powershell
$directoryArgs = @{
    ItemType = 'Directory'
    Path = '.agents'
    Force = $true
}
New-Item @directoryArgs | Out-Null

$copyArgs = @{
    LiteralPath = 'docs/templates/task-contract.toml'
    Destination = '.agents/task-contract.toml'
}
Copy-Item @copyArgs
```

Contract должен фиксировать exact branch/base, in/out of scope, allowed paths,
acceptance criteria, проверки и stop conditions. Он не становится шире только
потому, что рядом обнаружено несвязанное изменение.

## Cleanup и hygiene

Cleanup ограничивается outputs, созданными текущей задачей и явно признанными
безопасными для удаления. Не использовать recursive delete для checkout,
repository root, profile directories или вычисленного пути без проверки точного
resolved target.

Перед commit и в финале:

```powershell
$scopeArgs = @('scripts/run_python.mjs', 'scripts/check_task_scope.py')
& node @scopeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$diffArgs = @('diff', '--check')
& git @diffArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$statusArgs = @('status', '--short', '--branch')
& git @statusArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

Unrelated owner changes сохраняются. Reset, restore, stash, branch switch или
новое рабочее дерево не используются как способ получить «чистую» среду.

## Связанные документы

- [Codex work mode](codex-agent-rules.md)
- [Общие режимы работы](ai-work-modes.md)
- [AI context bootstrap](ai-context-bootstrap.md)
- [Test matrix](test-matrix.md)
- [Verification run policy](verification-run-policy.md)
