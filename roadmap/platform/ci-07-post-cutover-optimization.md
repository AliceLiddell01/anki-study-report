# CI Stage 7 — Post-cutover measurement and optimization budget

**Status:** Conditional

Stage 7 начинается только после CI Stage 6B и не является разрешением немедленно
менять runner, caches, test coverage или verification gates. Его задача — собрать
достаточно данных о новом GHCR-only contour и выбрать один доказанный bottleneck.

## Исходное состояние

К этому этапу уже выполнено:

- duplicate heavy release build удалён из PR path;
- Fast CI производит exact `.ankiaddon` и выполняет один canonical TypeScript
  typecheck;
- manual/reusable real-Anki E2E использует exact Fast CI package;
- release E2E использует exact release artifact;
- cloud environment берётся только по immutable GHCR digest;
- cloud BuildKit/Buildx/containerd build-load и `type=gha` cache удалены;
- local Docker build остаётся отдельным development/diagnostic contour.

Исторические измерения доказали пользу package reuse и GHCR cutover, но не
создают вечный baseline: после product growth меняются test count, screenshots,
restart checks и длительность canonical Anki contour.

## Цель

Построить rolling baseline, который отделяет:

```text
queue time
→ runner/action setup
→ dependency installation
→ canonical Fast CI phases
→ exact-package staging/upload
→ GHCR pull/validation
→ real-Anki canonical phases
→ artifact preparation/upload
→ cleanup/post-job work
```

Отдельно учитывать:

- targeted и `standard/full`;
- Fast CI, manual E2E и release-artifact E2E;
- project failure, infrastructure failure, cancellation и confirmed flake;
- direct removed work и observational cross-run difference;
- wall time, runner minutes, artifact storage и пользовательское ожидание.

## Источники данных

Приоритет источников:

1. schema-versioned JSON/Markdown внутри existing artifacts;
2. GitHub workflow/job/step timestamps;
3. GitHub Actions repository performance/usage metrics, когда они доступны;
4. decoded logs только для пробелов, которых нет в structured evidence.

Новые тяжёлые runs не создаются только ради наполнения графика. Сначала
используется обычная история product work. Controlled paired run допускается лишь
для одного выбранного candidate и с exact SHA/package/image identity.

## Минимальная выборка

Для trend-вывода желательно иметь не менее:

- 10 comparable successful Fast CI runs;
- 5 comparable targeted E2E runs одного scope;
- 3 comparable `standard/full` runs текущего contract.

Если release cadence не даёт такую выборку, stage фиксирует `insufficient data` и
использует один отдельный paired experiment вместо ложного среднего.

## Обязательные метрики

- p50/p90/p95 workflow и job duration;
- queue time;
- success/failure/cancel rate;
- Fast CI internal phase p50/p95;
- GHCR image preparation p50/p95;
- Anki startup/readiness, browser capture и restart phases;
- artifact preparation/upload duration и compressed size;
- runner image/version drift;
- monthly workflow minutes и artifact retention footprint;
- число повторов одного exact-SHA gate и причина каждого повтора.

## Результат Stage 7

Stage 7 должен выдать:

- один current baseline document;
- один sanitized machine-readable trend artifact или reproducible analysis script;
- top bottlenecks с confidence level;
- оценку expected saving, engineering cost и regression risk;
- решение `proceed / defer / reject` для CI Stage 8, 9 и 10;
- performance budget, который не основан на лучшем одиночном run.

## Completion criteria

- метрики воспроизводимы из GitHub evidence;
- неизвестные значения остаются `null/unknown`, а не превращаются в zero;
- scopes и изменившиеся contracts не смешиваются;
- direct и observational savings разделены;
- выбран не более чем один следующий optimization candidate;
- roadmap, `docs/e2e-performance.md` и verification policy не противоречат друг
  другу.

## Out of scope

- автоматический запуск full E2E на каждом PR;
- warm-cache или worker repeats без отдельной performance-задачи;
- возврат cloud BuildKit/GHA cache;
- self-hosted или larger runners;
- test sharding, automatic retries или quarantine;
- сокращение screenshot/API/security/restart coverage;
- изменение release semantics.
