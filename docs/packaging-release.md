# Упаковка и релиз

Снимок документации: 2026-07-06.

Практический чеклист перед публикацией: `docs/release-checklist.md`.

Релизный артефакт проекта:

```text
anki_study_report.ankiaddon
```

Это zip-архив, который должен содержать файлы add-on на верхнем уровне, без
обертки `anki_study_report/`.

## Главная команда

```powershell
.\build_ankiaddon.ps1
```

Скрипт делает полный путь:

1. Проверяет, что запущен из project root.
2. Валидирует `manifest.json` и `config.json`.
3. Компилирует Python-файлы add-on через `py_compile`.
4. Удаляет Python caches.
5. Устанавливает frontend dependencies, если не указан `-SkipInstall`.
6. Запускает frontend tests, если не указан `-SkipFrontendTests`.
7. Собирает dashboard assets и копирует их в add-on.
8. Запускает Python tests, если не указан `-SkipPythonTests`.
9. Собирает `.ankiaddon`.
10. Валидирует свежий архив.
11. Повторно валидирует итоговый архив через `--check-only`.

## Упаковщик

Основной скрипт:

```text
scripts/package_addon.py
```

Собрать архив:

```powershell
node scripts/run_python.mjs scripts/package_addon.py
```

Собрать и проверить:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check
```

Проверить существующий архив:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --check-only
```

Собрать в другой путь:

```powershell
node scripts/run_python.mjs scripts/package_addon.py --output C:\path\anki_study_report.ankiaddon --check
```

## Обязательные файлы в архиве

`scripts/package_addon.py` требует:

```text
__init__.py
manifest.json
config.json
dashboard_server.py
web_dashboard/index.html
```

Также должны быть JS и CSS assets под:

```text
web_dashboard/assets/
```

`web_dashboard/index.html` должен ссылаться на реальные non-empty Vite assets.

## Что запрещено в архиве

Запрещенные директории и файлы:

```text
.git
.pytest_cache
__pycache__
node_modules
tests
anki_study_report/
web-dashboard/node_modules/
web-dashboard/src/
web-dashboard/dist/
*.ankiaddon
*.pyc
*.pyo
*.zip
user_files/
e2e-artifacts/
```

Смысл: archive должен быть installable add-on, а не snapshot всего репозитория и
не смесь исходников, runtime данных и dev dependencies.

## CSS/package guards

Package validator проверяет, что dashboard CSS содержит важные markers:

```text
[data-theme=light]
.topbar-surface
.shadow-panel
.cards-risk-table
.anki-card-shadow-preview
```

Это защита от ситуации, где архив собран со stale или неполными dashboard
assets.

## Manifest/config

Текущий `manifest.json`:

```text
package: anki_study_report
name: Anki Study Report
min_point_version: 260500
max_point_version: 0
```

`mod` меняется только при осознанном release/versioning шаге. Для docs-only
handoff cleanup его не нужно bump-ать.

Текущий default dashboard port в `config.json`:

```text
web_dashboard.port: 8766
web_dashboard.auto_start: false
web_dashboard.idle_timeout_seconds: 1800
```

## Перед ручной проверкой в Anki

Если устанавливается свежий `.ankiaddon` поверх старой копии, лучше удалить
старую папку add-on из `addons21` или убедиться, что Anki полностью заменил
предыдущие файлы. После установки перезапустить Anki и заново открыть/restart
dashboard server.

Иначе можно случайно проверять новый архив через старые installed
`web_dashboard/assets`.
