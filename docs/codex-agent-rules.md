# Правила для Codex/AI-агента

Снимок документации: 2026-07-11.

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

## Git workflow

Можно автономно:

- создать/переключить branch;
- сделать логические commits;
- push/PR, если пользователь попросил;
- rebase/merge при необходимости.

Но нельзя терять или перетирать чужие изменения.

Commit messages писать кратко, в повелительном наклонении:

```text
docs: update project documentation
fix: handle empty review periods
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
