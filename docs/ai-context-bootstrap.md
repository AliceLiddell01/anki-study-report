# Anki Study Report — AI context bootstrap

**Назначение:** компактная точка входа для ChatGPT, Codex и другого AI-агента.
Этот файл можно прикрепить к контексту проекта, но он не является замороженным
снимком текущего кода.

## Главное правило актуальности

Не считать `master` автоматически самым актуальным состоянием разработки.

```text
current branch production code/tests
→ current branch focused docs
→ PR/base branch contracts
→ fresh relevant reports/artifacts
→ older chats/plans
→ assumptions
```

Роли веток:

- `master` — релизная ветка; feature work от неё не начинать без явной задачи.
- `core` — integration branch обязательного production Core-трека.
- Feature/remediation PR от `core` может быть свежее `core` в своём scope.
- `gamification` и её feature branches — отдельный research/product track;
  research не означает production approval.
- Operations, Identity, Extensions и Platform/CI — независимые/условные треки.
  Их состояние определять по фактической branch/PR и профильному roadmap.

Перед любым выводом определить repository, current branch/PR, base/head SHA,
draft/merge state и changed files.

## Что представляет собой проект

Anki Study Report — локальный add-on для Anki 26.05+:

- Python runtime и bounded local API;
- React/TypeScript dashboard;
- token-protected loopback server;
- локальные учебные/profile data;
- sanitizer и Shadow DOM preview без JavaScript execution surface;
- Fast CI, package validation и risk-based real-Anki Docker E2E.

Ключевые каталоги:

```text
anki_study_report/   Python runtime/API
web-dashboard/       React/TypeScript dashboard
tests/               Python/contract tests
scripts/             build/package/verification
docker/anki-e2e/     real-Anki E2E
docs/                current contracts
roadmap/             tracks and completion criteria
reports/             historical evidence
```

## Обязательный порядок чтения

1. `AGENTS.md`.
2. `README.md` текущей branch.
3. `docs/ai-handoff.md` текущей branch.
4. `roadmap/README.md` и профильный track roadmap.
5. профильные current contracts в `docs/`.
6. production code и tests затронутого scope.
7. fresh closeout/report/artifact — только когда он нужен задаче.

Не утверждать, что файл, код, лог или artifact изучен, если он не был открыт.

## Выбор режима

### Обсуждение / продуктовый анализ

Не менять repository. Отделить подтверждённое решение от идеи. Показать ограничения,
реальную развилку и рекомендуемый следующий шаг. Не добавлять соседние stages.

### Аудит текущего состояния

Проверить фактическую branch/PR, code, tests, docs и доступное evidence. Итог разделить:

- подтверждено;
- расхождения;
- что не проверено;
- риски;
- минимальный следующий шаг.

### Планирование этапа

Один roadmap stage остаётся одним stage. Не создавать лестницы `1.4.2.a`.
Зафиксировать цель, scope/out of scope, dependencies, completion criteria и
verification contour.

### Подготовка промта для Codex

Выдать отдельный `.md`. Включить:

- модель и reasoning level;
- exact repository/base branch/current PR;
- обязательные файлы для чтения;
- одну конечную цель;
- in scope / out of scope;
- allowed paths или обязанность создать task contract;
- architecture/security invariants;
- tests/verification и stop-loss;
- Git полномочия;
- формат финального отчёта.

### ChatGPT + GitHub connector

Использовать `docs/chatgpt-work-mode.md`. Connector подходит для чтения и
ограниченных GitHub writes. Не создавать controller/status workflows вместо shell.
Не обещать локально выполненную команду без результата владельца.

### Codex + local checkout

Использовать `docs/codex-agent-rules.md` и `docs/codex-local-environment.md`.
Для нетривиальной реализации создать `.agents/task-contract.toml` из template и
проверить scope командой:

```powershell
$scopeArgs = @('scripts/run_python.mjs', 'scripts/check_task_scope.py')
& node @scopeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

### Анализ выполненной работы

Проверить реальный diff, commits, PR, test output и evidence. Не принимать
самоотчёт агента за PASS без доступного подтверждения.

## Архитектурные и security-инварианты

Без отдельного решения нельзя:

- давать frontend прямой доступ к Anki collection;
- менять payload/public behavior только на одной стороне;
- открывать local server наружу;
- ослаблять token validation, sanitizer, media validation, action allowlists,
  preview isolation или privacy boundaries;
- логировать tokens, token-bearing URLs, profile data или secrets;
- редактировать generated assets вручную;
- коммитить runtime outputs, `.ankiaddon`, archives, logs, screenshots, cache,
  profile data, tokens, `node_modules` или E2E artifacts;
- менять production code только ради устаревшего test/harness;
- добавлять speculative routes, APIs, aliases, compatibility layers или placeholders;
- переносить research package/evidence в Core/Fast CI молча;
- выполнять merge в `master`, release, deployment или publication без явного
  разрешения владельца.

## Защита от типичных ошибок AI

### «Исправил строку — сломал соседний consumer»

До изменения shared helper открыть callers/consumers и релевантные tests.
Regression сначала воспроизвести тестом, если это технически возможно.

### Одностороннее изменение контракта

Payload/public behavior требует синхронного изменения backend, frontend
types/validators, tests и docs.

### Старый отчёт победил production code

Reports — historical evidence. Они не имеют приоритета над current code/tests/docs.

### Scope creep

Для нетривиальной задачи использовать task contract с allowed paths.
Не исправлять найденный рядом cleanup/refactor, если он не блокирует задачу.

### Бесконечная перепроверка

```text
focused checks
→ canonical/Fast CI when required
→ one targeted real-Anki gate
→ final full only when actual diff requires it
```

Successful unchanged exact-SHA gate не повторять. После двух одинаковых или
смежных failures без новой информации остановиться и зафиксировать root cause.

### Огромный бесконечный чат

Одна coherent task/PR — одна рабочая сессия. Состояние хранить в repository
handoff/task contract, а не в памяти длинного чата.

### Локальная среда не меняет reasoning

Authoritative local Codex profile — Windows, PowerShell 7, существующий основной
checkout `C:\Users\KykLa\Documents\anki-study-report` и указанная владельцем
существующая task branch. Локально не использовать WSL, Bash, Git Bash,
`git worktree`, второй checkout или повторный clone. Linux в GitHub Actions,
Docker containers и cloud E2E остаётся допустимым.

## Минимальный рабочий цикл

```text
resolve branch/base/head
→ read AGENTS + handoff + focused contracts/code/tests
→ fill task contract
→ one bounded implementation
→ focused tests
→ inspect full diff
→ scope guard + git diff --check
→ one separate diff review
→ at most one bounded remediation
→ risk-required final verification
→ commit/PR/final report
```

## Формат финального отчёта

```text
Mode:
Repository / target branch:
Branch / base / HEAD:
Commit(s) / PR:

Подтверждено:
Изменено:
Проверки:
Не запускалось:
Ограничения:
Следующий шаг:
```

Не выдавать планы, будущую работу или непроверенный самоотчёт за выполненный результат.
