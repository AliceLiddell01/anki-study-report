# Производительность Docker E2E

Снимок документации: 2026-07-13.

Этот документ задаёт измеряемый performance-контракт real-Anki E2E. Ускорение
не отменяет настоящий Anki, token/security checks, полный screenshot contract,
Cards/APKG и restart gate финального `full`-прогона.

## Авторитетный baseline

Старый checkout повторно не запускается. Единственный baseline — уже готовый
Stage 6.5 run:

| Поле | Значение |
| --- | --- |
| Commit | `cd68c2ca827023477422575d8421074d960fd4a7` |
| Workflow / run | Full Docker / Anki E2E / `29208090406` |
| Artifact | `ci-e2e-standard-29208090406-1` |
| Mode | `standard` |
| Canonical duration | `183 s` |
| GitHub UI duration | примерно `202 s` |
| Runner | `ubuntu-24.04`, public standard, 4 vCPU / 16 GB RAM / 14 GB SSD |
| Artifact | 103 файла, около 27.7 MB по zip listing |

Baseline phase/resource/screenshot telemetry отсутствует. Неизвестные значения
обозначаются `null` с причиной, а не нулём и не выдуманной точностью.

## Mode и scope

`mode` задаёт fixture/performance semantics: `standard`, `strict-apkg`,
`perf100`. `scope` независимо задаёт продуктовую область:

- `full` — вся существующая матрица, Cards/APKG по mode, states, 125% и restart;
- `global` — shell, Today, Profile, Tools, avatar menu и global theme;
- `stats` — пять Statistics routes, query controls, states и 125%;
- `decks` — hierarchy, selection/actions, states и 125%;
- `activity` — Calendar/history, states и 125%;
- `cards` — synthetic/APKG Cards modes, Shadow DOM, media/native rendering;
- `settings` — пять settings routes и 125%.

Каждый targeted scope всё равно проходит real Anki startup/import/readiness,
API health/status, token/safe URL checks, browser console/request checks,
redaction и manifest validation. Это development contour, не release gate.
`strict-apkg`/`perf100` разрешены только для `full` или `cards`.

Restart policy `auto` означает: обязателен для `full`, пропущен для targeted.
Явные `true`/`false` нужны только для диагностики. Финальный contour всегда
`mode=standard`, `scope=full`.

## Параллельный capture

Один Chromium process обслуживает bounded pool из BrowserContext/Page pairs.
Default `auto` на public runner означает 3 workers, допустимый диапазон 1–4.
Очередь состоит из stable task descriptors: ID, scope, route, theme, zoom,
state, unique artifact path и worker ownership. Порядок и manifest сортируются;
duplicate IDs/paths отклоняются.

Параллельны только read-only route/theme screenshots и их navigation/layout
assertions. Profile/settings persistence, deck Browser action, APKG import,
Cards/native rendering, fixture/report mutation, restarts и aggregate error
validation остаются serial. Ошибки workers агрегируются после controlled
cleanup; завершённые screenshots и per-task diagnostics сохраняются.

Файлы:

```text
artifacts/reports/screenshot-performance.json
artifacts/reports/screenshot-performance.md
```

Основные формулы:

```text
parallel speedup = sum(task duration) / capture phase wall
parallel efficiency = parallel speedup / worker count
saved wall = max(0, sum(task duration) - capture phase wall)
```

Это практическая оценка shared-browser workload, не изолированный академический
benchmark. Default 3 меняется на 4 только после стабильного `stats` comparison
без missing/collisions/errors и с приемлемым memory headroom.

## Docker cache и layers

Workflow использует Buildx + `docker/build-push-action`, default `docker`
driver с containerd image store, `cache-from` и `cache-to`
`type=gha,mode=max` с zstd compression. Containerd store позволяет BuildKit загрузить результат
непосредственно в Docker Engine без отдельного OCI export/import. Cache scope фиксирует Ubuntu/architecture,
Anki 26.05 и Playwright 1.49.1; Dockerfile, install script, image, versions и
lockfile естественно участвуют в layer keys.

Layering идёт от стабильного к volatile:

1. Playwright base и apt packages;
2. pnpm/Playwright Python tooling;
3. отдельный `install-anki.sh` и Anki installation;
4. package/workspace manifests + `pnpm fetch --frozen-lockfile`;
5. E2E `.sh/.py/.mjs` и entrypoint.

Изменение browser smoke больше не переустанавливает Anki. Runtime workspace
выполняет `pnpm install --offline --frozen-lockfile` из content-addressable
store, затем обычный frontend build. Source не берётся из cache: checkout
монтируется read-only и копируется в fresh writable build directory.

В BuildKit cache запрещены profile, collection, token, readiness, logs,
screenshots, package и user settings. `.dockerignore` исключает Git metadata,
node_modules, builds, downloads и runtime outputs, сохраняя tracked APKG.

`gha-enabled` означает, что backend подключён; это не заявление о cache hit.
Hit/miss подтверждается build record/log, а warm saving — двумя наблюдениями
одного exact SHA.

## Phase и resource telemetry

Container orchestration записывает structured phases в:

```text
artifacts/reports/e2e-phase-timings.json
artifacts/reports/e2e-phase-timings.md
```

Измеряются workspace copy, offline install, frontend build, package,
fixture/profile preparation, Anki start/readiness/API, browser capture,
restart phases, manifest validation и canonical total. Workflow отдельно
добавляет runner/Buildx/build-load/upload wall time, поскольку эти фазы живут
вне container. Отчёт показывает slowest phases и critical path без fake
precision.

Lightweight one-second cgroup sampler пишет:

```text
artifacts/reports/resource-samples.jsonl
artifacts/reports/resource-summary.json
artifacts/reports/resource-summary.md
```

Он агрегирует average/median/p95/peak CPU, average/p95/peak memory, headroom,
PIDs, disk delta и block IO. Network counters остаются `null` с причиной, если
lightweight cgroup surface их не даёт. Container CPU может превышать 100%; на
4-vCPU runner около 400% означает насыщение всех CPU. Выводы не делаются по
одному peak sample. Sampler bounded, останавливается через cleanup и не читает
env/token contents.

## Performance и artifact contract

Итоговые файлы:

```text
artifacts/reports/e2e-performance-summary.json
artifacts/reports/e2e-performance-summary.md
ci-e2e-summary.json                 schema v2
ci-e2e-summary.md
```

Они связывают baseline/current/improvement, phases, parallel workers,
resources, BuildKit state и artifact composition. Manifest schema v2 индексирует
performance reports; resource reports обязательны только при включённой
telemetry. Все paths relative/unique/sorted, traversal и missing required
отклоняются. Token и полный dashboard URL не попадают в public export.

Public upload сохраняет `if: always()`, redaction, retention 7 days и
`compression-level: 0` для PNG/`.ankiaddon`. File count, total/PNG/JSON-log
bytes и largest files считаются до upload. Duration, artifact ID и digest
фиксируются в GitHub Step Summary после upload.

## Запуск и verification

Manual inputs: `mode`, `scope`, `screenshot_workers`, `resource_telemetry`,
`verify_restart`. Неверные и несовместимые значения отклоняются до build.

Development example:

```powershell
gh workflow run ci-e2e.yml --ref <branch> `
  -f mode=standard -f scope=stats -f screenshot_workers=3 `
  -f resource_telemetry=true -f verify_restart=auto
```

Final example меняет scope на `full`. Проверка этапа: exact-SHA Fast CI,
targeted stats с 3 и 4 workers, первый full standard, один повтор того же SHA
для warm cache, затем ручной review обоих artifacts. Targeted/full не
сравниваются как apples-to-apples. После fast-forward merge full exact SHA не
дублируется; master Fast CI обязателен.

Цели — diagnostic, пока variance не изучена: warm canonical 130–145 s,
workflow 150–170 s, targeted 60–100 s, capture wall reduction не менее 25%,
peak memory ниже 12 GB и headroom не менее 3 GB. Они не являются flaky
second-level gates.

## Диагностика медленных runs

1. Сверить exact SHA/mode/scope/workers и cache state.
2. Сравнить `e2e-phase-timings`, slowest screenshots и worker utilization.
3. Проверить p95, не только peak CPU/memory, и disk/block IO delta.
4. Отличить cold BuildKit export от warm restore и runtime regression.
5. Проверить file count/bytes и upload duration.
6. При worker failure открыть task ID/route/theme и failure artifacts.

Runner variance не исправляется жёстким timeout threshold или удалением
coverage. Multi-job sharding остаётся future option только если full suite
вырастет примерно до 5–10 минут; отдельный BrowserContext pool дешевле и
сохраняет один real-Anki lifecycle.

## Измеренный результат Stage 6.6

Финальная functional implementation проверена на SHA
`33674a425ade17f07bed2ae2e4b5d9721bdbe567`. Performance goals остаются
report-only: warm full не достиг целевого диапазона, но причина измерена и
coverage не ослаблялась.

| Metric | Baseline | Full first `29214180020` | Full warm `29214315716` |
| --- | ---: | ---: | ---: |
| Canonical summary wall | 183 s | 205 s | 190 s |
| GitHub workflow wall | ~202 s | 231 s | 209 s |
| Build/cache/load | unknown | 87.7 s | 99.5 s |
| Inner real-Anki E2E | unknown | 106.2 s | 81.1 s |
| Parallel capture wall | n/a | 11.20 s | 8.95 s |
| Summed capture work | n/a | 32.49 s | 25.73 s |
| Parallel speedup | n/a | 2.90× | 2.87× |
| Parallel efficiency | n/a | 96.7% | 95.8% |
| p95 / peak CPU | n/a | 243% / 286% | 209% / 244% |
| p95 / peak memory | n/a | 1.86 / 1.99 GB | 1.79 / 1.89 GB |
| Memory headroom | n/a | 13.64 GB | 13.79 GB |
| Screenshots | 62 | 62 | 62 |
| Public artifact files | 103 | 106 | 106 |
| Public artifact bytes | ~27.7 MB | 27.84 MB | 27.85 MB |
| Upload duration | unknown | ~2 s | ~2 s |

Workers comparison использовал одинаковый SHA `0776643`: stats workers=3 run
`29213461563` дал capture 4.04 s, speedup 2.71×, efficiency 90.3% и p95 CPU
230%; workers=4 run `29213598324` дал 4.01 s, 3.34×, 83.4% и p95 CPU 266%.
Выигрыш 28 ms (0.7%) не устойчив и не оправдывает дополнительный context,
поэтому default остаётся 3.

Оба full artifacts имеют 62 одинаковых с baseline screenshot paths, 0 missing,
0 duplicates, 0 console/request/page errors и прошли token/secret scan.
Buildx record подтвердил cache reuse, но перенос image layers через GHA на
этом public runner стоил больше сохранённой сборки; warm canonical оказался на
7 s (3.8%) медленнее baseline. Это известный measured limitation, не скрытый
успех. Targeted inner stats contour при этом стабильно около 52–53 s и даёт
быстрый real-Anki development feedback; дальнейшая работа должна уменьшать
image-transfer cost, а не урезать full coverage.
