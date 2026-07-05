# Разработка и проверки

Снимок документации: 2026-07-05.

## Требования

- Windows + PowerShell является основной рабочей средой проекта.
- Python нужен для pytest, py_compile и package validation.
- Node.js + pnpm нужны для dashboard.
- Docker нужен только для тяжелого E2E через реальный Anki Desktop.

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

## Одна команда для локального пайплайна

Из `web-dashboard/`:

```powershell
pnpm run test:all
```

Эта команда делает:

1. TypeScript typecheck.
2. Vitest frontend tests.
3. Production build dashboard.
4. Copy built assets into `anki_study_report/web_dashboard`.
5. Python pytest.
6. Package build + validation.

## Полная проверка через PowerShell wrapper

Без Docker:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

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

Подробная матрица находится в `docs/test-matrix.md`.

Короткое правило:

- docs-only: `git diff --check`;
- Python pure logic: pytest;
- frontend/types: `pnpm run test:frontend`;
- package/build: `scripts/package_addon.py --check` или `build_ankiaddon.ps1`;
- renderer/media/startup/hooks: live Anki smoke или Docker E2E.
