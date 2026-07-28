# AGENTS.md

Этот файл — короткая автоматически загружаемая точка входа для AI-агентов.
Он не заменяет профильные документы, production code или tests.

## Первые действия

Перед анализом или изменением репозитория:

1. Определи фактический режим: ChatGPT с GitHub connector или Codex с локальным checkout.
2. Зафиксируй repository, текущую branch, `HEAD`, base branch/PR и dirty/untracked files.
3. Прочитай:
   - `README.md`;
   - `docs/ai-handoff.md`;
   - профильный roadmap и current contract;
   - production code и tests затронутого scope.
4. Для нетривиальной реализации создай `.agents/task-contract.toml` из
   `docs/templates/task-contract.toml`.
5. Не начинай реализацию, пока цель, out of scope, allowed paths и completion criteria
   не образуют одну ограниченную задачу.

Команды локального preflight:

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD
git diff --stat
git ls-files --others --exclude-standard
```

## Роли веток

Не считай default branch автоматически самым актуальным рабочим состоянием.

- `master` — релизная ветка. Не использовать её как базу feature work и не менять
  напрямую без явной release/merge задачи владельца.
- `core` — integration branch обязательного production Core-трека.
- Feature/remediation branch или открытый PR, основанный на `core`, может содержать
  более свежее рабочее состояние своего scope, чем сама `core`.
- `gamification` и её feature branches — отдельный research/product track.
  Research evidence не является production approval и не переносится в Core молча.
- Operations, Identity, Extensions и Platform/CI оцениваются по фактической текущей
  branch/PR и профильному roadmap. Не смешивай независимые треки.
- При работе через GitHub connector сначала прочитай metadata текущего PR:
  `base`, `head`, SHA, draft/merge state и changed files.

При конфликте используй:

```text
current branch production code and tests
→ current branch README and focused docs
→ base branch contracts
→ fresh relevant reports/artifacts
→ older plans/messages
→ assumptions
```

## Режимы работы

Общие правила: `docs/ai-work-modes.md`.

- ChatGPT + GitHub connector: `docs/chatgpt-work-mode.md`.
- Codex + local checkout: `docs/codex-agent-rules.md`.
- WSL environment: `docs/codex-local-environment.md`.
- Ручные checkpointed операции: `docs/chatgpt-manual-operations.md`.
- Компактный внешний контекст: `docs/ai-context-bootstrap.md`.

Не смешивай полномочия режимов. GitHub Actions не является заменой локальному shell,
Git или `gh`.

## Task contract и scope guard

Для нетривиального code/docs change используй:

```bash
mkdir -p .agents
cp docs/templates/task-contract.toml .agents/task-contract.toml
```

Заполни contract до изменения кода. В нём обязательны:

- одна конечная цель;
- base ref;
- in scope и out of scope;
- allowed paths;
- acceptance criteria;
- выбранные проверки;
- stop conditions.

Перед commit и в финале выполни:

```bash
python scripts/check_task_scope.py
git diff --check
```

Scope guard не разрешает неожиданный файл только потому, что он оказался удобным
для исправления. Если задача реально требует расширения scope, сначала обнови contract
и явно объясни причину.

## Как менять код

1. Прочитай изменяемый code path, его callers/consumers и релевантные tests.
2. Для regression сначала добавь воспроизводящую проверку либо зафиксируй, почему
   автоматический тест невозможен.
3. Внеси минимальное изменение в правильный слой.
4. Проверь полный diff от base, а не только последний изменённый файл.
5. При изменении payload/public behavior синхронно обнови backend, frontend
   types/validators, tests и docs.
6. Shared helper не изменяется без проверки основных consumers.
7. Не делай adjacent refactor/cleanup, если он не нужен для correctness, security
   или completion criteria текущей задачи.

## Project-specific Core boundaries

- Перед изменением Core UI прочитай `roadmap/core/README.md`, профильные
  contracts/reports, production code, tests, `docs/test-matrix.md` и
  `docs/verification-run-policy.md`.
- Payload или public-behavior change обновляет все затронутые слои вместе:
  backend implementation, frontend types/parsers, tests и documentation.
- Cards имеет статус `ACCEPTED / COMPLETE / FROZEN`. Без новой доказанной
  regression не меняй Cards composition, queue, rail, drawer, expanded answer,
  native preview, AV/audio/GIF/media paths, Shadow DOM или Cards-specific
  styling ради Settings.
- После shared-shell changes выполняй только Cards regression smoke,
  пропорциональный фактическому риску.
- Codex не назначает numerical visual score и не объявляет owner visual
  acceptance. Evidence должно содержать объективные screenshots, geometry,
  diffs и deviation ledger.
- Artifact считается complete только после inventory, checksum и CRC
  validation.

## Неприкосновенные границы

Запрещено без отдельного обоснованного решения:

- давать frontend прямой доступ к Anki collection;
- открывать dashboard server наружу или ослаблять token validation;
- ослаблять sanitizer, media validation, action allowlists или preview isolation;
- логировать token, полный token-bearing URL, profile data или secrets;
- менять production code ради устаревшего test/harness assertion;
- редактировать generated dashboard assets вручную;
- коммитить `.ankiaddon`, archives, logs, screenshots, profile/runtime data,
  caches, `node_modules` или E2E outputs;
- добавлять speculative routes, APIs, compatibility aliases или placeholders;
- переносить research code/evidence в package или Fast CI без отдельного решения;
- выполнять release, deployment, publication или merge в `master` без прямого
  разрешения владельца.

## Проверки и stop-loss

Выбирай проверки по `docs/test-matrix.md` и
`docs/verification-run-policy.md`.

```text
focused checks
→ canonical non-Docker/Fast CI when required
→ one targeted real-Anki scope
→ final full only when actual diff requires it
```

- Successful unchanged exact-SHA gate не повторяется.
- Docker E2E не используется как пошаговый debugger.
- После failure сначала изучи первый failed step, logs, artifacts и root cause.
- После двух одинаковых или смежных failures без новой информации остановись.
- По умолчанию: один implementation pass, один diff review, один bounded remediation.
- Новый review не превращается в повторный аудит всего неизменившегося проекта.
- Честный `Paused/Incomplete` лучше бесконечной цепочки blind fixes и reruns.

## Финальный отчёт

Всегда отделяй:

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

Не утверждай, что файл, code path, command, CI run, log или artifact проверен, если
он фактически не был открыт или выполнен.
