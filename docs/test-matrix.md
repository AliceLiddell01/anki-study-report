# Матрица проверок

Снимок документации: 2026-07-06.

Минимальная проверка - нижняя граница для маленького изменения. Желательная
проверка нужна перед merge/release или если изменение затрагивает несколько
слоев.

| Что изменилось | Минимальная проверка | Желательная проверка | Docker/live Anki нужен? | Почему |
| --- | --- | --- | --- | --- |
| docs-only | `git diff --check` | Проверить ссылки/пути вручную | Нет | Код и артефакты не менялись |
| Python pure logic | `node scripts/run_python.mjs -m pytest` | py_compile конкретных add-on files | Обычно нет | Большая часть pure modules тестируется без Anki |
| Anki hooks/startup | Targeted pytest если есть | Live Anki smoke или Docker E2E | Да | `aqt`, hooks и profile lifecycle не видны unit tests |
| Dashboard payload contract | `node scripts/run_python.mjs -m pytest tests/test_dashboard_payload.py` | `cd web-dashboard; pnpm run test:frontend` | Нет, если нет runtime/rendering | Backend shape должен совпасть с TS/types/normalizers |
| Frontend UI/types | `cd web-dashboard; pnpm run test:frontend` | `pnpm run build:addon` | Нет для чистой UI логики | TypeScript и Vitest ловят type/normalization regressions |
| Cards page/rendering/media | `pnpm run test:frontend` + `node scripts/run_python.mjs -m pytest tests/test_note_intelligence.py` | Docker E2E browser smoke | Да для final | Shadow DOM, native render и media loading зависят от runtime |
| Dashboard server/token/actions | `node scripts/run_python.mjs -m pytest tests/test_dashboard_server.py tests/test_dashboard_actions.py` | Frontend actions tests + local server smoke | Иногда | Нужно проверить token, allowlist и JSON errors |
| Cache/report_from_cache/stats_cache | `node scripts/run_python.mjs -m pytest tests/test_stats_cache.py` | smoke scripts из `scripts/smoke_report_cache_*.py` + full pytest | Нет обычно | Cache не должен менять public dashboard contract |
| Packaging/build scripts | `node scripts/run_python.mjs scripts/package_addon.py --check` | `.\build_ankiaddon.ps1` | Нет | Validator ловит forbidden files, linked assets, css markers |
| Docker E2E/runtime behavior | Targeted local checks перед запуском | `.\scripts\run_full_check.ps1 -CleanDocker` | Да | Проверяет реальный Anki Desktop/import/readiness/browser |
| Release artifact | `.\build_ankiaddon.ps1` | Fresh install in local Anki + optional Docker E2E | Да для runtime changes | Archive может быть валиден, но installed/runtime behavior важен |
| `.github/workflows/test.yml` или CI commands | Локально запустить измененные команды | `cd web-dashboard; pnpm run test:all` | Нет, если CI-only | CI должен повторять реальные local commands |
| `config.json` / config defaults | `node scripts/run_python.mjs -m pytest tests/test_config_service.py` | Package check | Нет обычно | Defaults должны нормализоваться без Anki |
| Browser search/query actions | `node scripts/run_python.mjs -m pytest tests/test_browser_actions.py tests/test_dashboard_actions.py` | Cards/Actions frontend tests | Иногда | Search query sanitizer защищает Anki Browser actions |

## Команды-шпаргалка

```powershell
git diff --check
node scripts/run_python.mjs -m pytest
cd web-dashboard
pnpm run test:frontend
pnpm run build:addon
pnpm run test:all
```

```powershell
.\build_ankiaddon.ps1
.\scripts\run_full_check.ps1 -SkipDocker
.\scripts\run_full_check.ps1 -CleanDocker
.\scripts\run_full_check.ps1 -DockerOnly
.\scripts\run_full_check.ps1 -CleanDocker -RequireApkgFixture -Perf100
```

## Когда не запускать Docker E2E

Не запускать Docker E2E для docs-only изменений и маленьких pure helper правок,
если они не касаются startup/rendering/media/server/package layout. Docker E2E
дорогой и нужен там, где unit tests не видят реальный Anki Desktop.

Для Cards preview финальный Docker browser smoke должен покрывать screenshots
`table`, `tiles` и `ankiPreview` в light/dark темах; `table`/`tiles` остаются
front-only через Shadow DOM, а `ankiPreview` проверяет единственный answer-only
preview host из `renderedPreview.backHtml` через `AnkiCardShadowPreview`
(`data-shadow-preview-mode="preview"`, `data-preview-side="answer"`). Perf100
использует tracked APKG fixture, клонирует импортированные cards/notes в Docker
collection до 100 cards, не создает новую APKG и не вводит virtualization;
timings сохраняются только как diagnostics.
