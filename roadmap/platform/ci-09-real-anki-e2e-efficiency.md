# CI Stage 9 — Real-Anki E2E efficiency and evidence cost

**Status:** Conditional

**Dependency:** CI Stage 7 должен подтвердить bottleneck в GHCR preparation,
Anki lifecycle, browser capture или artifact path.

## Цель

Сократить wall time и storage cost real-Anki E2E, сохранив цепочку:

```text
exact tested commit
→ exact Fast/release package SHA-256
→ exact immutable GHCR digest
→ real Anki Desktop
→ sanitized indexed evidence
```

## Environment image

Оптимизация environment image выполняется только новой versioned revision после
layer inventory. Проверяются compressed/uncompressed size, ненужные runtime
packages, дублирующиеся files, layer ordering и pull/unpack variance.

Новая revision обязана пройти producer smoke, boundary scan, SBOM/provenance,
registry round-trip и exact-digest consumer gate. Product checkout, current
harness и `.ankiaddon` не запекаются в image.

## Anki startup и readiness

Измеряются startup/restart distributions, readiness polling, fixed sleeps,
profile/fixture preparation и shutdown cleanup. Fixed delay можно заменить только
bounded condition wait с сохранением diagnostics при timeout. Timeout не
уменьшается по лучшему одиночному run.

## Browser capture

Исследуются task duration, serial/parallel split, worker utilization и CPU/memory
headroom. Worker count меняется только на одинаковом screenshot task set с нулём
missing paths, collisions, console/page/request failures.

Можно устранять повторную navigation/setup работу, но нельзя сокращать screenshot
contract только ради скорости.

## Targeted/full policy

Planner может точнее выбирать targeted scope, но:

- Fast CI не запускает E2E автоматически;
- shared runtime/package/E2E infrastructure эскалирует `full`;
- release всегда выполняет exact-artifact `standard/full`;
- successful same-SHA scope не повторяется без relevant change;
- `strict-apkg` и `perf100` остаются специализированными gates.

## Artifact path

Отдельно измеряются redaction/export, manifest validation, compression, upload и
retained bytes.

Возможные candidates:

- подходящий compression level для уже сжатых PNG/ZIP;
- lossless screenshot optimization;
- contact sheets как дополнительный review artifact, не замена originals;
- tiered retention для targeted, full, failure и release evidence;
- удаление только доказанно дублирующихся files при сохранении package/hash proof.

Artifact readers, manual review и incident evidence обновляются синхронно.

## Controlled comparison

Сравнение использует одинаковые workflow/source SHA, package SHA-256,
environment digest, mode/scope/restart/workers, screenshot path set, fixture и
Anki version. Inner canonical phases анализируются отдельно от queue, pull и
upload.

## Completion criteria

- уменьшен один подтверждённый phase или artifact cost;
- manifest/API/browser/security/restart contracts сохранены;
- нет missing screenshots, hidden retries или роста flake rate;
- environment identity остаётся immutable и fail-closed;
- release path проходит ту же инфраструктуру;
- local Docker остаётся source-build diagnostic fallback;
- evidence сохранено в `reports/ci/`.

## Out of scope

- возврат BuildKit/GHA cache в cloud;
- mutable GHCR tag;
- bake checkout/package/harness в image;
- automatic full E2E на каждом PR;
- изменение product behavior ради тестов;
- удаление security, APKG, telemetry, notification или restart checks.
