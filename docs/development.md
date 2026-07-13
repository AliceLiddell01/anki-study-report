# Разработка и проверки

Runtime/product verification follows `verification-run-policy.md`: Fast CI
exact SHA first, one targeted scope, then one final full. Same-SHA cloud PASS is
not duplicated locally.

Снимок документации: 2026-07-13.

## Требования

- Windows + PowerShell является основной рабочей средой проекта.
- Python нужен для pytest, py_compile и package validation.
- Node.js + pnpm нужны для dashboard.
- Docker нужен только для тяжелого E2E через реальный Anki Desktop.

Зафиксированный fast/CI runtime contract:

```text
Python 3.11
Node.js 20
pnpm 9.15.9
```

Версии находятся в `.python-version`, `.node-version` и `packageManager` в
`web-dashboard/package.json`.

В этой среде есть helper `scripts/run_python.mjs`, который подбирает рабочий
Python: `PYTHON`, bundled Codex Python, `python`, `python3`, `py -3`.

## Установка frontend dependencies

```powershell
cd web-dashboard
pnpm install --frozen-lockfile
```

## Быстрые проверки

Frontend:

```powershell
cd web-dashboard
pnpm run test:frontend
```

Python:

```powershell
node scripts/run_python.mjs -m pytest
```

Package validation существующего архива:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check-only
```

Сборка dashboard assets в add-on:

```powershell
cd web-dashboard
pnpm run build:addon
```

## Frontend-oriented aggregate

Из `web-dashboard/`:

```powershell
pnpm run test:all
```

Эта команда делает fast-проверки из frontend package scripts:

1. TypeScript typecheck.
2. Vitest frontend tests.
3. Production build dashboard.
4. Copy built assets into `anki_study_report/web_dashboard`.
5. Python pytest.
6. Package build + validation.

## Каноническая fast-команда

Без Docker:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

Это общая canonical точка входа для локального fallback и GitHub Actions Fast
CI. Она дополнительно проверяет `git diff --check`, отсутствие запрещённых
tracked runtime/generated файлов и существующий архив через `--check-only`.
Cloud workflow описан в `docs/ci-cd.md`.

С Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -CleanDocker
```

Только Docker E2E:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly
```

## Релизная сборка

```powershell
.\build_ankiaddon.ps1
```

Скрипт проверяет JSON, компилирует Python, запускает frontend tests, собирает
dashboard, запускает Python tests, собирает `.ankiaddon` и валидирует архив.

Полезные флаги:

```powershell
.\build_ankiaddon.ps1 -SkipInstall
.\build_ankiaddon.ps1 -SkipFrontendTests
.\build_ankiaddon.ps1 -SkipPythonTests
```

Флаги нужны только для осознанного ускорения локальной итерации. Для финальной
передачи артефакта лучше запускать без пропусков.

## Py_compile вручную

Если нужно отдельно проверить компиляцию Python:

```powershell
$files = Get-ChildItem -Path anki_study_report -Recurse -Filter *.py -File |
  Where-Object { $_.FullName -notmatch "\\__pycache__\\" } |
  Sort-Object FullName |
  ForEach-Object { $_.FullName }

node scripts/run_python.mjs -B -m py_compile @files
Remove-Item -Recurse -Force anki_study_report\__pycache__ -ErrorAction SilentlyContinue
```

После компиляции важно удалить `__pycache__`, иначе package validation или
структурные тесты могут обнаружить временные файлы.

## Git hygiene

Перед финальным отчетом или commit полезны быстрые проверки:

```powershell
git status --short --branch
git diff --stat
git diff --check
git ls-files --others --exclude-standard
git status --short --ignored e2e-artifacts
```

Не коммитить runtime outputs:

```text
e2e-artifacts/
web-dashboard/dist/
web-dashboard/screenshots/
anki_study_report/web_dashboard/
anki_study_report/user_files/
*.ankiaddon
```

## Как выбирать проверки

### Быстрый real-Anki contour

Для UI/runtime разработки вместо полного screenshot matrix можно выбрать
targeted workflow scope. Например Statistics:

```powershell
gh workflow run ci-e2e.yml --ref <branch> `
  -f mode=standard -f scope=stats -f screenshot_workers=3 `
  -f resource_telemetry=true -f verify_restart=auto
```

Targeted run остаётся real-Anki/security gate, но не является release proof.
Перед merge runtime/UI changes нужен `scope=full`; один повтор exact SHA
разрешён только для warm-cache measurement. Локально достаточно syntax,
targeted unit/structural tests и короткой диагностики. См.
`docs/e2e-performance.md`.

Подробная матрица находится в `docs/test-matrix.md`.

Короткое правило:

- docs-only: `git diff --check`;
- Python pure logic: pytest;
- frontend/types: `pnpm run test:frontend`;
- package/build: `scripts/package_addon.py --check` или `build_ankiaddon.ps1`;
- renderer/media/startup/hooks: live Anki smoke или Docker E2E.
