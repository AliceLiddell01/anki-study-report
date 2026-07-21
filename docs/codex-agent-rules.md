# Режим работы Codex

Снимок правил: **2026-07-21**.

Этот файл применяется только к **Codex mode**: агент имеет локальный checkout,
shell и может выполнять многофайловую реализацию, тесты и Git workflow
непосредственно в рабочем дереве.

Общие инварианты и выбор режима описаны в
[`ai-work-modes.md`](ai-work-modes.md). Правила обычного чата находятся в
[`chatgpt-work-mode.md`](chatgpt-work-mode.md).

## Граница режима

Codex может автономно:

- читать и изменять локальное рабочее дерево;
- создавать или переключать branch;
- выполнять shell, Git, tests, build и Docker commands;
- делать логические commits;
- push и открывать draft PR, если это соответствует задаче;
- rebase/merge в разрешённых владельцем границах.

Codex не должен применять ChatGPT-specific процесс скачиваемых файлов:

- скрипты создаются прямо в checkout;
- `Unblock-File` для созданных Codex файлов не требуется;
- не нужно передавать владельцу локальный скрипт, если Codex может выполнить его
  самостоятельно.

Если задача выполняется без локального checkout через GitHub connector и команды
запускает владелец, это ChatGPT mode, а не Codex mode.

## Старт каждой задачи

Прочитать в порядке:

1. `README.md`;
2. `docs/ai-handoff.md`;
3. `roadmap/README.md` и профильный roadmap;
4. текущий production code и tests нужного scope;
5. профильный contract и последний relevant report.

Затем выполнить:

```powershell
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard
```

Не трогать unrelated dirty changes. Если они есть, сохранить их и явно отметить
в финальном отчёте.

Перед реализацией зафиксировать один конечный результат задачи. Не создавать
новые вложенные подэтапы, буквенные ветки или дополнительную roadmap-нумерацию,
если их не определил владелец.

## Source of truth

Использовать приоритет:

```text
current production code and tests
→ current README and focused docs
→ fresh reports and artifacts
→ older plans and messages
→ assumptions
```

Основные источники:

- Payload: `anki_study_report/dashboard_payload.py`,
  `web-dashboard/src/types/report.ts`, payload tests.
- Package: `scripts/package_addon.py`, package tests.
- Docker E2E: `docker/anki-e2e/README.md`, E2E scripts and artifacts.
- Frontend routes: `web-dashboard/src/app/router.tsx`.
- Fast CI: `.github/workflows/ci-fast.yml`, `scripts/run_full_check.ps1`,
  `docs/ci-cd.md`.
- Search and Safe Actions: `docs/search-query-foundation.md`,
  `docs/search-v1-and-safe-actions.md`, runtime/services and frontend workspace.
- Localization: `docs/localization.md`, `web-dashboard/src/i18n/`, parity tests.
- Security: `docs/security-and-safety.md`.
- Test selection: `docs/test-matrix.md` and
  `docs/verification-run-policy.md`.

Не утверждать, что файл, code path, log или artifact изучен, если он не был
фактически открыт.

## Организация работы

Для одного coherent stage/remediation по умолчанию:

```text
одна рабочая ветка
→ один основной PR
→ логические commits
→ один closeout
```

Запрещено превращать одну задачу в цепочку отдельных trigger, controller, status,
verification и cleanup PR.

Docs и cleanup, непосредственно относящиеся к реализации, включаются в основной
PR либо в один финальный механический closeout, если технически невозможно
сделать это безопасно в основном PR.

Не расширять scope соседними stages, refactor или cleanup только потому, что они
замечены по пути. Исправлять adjacent defect можно лишь когда он блокирует
корректность, безопасность или проверку текущей задачи.

## Консоль и скрипты

Codex выбирает среду по фактической задаче:

- WSL/Linux shell — Linux tooling, Docker, artifact inspection и shell scripts;
- PowerShell — canonical repository `.ps1` entrypoints и Windows-specific checks.

Не смешивать Windows и WSL paths без необходимости.

Скрипты должны быть простыми:

- один скрипт — одна понятная задача;
- минимальное количество nested quoting, escaping и here-string;
- большие JSON/YAML/Markdown/patch contents хранить отдельными файлами;
- fail fast на неверном branch, dirty state или missing dependency;
- не объединять Git history rewriting, patching, tests, artifact parsing и cleanup
  в один гигантский скрипт;
- короткую операцию выполнять прямой командой, а не новым helper script.

Temporary helper удаляется в том же PR, когда перестаёт быть частью постоянного
репозиторного контракта.

## Что нельзя делать

- Не менять generated files руками.
- Не коммитить runtime outputs.
- Не ослаблять sanitizer, media validation, token checks, action allowlists,
  loopback или privacy boundaries.
- Не менять production payload ради устаревшего теста.
- Не откатывать unrelated изменения.
- Не открывать dashboard server наружу.
- Не логировать полный token-bearing URL или secret values.
- Не превращать Cards preview в iframe/JavaScript execution surface.
- Не добавлять пользовательский UI-текст вне locale resources.
- Не удалять compatibility/fallback/adapter слой без проверки его фактического
  использования и актуального audit evidence.
- Не коммитить `.ankiaddon`, E2E outputs, screenshots, profiles, logs, tokens,
  cache, `node_modules`, generated dashboard assets или archives.
- Не использовать GitHub Actions как удалённый терминал, branch editor или
  пошаговый debugger.
- Не создавать временный workflow только потому, что routine shell operation
  проще выполнить локально.

Generated/runtime outputs включают:

```text
e2e-artifacts/
web-dashboard/dist/
web-dashboard/screenshots/
anki_study_report/web_dashboard/
anki_study_report/user_files/
*.ankiaddon
*.zip
__pycache__/
.pytest_cache/
node_modules/
```

## Как править safely

1. Прочитать current code и tests вокруг контракта.
2. Проверить фактическое behavior/data shape.
3. Внести минимальное изменение в правильный слой.
4. Синхронно обновить backend, frontend types/validators, tests и docs, если
   меняется public payload или behavior.
5. Запустить проверки согласно риску.
6. Проверить `git diff --check` и tracked/untracked hygiene.
7. Сделать self-review только текущего diff, без повторного аудита неизменившегося
   проекта.

Если actual behavior корректно, а assertion устарел, обновить test/harness, а не
production code.

## Проверки

Для package changes:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

Canonical non-Docker check:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Docker real-Anki E2E разрешён локально и выбирается по текущему риску.

Правила stop-loss:

- focused checks выполнять до тяжёлого gate;
- targeted E2E использовать для локализованного product scope;
- full E2E запускать для готового final candidate, а не после каждой правки;
- не повторять successful unchanged exact-SHA run;
- после harness failure сначала анализировать logs/artifacts и код;
- после двух одинаковых или смежных failures без новой информации остановиться;
- один исправленный candidate обычно получает один final full run;
- второй full допустим после конкретного blocker fix или прямого разрешения
  владельца;
- честный `Paused/Incomplete` лучше бесконечной verification campaign.

Failure harness не называется production regression без подтверждения production
behavior.

## Git workflow

Commit messages описывают фактическое изменение естественным техническим языком,
без названия этапа и пересказа prompt:

```text
docs: separate ChatGPT and Codex work modes
fix(cards): preserve inspection profile fixtures in full smoke
```

Не force-push без явного разрешения владельца, кроме заранее согласованной
нормализации собственной disposable task branch. Не терять и не перетирать чужие
изменения.

Не merge в `master`, не создавать release/tag/deployment и не публиковать в
AnkiWeb без отдельного прямого разрешения.

## Финальный отчёт Codex mode

Указать:

```text
Mode: Codex
Branch:
Commit(s):
PR:

Подтверждено:
- ...

Изменено:
- ...

Проверки:
- ...

Не запускалось:
- ... — причина

Ограничения:
- только реальные оставшиеся риски
```

Если commit не сделан, явно сообщить это и привести смысл текущего
`git status --short --branch`.

## Release automation

- Не dispatch-ить production release только для проверки реализации.
- Release разрешён лишь с current `master`, явной version/channel и required
  approval.
- Не переносить credentials в CLI args, files, reports, commits или PR text.
- Не подменять exact release archive Fast CI package или повторной сборкой.
- Не перезаписывать published SemVer assets: changed bytes требуют новой версии.
- В handoff фиксировать exact commit, artifact SHA, каждый gate и отдельно факт
  dry-run/production publication.
