# Ручное сопровождение задач в ChatGPT mode

**Статус:** актуальный операционный runbook
**Снимок:** 2026-07-25
**Режим:** обычный ChatGPT + GitHub connector + локальная консоль владельца
**Канонический пример:** E2E-I4 cancellation/preflight closeout

Этот документ дополняет [`chatgpt-work-mode.md`](chatgpt-work-mode.md). Он описывает
не продуктовый или CI-контракт, а практический способ постепенно завершать
многошаговую работу после основной реализации, когда ChatGPT видит репозиторий и
GitHub, но локальные Git, WSL, PowerShell, Docker и `gh` запускает владелец.

Документ появился по итогам E2E-I4, где implementation, локальная remediation,
package-producing Fast CI, controlled cancellation A/B и artifact acceptance
потребовали последовательного ручного контура. Цель runbook — сохранить полезную
точность этого режима, но не повторять лишние двадцать итераций в следующих
задачах.

## Когда применять этот режим

Использовать ручное сопровождение ChatGPT mode, когда одновременно верны условия:

- работа уже ограничена одной веткой и одним основным PR;
- GitHub connector подходит для чтения кода, PR, jobs, logs и artifacts;
- connector не предоставляет нужную routine write/dispatch/cancel операцию;
- владелец может выполнять WSL или PowerShell команды;
- перенос задачи в Codex не требуется или временно невозможен;
- важна интерактивная диагностика по фактическому выводу каждого checkpoint.

Этот режим не должен превращаться в имитацию автономного агента через временные
controller/status workflows. Для routine Git, `gh`, Python, shell и artifact
inspection используется локальная консоль владельца.

## Модель ответственности

### ChatGPT

ChatGPT:

- восстанавливает exact repository/branch/PR/HEAD;
- читает production code, tests, docs, logs и artifacts;
- формулирует один ограниченный следующий checkpoint;
- создаёт отдельные скачиваемые scripts, когда copy-paste ненадёжен;
- указывает expected SHA-256 скачиваемого файла;
- анализирует полный возвращённый output;
- не объявляет локальную или cloud операцию выполненной до получения evidence;
- не делает merge/release/publication без прямого разрешения.

### Владелец

Владелец:

- запускает указанный checkpoint в правильной консоли;
- не смешивает параллельно ручные Git/CI операции с runner;
- возвращает полный output или сформированный diagnostic report;
- останавливается после failure вместо самовольного rerun;
- не публикует токены, private paths и несвязанные environment dumps.

### GitHub Actions

Постоянные workflows используются только в штатной роли:

- Fast CI — non-Docker checks и exact package producer;
- Docker E2E — exact package consumer и real-Anki integration gate;
- release — отдельный approval-gated delivery contour.

GitHub Actions не используется как удалённый shell, редактор branch или временный
контроллер ChatGPT.

## Рекомендуемая последовательность

### 1. Зафиксировать exact state

До mutation нужно проверить:

```text
repository
target branch
base branch
PR number
local HEAD
remote branch HEAD
working tree
expected dirty paths
gh authentication
required local tools
```

Минимальный read-only guard:

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/<branch>
git status --short --branch
gh auth status
```

Нельзя использовать `git reset --hard`, пока не доказано, что working tree не
содержит нужную работу владельца.

### 2. Решить: короткая команда или файл

Короткая операция из нескольких строк может быть дана inline.

Отдельный файл обязателен, когда есть:

- вложенные кавычки или heredoc;
- Python/PowerShell/Bash patch logic;
- больше одного fail-fast guard;
- SHA/branch/path verification;
- artifact parsing;
- controlled A/B orchestration;
- повторное использование после исправления.

Скачиваемый файл получает уникальное имя с задачей, step или short SHA:

```text
run_e2e_i4_controlled_ab_step20_5e52fae.py
```

Повторное использование общего имени вроде `runner.py` создаёт риск запуска старой
копии из `Downloads`.

### 3. Проверить целостность скачанного файла

Перед запуском:

```bash
EXPECTED_SHA="<sha256>"
actual_sha="$(sha256sum "$RUNNER" | awk '{print $1}')"
test "$actual_sha" = "$EXPECTED_SHA"
```

Если SHA не совпал, runner не запускается. Нельзя «попробовать всё равно».

`Unblock-File` выполняется только в Windows PowerShell:

```powershell
Unblock-File -LiteralPath "$HOME\Downloads\<file>"
```

Команда не существует в Bash/WSL и не нужна для обычного `python3 file.py` в WSL.

### 4. Один runner — один checkpoint

Хороший checkpoint:

```text
guard
→ одна ограниченная mutation
→ дешёвая focused verification
→ понятный final state
→ exit 0/не-0
```

Не следует заранее объединять в один giant runner:

```text
patch
→ полный suite
→ commit
→ push
→ Fast CI
→ Docker E2E
→ A/B
→ closeout
```

Объединение допустимо только после того, как предыдущие части уже отдельно
доказаны и повторное разделение не несёт диагностической пользы.

### 5. Делать patch state-aware

Patcher обязан проверять:

- exact branch и HEAD;
- exact expected dirty file set;
- exact old anchor или blob SHA;
- отсутствие несвязанных untracked files;
- idempotency либо явно заявленное одноразовое состояние.

Для partially applied patch нельзя слепо повторять исходный runner. Нужен
continuation/repair runner, который принимает только подтверждённое промежуточное
состояние.

### 6. Сначала дешёвые проверки

Обычный порядок:

```text
git diff --check
syntax/parser checks
focused tests
full non-Docker suite
package-producing Fast CI, если действительно нужен новый package
targeted/full Docker E2E согласно риску
controlled cloud acceptance
docs-only closeout
```

Full Docker E2E не используется как debugger. После cloud failure сначала
анализируются failed step, logs, summaries и artifacts.

### 7. Диагностировать первый реальный failure

Для GitHub Actions:

```bash
gh run view <run-id> --json status,conclusion,headSha,jobs,url
gh run view <run-id> --log-failed
gh run view <run-id> --job <job-id> --log
gh run download <run-id> --dir <output>
```

Источники истины:

```text
первый failed step
→ canonical summary/report
→ run-events
→ artifact contents
→ final wrapper/Restore result
```

Последний `Restore canonical result`, wrapper exception или upload warning может
быть вторичным следствием и не должен автоматически объявляться root cause.

### 8. Не ослаблять fail-closed package policy

Если complete-diff reuse validator отклоняет package reuse:

- не расширять allowlist ради прохождения текущего PR;
- определить, действительно ли diff package-impacting;
- при package-impacting или unknown diff запустить новый package-producing Fast CI;
- привязать E2E к exact Fast CI run, tested SHA и package SHA-256.

### 9. Controlled cancellation доказывать production concurrency

Для проверки `cancel-in-progress`:

1. Запустить A с exact inputs.
2. Дождаться, пока A реально войдёт в canonical long-running step.
3. Запустить B с теми же значениями concurrency identity.
4. Не использовать ручной `gh run cancel` как замену.
5. Проверить A=`cancelled`, B=`success`.
6. Скачать и валидировать оба artifacts.

Ручная отмена доказывает API cancellation, но не production concurrency group.

### 10. Валидировать source и public evidence на правильном уровне

Source canonical reports могут требовать byte-deterministic serialization.

Public artifact exporter может безопасно:

- редактировать private paths/tokens;
- pretty-print JSON;
- менять representation без изменения schema semantics.

Поэтому:

```text
source report  → byte-canonical + semantic validation
public report  → semantic/schema + sanitizer validation
```

Нельзя применять source byte-equality validator к намеренно перезаписанной public
копии.

### 11. Закрывать docs без нового тяжёлого прогона

После успешного exact production HEAD и cloud gates docs-only commit:

- обновляет contract, roadmap, handoff, indexes, final closeout и PR body;
- не требует повторного Fast CI/Docker E2E без изменения production/harness;
- не должен случайно начать следующий roadmap stage;
- не выполняет merge без отдельной команды.

## Проблемы, встретившиеся в E2E-I4

### Повреждённый длинный copy-paste block

**Симптом:** Bash потерял кавычки, Python text начал исполняться как shell, `!`
вызвал history expansion.

**Причина:** слишком большой inline block с nested quoting/heredoc.

**Исправление:** отдельный скачиваемый Python runner с SHA-256.

**Нужно было изначально:** после первой нетривиальной mutation перейти от
copy-paste к отдельному файлу.

### Потеря ведущего пробела в `git status --porcelain`

**Симптом:** `.github/...` превратился в `github/...`.

**Причина:** `.strip()` удалил значимый leading space из двухсимвольного `XY`
status field.

**Исправление:** удалять только trailing newline через `rstrip("\n")`.

**Нужно было изначально:** parser contract test на строки ` M path`, `M  path`,
`?? path`.

### Хрупкие anchors и partial patch

**Симптом:** patcher применил часть файлов и остановился на ожидаемом количестве
одинаковых anchors.

**Причина:** patch logic зависел от количества строк, а не от именованных функций
или exact state.

**Исправление:** state-aware repair runner; замена функций по имени; exact dirty
set.

**Нужно было изначально:** проектировать patcher как transactional checkpoint с
явным partial-state recovery.

### Отсутствующий `PyYAML` в project venv

**Симптом:** implementation была готова, но вспомогательная YAML-проверка не
запустилась.

**Причина:** validator не проверил собственные tool dependencies.

**Исправление:** использовать уже доступный system parser либо declared project
dependency.

**Нужно было изначально:** toolchain preflight до mutation.

### Отсутствующий `jsonschema`

**Симптом:** полный pytest остановился на collection.

**Причина:** `.venv` не была синхронизирована с `requirements-dev.txt`.

**Исправление:** установить полный dev requirements, а не один случайный package.

**Нужно было изначально:** проверить importability всех declared test
dependencies до первого full suite.

### `.venv` без `pip`

**Симптом:** `python -m pip` отсутствовал.

**Причина:** окружение создано через `uv` без embedded pip.

**Исправление:** `uv pip install --python .venv/bin/python -r requirements-dev.txt`.

**Нужно было изначально:** определить package manager по фактическому окружению,
а не предполагать наличие pip.

### Generated `__pycache__` нарушил hygiene test

**Симптом:** 978 тестов прошли, один cleanliness test упал.

**Причина:** предыдущий import оставил bytecode внутри add-on directory.

**Исправление:** удалить generated caches и запускать с
`PYTHONDONTWRITEBYTECODE=1`.

**Нужно было изначально:** cleanup generated outputs перед full suite и после
вспомогательных direct imports.

### PowerShell parser error `$code:`

**Симптом:** cloud E2E не стартовал, хотя Python contracts были зелёными.

**Причина:** PowerShell интерпретирует colon после variable name как часть
drive-qualified reference.

**Исправление:** `${code}:`; regression через
`System.Management.Automation.Language.Parser.ParseFile`.

**Нужно было изначально:** parser-backed syntax test для каждого изменённого
`.ps1` до Fast CI/E2E.

### Устаревшие string-based tests

**Симптом:** production contract изменился корректно, но tests искали старые
названия steps и literal implementation strings.

**Причина:** assertions проверяли incidental text, а не observable behavior.

**Исправление:** обновить behavioral/structural contracts, не возвращая legacy.

**Нужно было изначально:** одновременно менять production behavior и tests,
которые описывают именно новый контракт.

### Functional failure и cancellation смешивались

**Симптом:** cancellation могла превращаться в generic failure или терять
`130/143`.

**Причина:** отсутствовал отдельный canonical cancellation lifecycle.

**Исправление:** `cancellation-summary.json`, stable codes,
`phase/cancel → run/cancel`, exact exit/signal parity.

**Нужно было изначально:** проектировать cancellation как отдельный terminal
state, а не special case failure.

### `ASR-E2E-UNKNOWN`

`ASR-E2E-UNKNOWN` оставлен как редкий fail-closed fallback, когда run уже failed,
но known failure path не успела сохранить конкретный code. Он не является
нормальной категорией. Повторяющийся `UNKNOWN` означает диагностическую дыру,
которой нужен отдельный stable code или более ранняя persistence.

### `always()` удерживал тяжёлую финализацию при cancellation

**Симптом:** обычная artifact preparation/cleanup могла продолжаться после cancel.

**Причина:** `always()` истинно и для cancelled workflow.

**Исправление:** normal success/failure tail использует `!cancelled()`;
cancellation-only bounded tail — `cancelled()`.

**Нужно было изначально:** провести полный condition audit до cloud acceptance.

### «Успешный» upload без artifact

**Симптом:** upload step был зелёным, но GitHub artifact отсутствовал.

**Причина:** `if-no-files-found: warn` и `continue-on-error`.

**Исправление:** required cancellation upload использует
`if-no-files-found: error`; `continue-on-error` сохраняет overall conclusion
`cancelled`, но отсутствие evidence становится видимым в step.

**Нужно было изначально:** заранее определить обязательность каждого artifact и
fail policy для empty path.

### Root-owned bind-mounted evidence

**Симптом:** host не мог прочитать cancellation summary и записать host log.

**Причина:** container оставил artifact tree владельцем root.

**Исправление:** host log сначала пишется в `$RUNNER_TEMP`; после bounded compose
down ownership восстанавливается scoped `chown` только для `e2e-artifacts`;
затем log копируется и preparer читает evidence.

**Нужно было изначально:** нарисовать ownership lifecycle host/container для
каждого bind mount.

### Inner cleanup удалял canonical preflight report

**Симптом:** E2E успешно дошёл до manifest, но обязательный proof отсутствовал.

**Причина:** `run-e2e.sh` очищал весь artifact root после host preflight.

**Исправление:** очистка сохраняет только
`reports/preflight-report.json`, удаляя остальные stale outputs.

**Нужно было изначально:** определить producer/consumer ownership каждого
evidence path до добавления cleanup.

### Package reuse был отклонён

**Симптом:** существующий package нельзя было использовать для полного diff.

**Причина:** complete-diff содержал paths вне fail-closed allowlist.

**Исправление:** allowlist не ослаблялся; создан новый package-producing Fast CI.

**Нужно было изначально:** принять package identity decision до первого cloud E2E.

### Same-SHA rerun не давал новой информации

**Риск:** повторение старого failed run после code changes отсутствуют либо уже
локализован blocker.

**Правило:** новый cloud run нужен на новом SHA после конкретного исправления.
Rerun same SHA допустим только для классифицированного infrastructure failure.

### Ручной cancel не доказал бы concurrency

**Риск:** `gh run cancel A` показал бы signal handling, но не
`cancel-in-progress`.

**Исправление:** B был запущен с exact same concurrency identity и автоматически
отменил A.

### Старый runner в `Downloads`

**Симптом:** имя совпало, SHA — нет.

**Причина:** браузер/Windows сохранил старую копию под ожидаемым общим именем.

**Исправление:** уникальное имя с step/HEAD; поиск кандидата по SHA-256.

**Нужно было изначально:** never reuse generic downloadable filename внутри одной
долгой задачи.

### Byte-canonical validator на public JSON

**Симптом:** успешный artifact был ошибочно отклонён как
`serialization is not deterministic`.

**Причина:** sanitizer намеренно pretty-print-ил JSON.

**Исправление:** public copy валидируется по schema/semantics и sanitizer; source
copy — дополнительно byte-canonical.

**Нужно было изначально:** зафиксировать validation level для source и exported
evidence рядом с artifact contract.

### Inner и host artifact status выглядят противоречиво

Inner cancellation summary записывает состояние в момент signal handling:

```text
cleanup=partial
artifact=unavailable
```

Host workflow позже может остановить Compose, восстановить ownership и
опубликовать bounded artifact. Это два разных слоя и момента времени. Финальный
closeout обязан показывать оба, а не переписывать inner historical evidence.

## Что следует подготовить до первого запуска

Перед аналогичным этапом нужно заранее иметь:

- exact completion criteria;
- список изменяемых layers;
- signal/exit matrix;
- process ownership diagram;
- filesystem ownership diagram;
- source/public artifact distinction;
- normal/cancelled/failure step condition matrix;
- `if-no-files-found` policy;
- package reuse decision;
- parser/syntax checks для всех языков;
- environment dependency preflight;
- controlled A/B acceptance plan;
- artifact validation script;
- stop-loss criteria;
- final documentation inventory.

## Стандартный acceptance checklist

```text
[ ] exact branch/HEAD/PR
[ ] clean или exact expected dirty set
[ ] syntax/parser checks
[ ] focused tests
[ ] full non-Docker suite
[ ] package decision зафиксирован
[ ] Fast CI exact package PASS, если нужен
[ ] run A вошёл в intended active step
[ ] run B использовал ту же concurrency identity
[ ] A conclusion=cancelled
[ ] A bounded artifact существует и валиден
[ ] B conclusion=success
[ ] B public artifact валиден
[ ] no unrelated active/orphan resources
[ ] docs-only closeout без повторного тяжёлого gate
[ ] PR body соответствует фактам
[ ] merge не выполнен без отдельной команды
```

## Формат финального отчёта

```text
Mode: ChatGPT
Repository / target branch:
PR / implementation commits:

Подтверждено:
- exact facts and evidence identities

Изменено:
- production
- tests
- docs

Проверки:
- local
- Fast CI
- Docker E2E / controlled acceptance

Не запускалось:
- explicit list with reason

Осталось:
- only real limitations

Merge/release/publication:
- performed or explicitly not performed
```

## Case study: E2E-I4

```text
Implementation HEAD:
5e52faee5cd97af8e7760e2c5041c782ce4273fa

Fast CI:
30125233072 — success

Controlled run A:
30126100944 — cancelled
artifact 8609322435
digest sha256:9389b791b41bf6829b499f1dc491bc750725030f682ab7c4a63c7000901edaf1

Controlled run B:
30126228749 — success
artifact 8609400578
digest sha256:93133537cb8aff08a792da5475d6c5676fafd314cadf639936a731f8d0ad3dca

Browser:
23/23 items PASS

Screenshots:
18/18

Preflight:
20/20 checks PASS
```

Технический контракт: [`e2e-preflight-cancellation.md`](e2e-preflight-cancellation.md).
Финальный исторический отчёт:
[`../reports/ci/e2e-i4-cancellation-preflight-closeout.md`](../reports/ci/e2e-i4-cancellation-preflight-closeout.md).

## Внешние справочные материалы

- [GitHub Actions workflow cancellation reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation)
- [GitHub Actions concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [GitHub CLI: `gh workflow run`](https://cli.github.com/manual/gh_workflow_run)
- [GitHub CLI: `gh run view`](https://cli.github.com/manual/gh_run_view)
- [GitHub CLI: `gh run download`](https://cli.github.com/manual/gh_run_download)
- [PowerShell parsing](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing)
- [PowerShell `Parser.ParseFile`](https://learn.microsoft.com/en-us/dotnet/api/system.management.automation.language.parser.parsefile)
