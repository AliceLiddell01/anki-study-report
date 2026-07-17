# CI Stage 8 — Fast CI critical-path optimization

**Status:** Conditional

**Dependency:** CI Stage 7 должен подтвердить, что Fast CI остаётся приоритетным
bottleneck и что выбранный candidate даст заметную экономию без потери coverage.

## Цель

Сократить время обязательного PR gate, сохранив:

- одну canonical non-Docker команду;
- полный Python/frontend/package contract;
- exact tested commit и exact package producer;
- fail-closed artifact metadata и SHA-256;
- возможность локального воспроизведения той же командой.

Stage 8 не должен превращать Fast CI в набор несогласованных YAML-команд или
заменять полный gate path-based предположениями.

## Кандидаты для исследования

### Runner comparison

Провести paired exact-SHA benchmark `windows-2025` и `ubuntu-24.04` только если
Stage 7 показывает значительную долю runner/setup overhead.

Смена primary runner допустима лишь при доказанной эквивалентности:

- test inventory и results;
- generated dashboard assets;
- package inventory и validation;
- line-ending/permissions semantics;
- platform-specific security tests;
- exact package handoff в Linux real-Anki E2E.

Если Linux значительно быстрее, возможна модель `Linux primary + narrow Windows
compatibility`, но не два полных mandatory jobs на каждый PR. Windows release
artifact path меняется только отдельным release-stage решением.

### Python test execution

Исследовать `pytest` parallelism или bounded sharding только после аудита:

- shared process/global state;
- temporary paths и SQLite files;
- monkeypatch/environment isolation;
- ordering assumptions;
- Anki stubs и platform-specific skips.

Любой worker-dependent failure считается regression. Нельзя скрывать его rerun
или увеличением timeout.

### Frontend critical path

Измерять отдельно:

- TypeScript typecheck;
- Vitest transform/collection/execution;
- Vite production build;
- bundle guard и asset synchronization.

Incremental typecheck/build cache допускается только с точным invalidation key,
clean-run comparison и доказательством отсутствия stale success. Второй canonical
typecheck не возвращается.

### Dependency setup

Возможные направления:

- deterministic Python dev dependency lock и hash verification;
- анализ setup action/cache restore/save overhead;
- исключение сетевых обращений после успешного cache restore, где это возможно;
- обновление pinned Actions без mutable refs.

Cache enabled не считается cache hit. Оптимизация должна измерять restore, install
и post-job save отдельно.

### Job DAG

Разделение frontend/Python/package на параллельные jobs рассматривается только
если measured wall-time saving превышает:

- дополнительные runner startups;
- повторный checkout/setup;
- artifact handoff;
- суммарный рост Actions minutes.

Package job должен собирать ровно один exact artifact из доказанных inputs, а не
повторять frontend/Python pipeline. Простое «разделить на больше jobs» не является
оптимизацией.

## Запрещённые shortcuts

- пропуск полного Fast CI по path filter;
- removal Python/frontend/package validation ради секунд;
- `continue-on-error` для обязательного check;
- unbounded caches или cache key без lockfile/toolchain identity;
- mutable Action tags без full-SHA pin;
- self-hosted runner как способ скрыть неэффективный pipeline;
- изменение production code ради ускорения теста.

## Verification experiment

Для одного выбранного candidate:

1. exact base SHA и exact feature SHA;
2. одинаковый source/test inventory;
3. controlled before/after pair;
4. один post-change validation run;
5. сравнение internal phases, job wall, queue и Actions minutes;
6. проверка exact package metadata/inventory/hash contract;
7. отсутствие роста failure/flake rate в последующих обычных runs.

## Completion criteria

- direct saving доказан, а не выведен из случайного workflow delta;
- p50 улучшается без ухудшения p95;
- test count и mandatory checks не сокращены;
- exact package producer остаётся единственным источником manual E2E package;
- local canonical command и cloud command graph остаются согласованными;
- изменение документировано в `docs/ci-cd.md`, test matrix и reports.

## Out of scope

- real-Anki E2E runtime;
- release publication semantics;
- merge queue и organization-scale governance;
- automatic flaky-test retries;
- scheduled heavy benchmark runs.
