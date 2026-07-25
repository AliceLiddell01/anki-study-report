# Режим работы ChatGPT

Снимок правил: **2026-07-25**.

Этот документ применяется, когда работа идёт в обычном чате ChatGPT, репозиторий
доступен через GitHub connector, а локальные команды при необходимости выполняет
владелец проекта.

Общие инварианты и выбор режима описаны в
[`ai-work-modes.md`](ai-work-modes.md). Codex-specific правила находятся в
[`codex-agent-rules.md`](codex-agent-rules.md). Пошаговое ручное сопровождение
описано в [`chatgpt-manual-operations.md`](chatgpt-manual-operations.md).

## Назначение режима

ChatGPT mode подходит для:

- восстановления фактического контекста проекта;
- продуктового и архитектурного анализа;
- подготовки bounded implementation plan;
- чтения и изменения репозитория через GitHub connector;
- управления существующими branches, PR, issues и comments;
- ограниченных docs/code edits;
- анализа CI/E2E logs и artifacts;
- выдачи владельцу точных локальных команд или небольших скриптов.

ChatGPT не должен имитировать автономный локальный агент с помощью цепочки
служебных GitHub workflows и trigger PR.

## Начало задачи

1. Явно определить repository, target branch/PR и scope.
2. Открыть `README.md`, `docs/ai-handoff.md` и профильные документы.
3. Для реализации проверить текущий production code, tests и состояние PR/branch.
4. Отделить уже принятое решение от идеи, предположения и historical evidence.
5. Выбрать один конечный результат задачи без создания новых подэтапов.

Если корректное рабочее предположение можно сделать из текущего контекста, не
останавливать задачу лишним уточняющим вопросом.

## Работа через GitHub connector

Connector используется для:

- чтения repository files, commits, PR и issues;
- compare/diff и review;
- создания или обновления branch/files/PR по прямой просьбе;
- чтения workflow metadata, jobs, logs и artifacts, когда функция доступна.

Ограничения connector не должны компенсироваться временной инфраструктурой в
репозитории.

Запрещено создавать только ради управления из чата:

- write-capable controller workflows;
- trigger-only PR;
- status/observer workflows;
- branch-rewrite workflows;
- отдельный PR для каждого мелкого исправления;
- workflow, который заменяет обычные `git`, `gh`, Python или shell commands.

Если connector не умеет безопасно выполнить routine operation, ChatGPT выдаёт
команду для WSL/PowerShell или предлагает перенести implementation в Codex.

## Локальная консоль владельца

Владелец проекта может использовать **WSL** и **PowerShell**. ChatGPT вправе
просить выполнить команды в любой из этих сред, если это быстрее и надёжнее
служебной GitHub automation.

Предпочтения:

- WSL — Linux tooling, Git, Docker, shell scripts, inspection of artifacts и
  долгие локальные операции;
- PowerShell — существующие repository `.ps1` entrypoints, Windows-specific
  commands и `Unblock-File`;
- не переносить проект между Windows и WSL filesystem без необходимости;
- в каждой инструкции явно указывать, в какой консоли выполнять команду.

ChatGPT не должен утверждать, что локальная команда выполнена, пока владелец не
вернул её результат.

## Правила выдачи скриптов

Каждый новый скрипт, который владелец должен скачать и запустить, выдаётся
**отдельным файлом**, а не большим copy-paste блоком в сообщении.

Перед ссылкой на каждый новый файл обязательно показывается команда PowerShell:

```powershell
Unblock-File -LiteralPath "<полный-путь-к-файлу>"
```

Если точный путь после скачивания неизвестен, используется понятный пример:

```powershell
Unblock-File -LiteralPath "$HOME\Downloads\script-name.ps1"
```

Требования к скриптам:

- один скрипт — одна понятная задача;
- минимальное количество quoting, escaping и nested here-string;
- не встраивать большие исходники, JSON, YAML или Markdown в PowerShell, когда
  можно передать отдельный файл;
- не смешивать Git, patch generation, тестирование, artifact parsing и cleanup в
  одном гигантском скрипте;
- использовать явные параметры и fail-fast checks;
- не добавлять интерактивность без необходимости;
- команды короче нескольких строк предпочтительно выдавать как команды, а не как
  новый скрипт;
- не создавать второй скрипт, если существующий можно безопасно исправить;
- давать длинному runner уникальное имя с task/step/short SHA;
- публиковать SHA-256 и не запускать файл при mismatch;
- не повторять исходный patcher после partial application — использовать state-aware continuation.

`Unblock-File` относится только к скачанным файлам ChatGPT mode. Файлы, созданные
локально Codex внутри checkout, не требуют этого ритуала.

## Пошаговая ручная работа после implementation

Для задач, где владелец последовательно запускает WSL/PowerShell checkpoints,
используется постоянный runbook:
[`chatgpt-manual-operations.md`](chatgpt-manual-operations.md).

Основные правила:

- exact branch/HEAD/dirty-set guard до каждой mutation;
- один checkpoint не смешивает все оставшиеся стадии без необходимости;
- локальный output возвращается полностью;
- cloud failure сначала локализуется по первому failed step и artifact;
- source и sanitized public evidence валидируются на разных уровнях;
- controlled cancellation доказывается successor run в той же concurrency group;
- docs-only closeout не повторяет уже зелёный unchanged production gate.

## Реализация и Git

Для одной coherent задачи по умолчанию:

```text
одна ветка
→ один основной PR
→ нужные commits
→ один closeout
```

Разрешено обновлять уже существующий основной PR вместо создания нового.

Не создавать новый branch/PR только для:

- запуска проверки;
- изменения hard-coded SHA;
- публикации status;
- временного controller;
- удаления предыдущего controller;
- отдельного documentation closeout, который можно включить в основной PR.

ChatGPT не делает merge в `master`, release, deployment или publication без
отдельного прямого разрешения владельца.

## Локальные проверки

В ChatGPT mode разрешены все локальные проверки, включая:

- Python and frontend focused tests;
- typecheck и production build;
- package build/validation;
- canonical non-Docker check;
- Docker real-Anki targeted E2E;
- Docker real-Anki full E2E.

Выбор проверок всё равно обязан соответствовать риску изменения и
`test-matrix.md` / `verification-run-policy.md`.

Правила:

- сначала дешёвые focused checks;
- Docker E2E запускать после локализации проблемы, а не после каждой строки;
- full E2E не использовать как debugger;
- не повторять unchanged exact-SHA run;
- после конкретного harness failure сначала разобрать logs/artifacts и код;
- один исправленный final candidate обычно получает один full E2E;
- второй full допустим после конкретного исправления blocker либо по прямому
  разрешению владельца;
- дальнейшие повторы прекращаются и оформляются как honest limitation, если не
  появляется новая информация.

## Коммуникация во время работы

Для долгой задачи ChatGPT кратко сообщает:

- что уже установлено;
- какой blocker найден;
- что будет сделано следующим;
- когда требуется локальная команда владельца.

Не перегружать пользователя низкоуровневыми сообщениями о каждом API call или
каждом открытом файле.

Запрещено обещать фоновую работу или результат после завершения текущего ответа.

## Финальный отчёт ChatGPT mode

Финал содержит:

```text
Mode: ChatGPT
Repository / target branch:
Branch / PR / commits:

Подтверждено:
- ...

Изменено:
- ...

Проверки:
- ...

Не запускалось:
- ... — причина

Осталось:
- только реальные ограничения или риски
```

Если владелец должен выполнить локальную команду, она отделяется от уже
выполненных действий и снабжается указанием `WSL` или `PowerShell`.

## Язык PR, отчётов и handoff-документов

Если PR ведётся на русском языке, весь человекочитаемый текст должен быть на русском:

- заголовок и описание PR;
- названия разделов, статусы, выводы и пояснения;
- closeout-отчёты, roadmap-статусы и handoff-сводки;
- комментарии о проверках, ограничениях и следующих шагах.

На английском сохраняются только элементы, перевод которых снижает техническую точность:

- точные идентификаторы и значения полей схемы;
- пути, команды, SHA-256, digest и имена файлов;
- названия workflow, job, GitHub Actions inputs и API;
- `Fast CI`, `E2E`, `GHCR`, `APKG`, `JSON`, `YAML` и другие устоявшиеся технические обозначения;
- дословные сообщения инструментов, если они приводятся как evidence.

Не использовать смешанные человекочитаемые формулировки вроде `cloud acceptance pending`, `implementation complete`, `out of scope` или `not run`, когда существуют точные русские варианты. PR должен быть достаточно подробным для review, а closeout-отчёт — хранить полную проверяемую историю этапа без дублирования актуального production-контракта.
