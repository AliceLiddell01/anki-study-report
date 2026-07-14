# Правила для Codex/AI-агента

For runtime work: Fast CI exact SHA before E2E, one targeted scope, one final
full; no blind, warm-cache or successful same-SHA reruns. See
`verification-run-policy.md`.

Снимок документации: 2026-07-13.

Этот файл можно дать новому агенту как prompt-like инструкцию для работы в
репозитории.

## Старт каждой задачи

1. Выполни:

```powershell
git status --short --branch
```

2. Для нетривиальных задач также проверь:

```powershell
git diff --stat
git ls-files --others --exclude-standard
```

3. Не трогай unrelated dirty changes. Если они есть, явно отметь это в финале.

## Source of truth

- Payload: `anki_study_report/dashboard_payload.py`,
  `web-dashboard/src/types/report.ts`, `tests/test_dashboard_payload.py`.
- Package: `scripts/package_addon.py`, package tests.
- Docker E2E: `docker/anki-e2e/README.md`, E2E scripts/artifacts.
- Frontend routes: `web-dashboard/src/app/router.tsx`.
- Config: `config.json`, `manifest.json`, `config_service.py`.
- Legacy cleanup: `docs/legacy-cleanup-inventory.md`.
- Card payload aliases: `docs/card-alias-audit.md`.
- Fast CI: `.github/workflows/ci-fast.yml`, `scripts/run_full_check.ps1`,
  `docs/ci-cd.md`.
- Global theme/visual polish: `docs/ui-polish-global-controls.md`,
  `web-dashboard/src/layout/GlobalUtilityDock.tsx`, Docker browser smoke.
- Localization: `docs/localization.md`, `web-dashboard/src/i18n/`, locale
  parity tests и Docker browser smoke.
- E2E performance/scopes: `docs/e2e-performance.md`,
  `docker/anki-e2e/e2e-contract.mjs`, `e2e-telemetry.py`.
- Search query/inspect: `docs/search-query-foundation.md`,
  `search_service.py`, `search_runtime.py`.
- Search UI/actions: `docs/search-v1-and-safe-actions.md`, `entity_actions.py`,
  `entity_action_runtime.py`, `useSearchWorkspace.ts`; не расширять mutation
  allowlist, batch limits или filtered-deck semantics без отдельного решения.

## Что нельзя делать

- Не менять generated files руками.
- Не коммитить runtime outputs.
- Не ослаблять sanitizer без точечного теста и причины.
- Не менять production payload ради устаревшего теста.
- Не удалять compatibility/fallback/adapter слой без проверки по
  `docs/legacy-cleanup-inventory.md`.
- Не удалять card payload aliases без проверки по
  `docs/card-alias-audit.md`.
- Не открывать dashboard server наружу.
- Не логировать полный token-bearing URL.
- Не откатывать чужие изменения без прямой просьбы.
- Не превращать Cards preview в iframe/JS execution surface. `table`/`tiles`
  проверять как front-only Shadow DOM, `ankiPreview` - как answer-only
  `AnkiCardShadowPreview` / Shadow DOM host из `renderedPreview.backHtml`.
- Не добавлять новый пользовательский UI-текст напрямую в React components или
  helpers вне locale resources. Сначала добавить semantic key с parity во все
  поддерживаемые локали, затем использовать `t()`; payload/user/technical data
  переводить нельзя.

Generated/runtime outputs:

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

1. Прочитать текущий код и тесты вокруг контракта.
2. Проверить фактическое поведение/форму данных.
3. Вносить минимальное изменение в правильный слой.
4. Обновить docs, если меняется behavior/contract.
5. Запустить проверки из `docs/test-matrix.md`.

Если actual payload корректен, а test assertion устарел, обновить тест.

Для rendering/media/startup не ограничиваться unit tests. Нужен live Anki smoke
или Docker E2E, если изменение затрагивает реальный runtime.

Для package changes запускать:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

или полный:

```powershell
.\build_ankiaddon.ps1
```

Для изменений Fast CI запускать общую cloud/local команду:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Не дублировать test pipeline в workflow YAML. Cloud failure не считается
успешным из-за локального PASS; distinction и fallback policy описаны в
`docs/ci-cd.md`.

Для Full Docker E2E использовать только typed modes workflow и существующие
`run_full_check.ps1 -DockerOnly ...` команды. Не переносить шаги `run-e2e.sh`
в YAML, не загружать raw `e2e-artifacts/` и не обходить failure exporter'а.
Перед handoff проверить exporter tests, локальные strict APKG/Perf100 и exact-SHA
cloud artifacts/screenshots. Bootstrap push trigger должен быть удалён до merge.

Для performance changes не запускать старый checkout ради нового baseline.
Targeted scope не называть release gate; `full` не урезать. Разрешён ровно один
осознанный exact-SHA warm-cache repeat. Parallel pool содержит один Chromium и
несколько contexts; state-mutating операции остаются serial. Runtime/profile/
token данные не попадают в BuildKit cache или public telemetry.

## Git workflow

Можно автономно:

- создать/переключить branch;
- сделать логические commits;
- push/PR, если пользователь попросил;
- rebase/merge при необходимости.

Но нельзя терять или перетирать чужие изменения.

Commit messages писать кратко и по фактическому результату, без повелительного
наклонения, названия этапа или пересказа prompt:

```text
docs: statistics metrics and reference inventory
fix(stats): partial previous-period coverage
```

## Финальный ответ

Указать:

```text
Branch:
Commit(s):

Изменено:
- ...

Добавлено:
- ...

Проверки:
- git diff --check: PASS

Не запускал:
- Docker E2E — причина.

Замечания:
- dirty changes, skipped checks, ограничения.
```

Если commit не делался, явно написать это и показать смысл текущего
`git status --short --branch`.

## Release automation

- Не dispatch-ить production release только для проверки реализации.
- Release разрешён лишь с current `master`, явной version/channel и approval
  `ankiweb-production`.
- Не переносить credentials из environment в CLI args, files, reports, commits
  или PR text и не сохранять browser auth state.
- Не подменять exact release archive Fast CI package или повторной сборкой.
- Не автоматизировать `Add New Branch`; существующая `Branch 1` обновляется
  максимум одним Save после всех pre-save checks.
- Не перезаписывать published SemVer assets: changed bytes требуют новой версии.
- В handoff фиксировать exact commit, artifact SHA, каждый gate и отдельно факт
  live dry-run/production publication.
