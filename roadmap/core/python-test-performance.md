# Python test performance roadmap

**Роль:** supporting engineering roadmap для Core; не новый numbered `C` stage  
**Статус:** Planned / measurement-gated  
**Core relationship:** поддерживает текущий путь `post-C2 remediation → C3 → C4 → C5 → C6 → Core 1.0`  
**Platform relationship:** изменение mandatory Fast CI регулируется `CI 7 → CI 8`

## Зачем это нужно

Python test suite уже превышает 960 тестов и приближается к тысяче. Само количество тестов не является дефектом: полный inventory защищает runtime, API, security, packaging и CI contracts. Проблемой становится только доказанное замедление feedback loop, которое:

- повышает стоимость каждой Core-правки;
- провоцирует лишние повторные прогоны;
- усложняет локальное воспроизведение Fast CI;
- скрывает повторяющуюся стоимость fixtures, SQLite, imports и polling;
- увеличивает время обязательного non-Docker gate.

Цель roadmap — сократить подтверждённое wall time без удаления coverage, ослабления security boundaries или создания второго несогласованного test contour.

## Положение внутри Core

```text
post-C2 manual acceptance remediation
→ C3 Core UI & Shell Consolidation
→ C4 First-party Data Independence
→ C5 Today v2
→ C6 Profile v2 Foundation
→ Core 1.0 owner acceptance

Python test performance
└─ одна bounded supporting initiative, активируемая только по измерениям
```

Инициатива:

- не становится `C2.1`, `C3.1` или отдельной лестницей подпунктов;
- не меняет обязательную продуктовую последовательность;
- не блокирует текущий Core автоматически;
- может выполняться между Core-этапами либо внутри затронутого этапа, если test cost действительно мешает его разработке;
- не разрешает автоматически менять Fast CI: workflow-level adoption остаётся в Platform `CI 7 → CI 8`.

## Цель

Получить быстрый, детерминированный и поддерживаемый Python test contour с:

- одним authoritative test inventory;
- надёжным serial fallback;
- evidence-backed parallel mode только при доказанной пользе;
- ограниченной стоимостью fixtures и database setup;
- focused local commands, которые не заменяют полный Fast CI gate;
- воспроизводимыми timing evidence и rollback procedure.

## Вне scope

- удаление тестов ради красивого времени;
- сокращение sanitizer, token, media, action, APKG, migration, package или failure-diagnostics coverage;
- изменение production-кода только для ускорения теста;
- скрытие worker-dependent failures через retries, quarantine или увеличение timeout;
- path-based пропуск полного mandatory Fast CI;
- `continue-on-error` для обязательных тестов;
- self-hosted/larger runners как первый способ решения;
- широкое CI sharding до проверки более дешёвых вариантов;
- оптимизация real-Anki Docker E2E;
- committed caches, profiles, temporary databases или benchmark outputs.

## Условия активации

Реализация начинается только при наличии актуального evidence хотя бы по одному условию:

- Python tests выбраны `CI 7` как один главный Fast CI bottleneck;
- Python phase p50 составляет не менее 20% canonical Fast CI wall time;
- controlled estimate показывает не менее 30 секунд или 20% прямой экономии Python phase;
- локальный полный Python run заметно тормозит текущую Core-разработку;
- duration evidence показывает повторяющуюся стоимость fixtures, SQLite, imports, archives, sleeps или polling.

Если material bottleneck не подтверждён, roadmap остаётся Planned. Parallelism, новая dependency и дополнительная CI-сложность заранее не добавляются.

## Обязательный baseline

До оптимизации фиксируется baseline на exact commit и стабильном toolchain.

Нужно записать:

- exact source SHA;
- Python и pytest versions;
- OS, runner class и logical CPU count;
- collected, deselected и skipped counts;
- collection time и полное execution wall time;
- slowest setup/call/teardown entries;
- время по test modules или другой стабильной группировке;
- serial first-run result;
- Fast CI Python phase p50/p95 из ordinary runs, если выборка достаточна;
- platform-specific skips и Anki stub boundaries;
- наличие coverage/plugin overhead.

Диагностические команды:

```powershell
node scripts/run_python.mjs -m pytest --collect-only -q
node scripts/run_python.mjs -m pytest --durations=50 --durations-min=0.05
```

Для одного выбранного candidate допускается bounded exact-SHA comparison. Routine warm-cache repeats и повторное выполнение unrelated gates запрещены.

## Milestone 1 — Measurement and classification

Создать один baseline report, который классифицирует стоимость вместо предположения, что ответом обязательно является parallelism.

Разделить время на:

- collection и imports;
- fixture setup/teardown;
- test body execution;
- SQLite schema/data creation и copying;
- filesystem, archives и package fixtures;
- sleeps, polling и retry loops;
- subprocess/PowerShell/Node bridging;
- coverage/plugins;
- несколько длинных тестов против распределённого per-test overhead.

Результат:

- reproducible timing command или machine-readable output;
- top slow tests и modules;
- top expensive fixtures;
- один выбранный optimization candidate;
- expected direct saving;
- engineering cost;
- regression risk;
- stop condition.

Одновременно не запускаются несколько независимых performance candidates.

## Milestone 2 — Isolation and determinism audit

До принятия parallel execution проверить:

- shared mutable module/process state;
- `os.environ`, `sys.path`, `sys.modules` и global registries;
- fixed temp paths, archive names и SQLite filenames;
- mutable session/module fixtures;
- `autouse=True` fixtures и их transitive dependencies;
- execution-order assumptions;
- nondeterministic parametrization из sets/unordered data;
- Anki stubs и корректность monkeypatch restoration;
- path separators, permissions и line endings;
- subprocesses, ports, threads и background workers;
- generated package/dashboard paths, используемые несколькими тестами;
- session fixtures, которые будут повторяться на каждом worker.

Каждая обнаруженная коллизия получает одно решение:

- worker-specific isolated state;
- immutable/read-only fixture;
- deliberate grouping действительно связанных tests;
- documented serial-only scope.

Parallel failure считается regression. Его нельзя «исправлять» повторным прогоном.

## Milestone 3 — Один bounded parallel pilot

После isolation audit оценить `pytest-xdist` как candidate, а не как заранее принятое решение.

Сравнить одинаковый source и test inventory:

```text
serial
-n 2
-n 4
-n 4 --dist=worksteal
-n 4 --dist=loadscope
```

`loadscope` включается в comparison только если audit показывает значимую fixture locality.

Правила pilot:

- не использовать `-n auto` как initial default;
- в CI использовать fixed bounded worker count;
- сохранить documented serial command;
- сравнить collected/passed/failed/skipped/deselected counts;
- учитывать worker startup, repeated collection и per-worker session-fixture cost;
- проверять authoritative Fast CI platform до изменения mandatory gate;
- не совмещать pilot с runner migration, coverage change, cache experiment или job splitting;
- не добавлять retries и timeout inflation.

Parallel execution принимается только при material direct saving и детерминированном результате. Иначе candidate отклоняется, а работа продолжается через serial hotspot optimization.

## Milestone 4 — Hotspot optimization

Оптимизации применяются только к измеренной стоимости в таком порядке:

1. Удалить случайно повторяющуюся работу в fixtures/helpers.
2. Сузить ненужные `autouse` fixtures и локализовать их в профильных `conftest.py`.
3. Повысить fixture scope только для immutable или безопасно reset state.
4. Использовать validated SQLite template-copy pattern там, где migration/create behavior не является предметом теста.
5. Заменить real sleeps на injected clocks, events или deterministic transitions, если wall time не является контрактом.
6. Переиспользовать parsed read-only fixture data без shared mutable result.
7. Сократить повторную package/archive construction, сохранив package validation coverage.
8. Оптимизировать production-independent test helpers только после profiling.
9. Рассматривать bounded grouping/sharding лишь если fixture work и in-process parallelism недостаточны.

Каждая правка должна указывать, какую measured cost она устраняет. Refactor без timing hypothesis не входит в performance task.

## Milestone 5 — Adoption and regression budget

При принятии решения:

- canonical entrypoint остаётся `scripts/run_full_check.ps1 -SkipDocker`;
- focused local Python commands не объявляются merge evidence;
- `requirements-dev.txt` меняется только если новая test dependency действительно принята;
- `run_full_check.ps1`, Fast CI, timing schema и их tests обновляются синхронно при изменении execution semantics;
- `docs/test-matrix.md`, `docs/verification-run-policy.md`, `docs/ci-cd.md` и closeout report обновляются при фактическом adoption;
- serial execution сохраняется как diagnostic fallback;
- worker count и distribution strategy фиксируются явно;
- ordinary post-change runs наблюдаются по p50/p95 и first-run pass rate.

## Acceptance criteria

Для adoption обязательны все условия:

- полный Python test inventory сохранён;
- serial и optimized modes собирают эквивалентные tests;
- mandatory checks и coverage contracts не удалены;
- ordering dependency, shared-path collision и worker-only failure отсутствуют;
- Python phase p50 улучшается минимум на 20% либо baseline документирует другой material threshold;
- Fast CI p95 существенно не ухудшается;
- first-run pass rate не снижается;
- local canonical command и cloud command graph остаются согласованными;
- exact package metadata/inventory/SHA-256 contracts не меняются;
- platform-specific coverage остаётся явной;
- maintenance cost ниже сохранённого developer/CI time.

Если критерии не выполнены, serial contour сохраняется, candidate получает решение `reject/defer`, а parallelism не проталкивается искусственно.

## Verification plan

Минимум для implementation task:

- focused tests изменённых fixtures/helpers/configuration;
- один полный serial Python run;
- один полный candidate-mode run на том же exact commit;
- explicit test inventory/result comparison;
- `git diff --check` и dependency/config validation;
- canonical `scripts/run_full_check.ps1 -SkipDocker` после финальной правки;
- один authorized exact-SHA Fast CI run, если изменены workflow или canonical execution semantics.

Docker/real-Anki E2E не требуется для test-runner-only change, если diff не затрагивает runtime, package, APKG, browser harness или E2E contracts.

## Evidence и closeout

Historical measurements и итоговое решение сохраняются в `reports/`. Не коммитить raw caches, profiles, temp DB или benchmark directories.

Closeout report содержит:

- baseline и exact source identity;
- selected/rejected candidates;
- direct before/after Python comparison;
- Fast CI wall-time и Actions-minutes impact;
- flake/determinism evidence;
- dependency/maintenance impact;
- serial fallback и rollback procedure;
- remaining slow scopes;
- решение `adopt`, `defer` или `reject`.

## Rollback

Rollback обязателен при:

- worker-only failures;
- p95 regression;
- unstable test inventory;
- hidden shared-state leakage;
- platform-specific loss of coverage;
- maintenance cost выше measured benefit.

Rollback возвращает previous serial canonical execution, но не отменяет независимые fixture correctness improvements. Причина фиксируется в closeout, чтобы rejected experiment не повторялся без нового evidence.
