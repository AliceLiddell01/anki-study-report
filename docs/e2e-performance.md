# Производительность Docker E2E

**Снимок документации:** 2026-07-23

Этот документ задаёт performance-контракт real-Anki E2E. Производительность не может достигаться удалением реального Anki, обязательного импорта трёх рабочих колод, token/security checks, native rendering, media proof, restart или artifact validation.

## Collection workload

Каждый Docker E2E импортирует три committed packages из `docker/anki-e2e/fixtures/real-decks/`.

Стандартный workload включает:

- 921 real notes;
- 921 real cards;
- 3 используемых real note types;
- 2,153 real media files;
- manifest/checksum/import/inventory/anchor reports;
- bounded scenario study history на существующих cards;
- API и browser proof Words/Grammar/Java.

Harness не создаёт synthetic collection content. Старый 10-card regression APKG и optional `strict-apkg` mode удалены.

## Mode и scope

Поддерживаемые modes:

```text
standard
perf100
```

`standard` — acceptance mode.

`perf100` используется только для отдельной performance-задачи. Он выбирает 100 distinct existing imported card IDs и применяет study-state. Notes/cards не создаются и не клонируются.

Scopes:

```text
full
global
stats
decks
activity
cards
settings
notifications
```

Scope определяет продуктовые API/browser assertions, но не отключает:

- три package imports;
- checksum и manifest validation;
- collection inventory;
- anchor resolution;
- zero-synthetic/zero-cloning proof;
- health, token и artifact security.

Restart policy `auto` означает обязательный restart для `full` и policy-defined behavior для targeted scopes. Для Cards/Inspection Profiles целевой proof использует `verify_restart=true`.

## Canonical verification sequence

```text
focused tests
→ Fast CI exact SHA
→ один targeted real-Anki gate
→ один standard/full только при matrix/planner escalation
```

Warm-cache repeats, worker comparisons и resource benchmarks не входят в обычную продуктовую работу.

## Image preparation

Cloud E2E использует exact GHCR digest и точный package artifact Fast CI. Mutable tags и fallback на локальную сборку запрещены в cloud consumer contour.

Локальный запуск может собирать image через Docker BuildKit. Cloud и local measurements не смешиваются.

Image preparation отдельно фиксирует:

- source (`ghcr` или local BuildKit);
- digest/image identity;
- pull/build/load duration;
- cache state;
- platform/label validation.

## Phase telemetry

Контейнер пишет:

```text
reports/e2e-phase-timings.json
reports/e2e-phase-timings.md
```

Минимальные измеряемые фазы:

- workspace copy;
- offline frontend install;
- frontend build;
- package build/check;
- real package checksum/import;
- inventory/anchor/scenario preparation;
- Anki startup/readiness;
- API smoke;
- browser capture;
- restart, если включён;
- artifact manifest validation;
- canonical total.

Для импорта дополнительно важны durations по каждому package и общий media import wall. Они диагностические и не должны становиться flaky second-level gate без накопленного baseline.

## Console progress

Долгие стадии обязаны печатать живой прогресс с префиксом `[real-decks]`:

```text
package 1/3 ... checksum PASS
importing package 1/3 ...
imported ... notes/cards/media
resolving anchors
applying scenarios
collection ready
browser smoke PASS
```

Отсутствие минутного «немого» ожидания является частью usability контракта harness.

## Screenshot workload

Стандартный browser proof создаёт:

- 10 page screenshots: 5 маршрутов × light/dark;
- 6 real-deck preview screenshots: Words/Grammar/Java × light/dark;
- 2 Cards state screenshots: light/dark;
- дополнительные policy-specific screenshots из wrapper checks, если scope их требует.

Native preview proof выполняется serial, потому что использует resolved runtime cards и media. Read-only page capture может использовать bounded workers, когда orchestration это поддерживает.

Файлы:

```text
reports/screenshot-performance.json
reports/screenshot-performance.md
```

Показатели:

```text
capture wall
summed task duration
screenshot count
worker count
failed task count
peak page/context count
```

## Resource telemetry

При включённой telemetry one-second cgroup sampler пишет:

```text
reports/resource-samples.jsonl
reports/resource-summary.json
reports/resource-summary.md
```

Агрегируются:

- average/median/p95/peak CPU;
- average/p95/peak memory;
- memory headroom;
- PID count;
- disk delta и block I/O.

Network counters остаются `null` с явной причиной, если cgroup surface их не предоставляет. Один peak sample не является достаточным основанием для вывода.

## Artifact composition

Итоговые reports:

```text
reports/e2e-performance-summary.json
reports/e2e-performance-summary.md
artifact-manifest.json
```

Performance summary связывает:

- exact SHA;
- mode/scope/restart;
- package/inventory totals;
- phase timings;
- image preparation;
- screenshot workload;
- resources;
- file count и bytes;
- artifact upload metadata.

Artifact manifest индексирует относительные уникальные paths. Traversal, missing required files, duplicate paths и token-bearing URL являются hard failure.

Обязательные real-deck reports:

```text
real-deck-manifest-report.json
real-deck-import-report.json
collection-inventory.json
anchor-resolution-report.json
scenario-application-report.json
```

## Historical baseline

Исторический baseline до real-deck foundation:

| Поле | Значение |
| --- | --- |
| Commit | `cd68c2ca827023477422575d8421074d960fd4a7` |
| Run | `29208090406` |
| Canonical duration | `183 s` |
| GitHub UI duration | примерно `202 s` |
| Runner | `ubuntu-24.04`, public standard |
| Artifact | около 27.7 MB |

Этот baseline использовал другой synthetic/APKG workload и не является apples-to-apples baseline для нового real-deck foundation. Он сохраняется только как историческая точка стоимости общего Docker lifecycle.

Новый baseline считается только после первого успешного exact-head `standard/full` с тремя committed working decks. До этого improvement/regression относительно 183 s не вычисляется.

## Diagnostic goals

До накопления минимум нескольких сопоставимых runs значения являются report-only:

- package checksum/import progress не зависает без сообщений;
- import inventory строго совпадает с manifest;
- browser proof не выполняет external requests;
- peak memory остаётся в пределах public runner с разумным headroom;
- artifact size объясняется media/screenshots, а не дублированием collection/package;
- `perf100` не увеличивает note/card count;
- successful exact-tree run не повторяется.

Hard timeout thresholds, удаление coverage или пропуск package import не являются допустимой оптимизацией.

## Диагностика медленного run

1. Сверить exact SHA, mode, scope, restart и image digest.
2. Проверить package-specific checksum/import durations.
3. Сопоставить media import wall с disk/block I/O.
4. Проверить Anki readiness и restart отдельно от browser capture.
5. Сравнить screenshot task sum и capture wall.
6. Смотреть p95 memory/CPU, а не только peak.
7. Проверить file count, largest files и upload duration.
8. Не повторять run без конкретной гипотезы и изменения.

## Performance changes

Изменение worker count, screenshot parallelism, image layering, package order или resource sampler требует отдельной performance-задачи и собственного verification plan.

Нельзя изменять generic harness под конкретное слово, filename или текущий media count. Изменение содержимого deck отражается в manifest/inventory и измеряется как новый fixture revision.
