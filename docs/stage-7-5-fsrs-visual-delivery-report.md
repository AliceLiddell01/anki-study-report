# Stage 7.5: FSRS visual delivery, split bundle и CI runtime

Снимок документации: 2026-07-13.

## Executive summary

Stage 7.5 превратил пять FSRS routes из технического вывода в связный
read-only analytics surface, вынес Statistics и FSRS в реальные lazy chunks,
сделал package/runtime validation aware ко всему Vite asset graph и перевёл
Docker build actions на Node 24 releases. Backend formulas, typed payload,
cache identity, manual heavy calculations, token model и Anki configuration не
изменялись.

Локальный контур закрыт. Exact-SHA Fast CI и два cloud E2E gate фиксируются в
разделе Verification после публикации ветки.

## Visual redesign

### Overview

Проблема: плоская выдача не отделяла главный вывод от конфигурации и деталей.
Новая структура: primary insight, actual-vs-target track, иерархические KPI,
configuration groups и ссылки в глубокие analyses. Несовместимые presets не
усредняются. Unavailable values имеют отдельное состояние. Обе темы используют
одинаковую смысловую иерархию.

### Memory State

Проблема: distributions читались как raw data dump. Новая структура начинает
с честной snapshot estimate и показывает retrievability, stability и
difficulty как визуальные распределения. Исходные bins доступны в раскрываемых
таблицах. Sparse snapshot и ограничения historical interpretation видимы.

### Model Accuracy

Проблема: manual calculation выглядел как незавершённая форма. Idle state
объясняет scope, period и read-only безопасность; loading сохраняет контекст;
ready state показывает verdict, sample, RMSE, predicted/actual/ideal chart,
sparse bins и sample-size strip. Ошибка остаётся рядом с повторным действием и
не уничтожает последний валидный контекст.

### Learning Steps

Проблема: конфигурация и наблюдения не давали короткого ответа. Новая структура
показывает sufficiency verdict, текущие steps, наблюдаемые сценарии, confidence
и только observational recommendation. Расширение scope предлагается лишь при
реально недостаточной выборке.

### Simulator

Проблема: baseline и hypothetical result были визуально равноправными с
параметрами. Теперь сначала показаны scope/preset/current target/horizon, затем
валидируемая форма с единицами и bounds. Результат сравнивает current и
hypothetical workload карточками, chart и таблицей. Invalid input блокирует
запрос; sparse/truncated результат явно предупреждает об ограничениях.
Сценарий ничего не применяет к Anki.

### Shared behavior

Общий FSRS shell формулирует вопрос каждой страницы, сохраняет локальную
навигацию, scope/period context и mixed-preset warning. Тяжёлые расчёты остались
manual. Light/dark screenshots проверены локально при ширине 1265 и 989 px:
горизонтального overflow нет, controls и focusable elements сохраняют контраст.

## Bundle before/after

| Metric | До | После |
| --- | ---: | ---: |
| Entry JS | 878.24 kB | 235.49 kB |
| Largest JS chunk | 878.24 kB | 304.09 kB |
| Total JS | 878.24 kB | 911.50 kB |
| Total JS gzip | 249.30 kB | 256.26 kB |
| CSS | 82.31 kB / 14.95 kB gzip | 99.70 kB / 17.76 kB gzip |
| JS chunks | 1 | 8 |
| Build time | 6.21 s | 4.55 s |
| Vite large-chunk warning | Да | Нет |

Evidence filenames текущей сборки: `index-CRyr4kle.js` — entry,
`charts-runtime-DmzyL_mD.js` — крупнейший chunk,
`FsrsStatisticsPage-D7ZM8RvK.js` и `StatisticsPage-BvtjmR9Z.js` — lazy route
entries. Хэши имён не являются контрактом.

## Chunk architecture

`StatisticsPage` и `FsrsStatisticsPage` загружаются через `React.lazy`.
`RouteDeliveryBoundary` даёт branded Suspense fallback и отдельный reload UI
для ошибки lazy import без логирования URL/token. Deliberate `manualChunks`
разделяет React runtime, icons, Recharts runtime, chart math и chart state.
Границы нужны, чтобы chart dependency graph не возвращал monolithic entry и
чтобы каждый emitted JS оставался ниже 500 kB без повышения warning limit.

`scripts/check-bundle.mjs` проверяет manifest graph, минимум три JS chunks,
динамические Statistics/FSRS entries и лимит 500,000 bytes на каждый chunk.

## Package validation

Source of truth — Vite `manifest.json` плюс entry references из `index.html`.
Общий pure helper рекурсивно проходит `imports` и `dynamicImports`, включает
chunk `file`, `css` и `assets`, нормализует paths и запрещает traversal,
absolute/root-relative и backslash references. Package validator требует все
reachable files non-empty и продолжает отклонять stale unreachable JS/CSS.

Runtime `static_available` выполняет тот же graph traversal. Если manifest
есть, missing/empty/unsafe lazy dependency делает dashboard недоступным; для
legacy single-entry каталога без manifest сохранена прежняя проверка HTML.

Тесты покрывают single-entry compatibility, valid dynamic JS/async CSS,
missing/empty dynamic JS, missing async CSS, stale asset, unsafe path и runtime
failure при удалённом lazy chunk. Реальный архив содержит 38 entries и девять
достижимых JS/CSS assets.

## GitHub Actions maintenance

| Action | Было | Стало |
| --- | --- | --- |
| `docker/setup-buildx-action` | v3.12.0, `8d2750c68a42422c14e847fe6c8ac0403b4cbd6f` | v4.1.0, `d7f5e7f509e45cec5c76c4d5afdd7de93d0b3df5` |
| `docker/build-push-action` | v6.19.2, `10e90e3645eae34f1e60eeb005ba3a3d33f178e8` | v7.2.0, `f9f3042f7e2789586610d6e8b85c8f03e5195baf` |

Обе новые версии объявляют `runs.using: node24` и pinned полным immutable SHA.
`driver: docker`, containerd image store, `load`, GHA cache, telemetry и artifact
contract не менялись. Итоговый annotation status фиксируется после cloud gate.

## Verification

| Check | SHA | Result | Duration / evidence |
| --- | --- | --- | --- |
| `pnpm run test:frontend` | working tree | PASS, 146 tests | 5.07 s |
| focused package/server/E2E pytest | working tree | PASS, 24 tests | 4.90 s |
| `pnpm run build:addon` | working tree | PASS | 5.38 s build; bundle metrics above |
| package `--check` + `--check-only` | working tree | PASS | 38 entries, graph clean, `ZipFile.testzip=None` |
| Python compileall | working tree | PASS | `node scripts/run_python.mjs -m compileall -q anki_study_report` |
| `.\scripts\run_full_check.ps1 -SkipDocker` | working tree | PASS | 29.3 s; 146 frontend + 212 Python tests |
| Fast CI | pending publication | PENDING | exact SHA/run will be recorded |
| `standard/stats`, workers=3, telemetry | pending publication | PENDING | run/artifact and screenshot review will be recorded |
| `standard/full`, workers=3, telemetry | pending publication | PENDING | run/artifact and screenshot review will be recorded |
| master Fast CI | pending merge | PENDING | follows repository merge policy |

## Remaining limitations

- FSRS samples may remain sparse; presentation does not manufacture certainty.
- Memory state is a current snapshot, not historical reconstruction.
- Simulator is bounded by backend assumptions and is not a forecast guarantee.
- Simulator and recommendations are read-only; apply/mutation actions are out
  of scope.
- No new historical data, per-card inspector or multi-config aggregation was
  introduced.

